"""Load the frozen final bundle for inference, after the SAME integrity verification as ``package-final-bundle --verify``.

There is no fallback to an unverified bundle: any integrity problem raises :class:`BundleIntegrityError` before a model is
used. Inference never imports or calls training, tuning or calibration code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..features import leakage_guard
from ..phase3 import packaging
from ..phase3.core import Paths
from .explanations import SignalExplainer, SpecError
from .schema import SIGNAL_NAMES


class BundleIntegrityError(RuntimeError):
    """The frozen bundle failed verification. The message names the failed checks, never data."""


@dataclass
class SignalModel:
    signal: str
    label: str
    family: str
    calibration: str
    features: list[str]
    pipeline: object
    calibrator: object
    explainer: SignalExplainer


@dataclass
class Bundle:
    model_version: str
    selected_models_sha256: str
    signals: dict[str, SignalModel]
    modality: dict[str, str]
    reference_versions: dict
    runtime_versions: dict
    version_source: str
    warnings: list[str] = field(default_factory=list)

    @property
    def signal_features(self) -> dict[str, list[str]]:
        return {name: model.features for name, model in self.signals.items()}

    @property
    def features(self) -> list[str]:
        return list(dict.fromkeys(f for name in SIGNAL_NAMES for f in self.signals[name].features))


# The verification code is imported, not copied, so that inference and `package-final-bundle --verify` cannot drift apart.
verify_bundle = packaging.verify


def load_bundle(paths: Paths | None = None, expected_selected: str | None = None) -> Bundle:
    """Verify, then load, the frozen bundle. ``paths`` default to the configured locations; nothing is hard-coded."""
    paths = paths or Paths()
    warnings: list[str] = []
    problems = verify_bundle(paths, expected_selected, warnings_out=warnings)  # BEFORE any model is loaded or used
    if problems:
        raise BundleIntegrityError("the frozen bundle failed verification, no prediction was made: " + "; ".join(problems))
    import yaml

    version = str(yaml.safe_load(paths.config.read_text(encoding="utf-8"))["final"]["version"])
    folder = packaging.packaging_dir(paths, version)
    manifest = json.loads((folder / packaging.MANIFEST_FILE).read_text(encoding="utf-8"))
    specs = json.loads((folder / packaging.SPECS_FILE).read_text(encoding="utf-8"))["signals"]
    matrix = leakage_guard.load_matrix()
    models = {}
    for label, signal in packaging.SIGNALS.items():
        item, root = manifest["signals"][signal], paths.models / version / label
        features = json.loads((root / "features.json").read_text(encoding="utf-8"))
        pipeline = packaging.load_artifact(root / "pipeline.joblib")
        calibrator = packaging.load_artifact(root / "calibrator.joblib")
        try:
            explainer = SignalExplainer(signal, label, item["estimator_family"], specs[signal], pipeline, features)
        except SpecError as exc:
            raise BundleIntegrityError(f"no explanation can be produced, no prediction was made: {exc}") from None
        models[signal] = SignalModel(signal, label, item["estimator_family"], item["calibration_method"], features, pipeline, calibrator, explainer)
    return Bundle(manifest["model_version"], manifest["selected_models_sha256"], models, dict(zip(matrix["feature"], matrix["modality"])),
                  manifest["reference_training_library_versions"], manifest["packaging_runtime_versions"], manifest["version_source"], warnings)
