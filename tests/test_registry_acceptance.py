"""T021: end-to-end acceptance with executable, synthetic multi-label models.

These test-only linear models require no training or clinical data. Their JSON
artifact format is one owner integration, not a Safira serialization standard.
"""

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from safira import AdapterCapabilities, ModelAdapter
from safira.registry import (
    DuplicateRegistrationError,
    IdentityEvidence,
    ModelRegistry,
    RegisteredModelVersion,
    UnattachedModelError,
    UnknownVersionError,
)


@dataclass(frozen=True)
class _ToyClassifier:
    labels: tuple[str, ...]
    weights: tuple[tuple[float, ...], ...]
    offsets: tuple[float, ...]

    def score(self, vector, label):
        index = self.labels.index(label)
        return sum(weight * value for weight, value in zip(self.weights[index], vector)) + self.offsets[index]


class _ToyAdapter(ModelAdapter):
    def __init__(self, classifier, kind, boundaries):
        super().__init__(AdapterCapabilities(
            prediction_probability=kind == "probability", feature_representation=True,
        ))
        self.classifier = classifier
        self.kind = kind
        self.boundaries = tuple(boundaries)

    def predict(self, patient_data, label):
        if self.kind == "continuous_score":
            return self.classifier.score(patient_data, label)
        boundary = self.boundaries[self.classifier.labels.index(label)]
        return int(self.predict_probability(patient_data, label) >= boundary)

    def predict_probability(self, patient_data, label):
        self._require_capability("prediction_probability")
        return 1.0 / (1.0 + math.exp(-self.classifier.score(patient_data, label)))

    def extract_features(self, patient_data, label):
        self._require_capability("feature_representation")
        return tuple(patient_data)


class _ToyLoader:
    """Trusted owner loader associates known artifact bytes with its actual pair."""

    def __init__(self, artifact):
        self.artifact = artifact
        self.payload = json.loads(artifact)
        self.classifier = _ToyClassifier(
            tuple(self.payload["labels"]),
            tuple(tuple(row) for row in self.payload["weights"]),
            tuple(self.payload["offsets"]),
        )
        self.adapter = _ToyAdapter(
            self.classifier, self.payload["kind"], self.payload["boundaries"]
        )

    def identify_loaded_pair(self, classifier, adapter):
        return IdentityEvidence(
            sha256(self.artifact).hexdigest(),
            sha256(inspect.getsource(_ToyAdapter).encode()).hexdigest(),
            classifier is self.classifier and adapter is self.adapter
            and adapter.classifier is classifier
            and adapter.kind == self.payload["kind"]
            and adapter.boundaries == tuple(self.payload["boundaries"]),
        )


def _example(template, kind, label_count, model_id="toy-model", version="v1", seed=1):
    labels = [f"synthetic-label-{index}" for index in range(label_count)]
    # Class boundaries belong to these primary toy models, never a safety policy.
    boundaries = [0.4 + index * 0.1 if kind == "probability" else index - 0.5
                  for index in range(label_count)]
    payload = {
        "labels": labels, "kind": kind, "boundaries": boundaries,
        "weights": [[0.25 * (seed + index), -0.5] for index in range(label_count)],
        "offsets": [float(index) for index in range(label_count)],
    }
    artifact = json.dumps(payload, sort_keys=True).encode()
    loader = _ToyLoader(artifact)
    metadata = deepcopy(template)
    metadata.update(model_id=model_id, model_version=version)
    evidence = loader.identify_loaded_pair(loader.classifier, loader.adapter)
    metadata["classifier_artifact"] = {"sha256": evidence.classifier_sha256}
    metadata["adapter"].update(
        associated_model_id=model_id, associated_model_version=version,
        implementation_fingerprint=evidence.adapter_sha256,
        capabilities=loader.adapter.capabilities.to_dict(),
    )
    metadata["labels"] = [
        {
            "label_id": label, "negative_outcome": f"{label} absent",
            "positive_outcome": f"{label} present", "output_selector": label,
            "value_kind": kind,
            "value_source": "predict_probability" if kind == "probability" else "predict",
            "value_scale": {
                "minimum": 0.0 if kind == "probability" else None,
                "maximum": 1.0 if kind == "probability" else None,
                "meaning": "primary positive-class probability" if kind == "probability"
                           else "primary unbounded linear margin",
                "positive_direction": "increasing",
            },
            "class_mapping": {"positive_when": ">=", "boundary": boundaries[index]},
        }
        for index, label in enumerate(labels)
    ]
    metadata["input"] = {
        "schema": {"synthetic-vector": {"type": "float", "shape": [2]}},
        "modalities": ["synthetic-a", "synthetic-b"],
    }
    metadata["preprocessing_identity"] = {"version": f"synthetic-identity-{version}"}
    return loader, metadata


@pytest.mark.parametrize("kind,label_count", [
    ("probability", 2), ("continuous_score", 3), ("probability", 4),
])
def test_end_to_end_registration_preserves_primary_outputs_without_safety_setup(
    catalog_path, synthetic_metadata, kind, label_count, monkeypatch
):
    """SC-001/004/006; US1 1–6; FR-001–006, FR-009, FR-011–014."""
    loader, metadata = _example(synthetic_metadata, kind, label_count)
    expected = deepcopy(metadata)
    declared = RegisteredModelVersion.from_dict(metadata)
    patient_methods = []
    for name in (
        "predict", "predict_probability", "extract_features", "get_repeated_outputs",
        "get_modality_outputs", "get_domain_metadata", "explain", "get_input_metadata",
        "get_available_modalities",
    ):
        spy = Mock(wraps=getattr(loader.adapter, name))
        monkeypatch.setattr(loader.adapter, name, spy)
        patient_methods.append(spy)
    safety_methods = []
    for name in ("fit", "train", "calibrate", "prepare_safety_data", "select_policy", "assess", "deploy"):
        spy = Mock(side_effect=AssertionError("Unexpected safety setup or assessment."))
        object.__setattr__(loader.classifier, name, spy)
        safety_methods.append(spy)
    # No labelled dataset or safety-package argument/object exists in this flow.
    with ModelRegistry(catalog_path) as registry:
        accepted = registry.register(declared, loader.classifier, loader.adapter, loader)
        metadata["input"]["modalities"].clear()
        accepted.to_dict()["labels"].clear()
        fetched = registry.get_metadata(declared.model_id, declared.model_version)
        assert fetched.to_dict() == expected
        usable = registry.attach(
            declared.model_id, declared.model_version, loader.classifier, loader.adapter,
            loader, definition=declared,
        )
        assert registry.resolve_usable(declared.model_id, declared.model_version) is usable
        assert usable.metadata == fetched
        assert usable.classifier is loader.classifier
        assert usable.adapter is loader.adapter
        assert fetched.adapter.capabilities.feature_representation is True
        assert fetched.adapter.capabilities.explanation is False
        assert not hasattr(fetched, "signal_scores")
        assert not hasattr(fetched, "reliability_score")
        assert not hasattr(fetched, "status")
        for spy in patient_methods + safety_methods:
            spy.assert_not_called()
        # Independently exercise the existing adapter on invented numeric vectors
        # after registry operations; these are primary values, not assessments.
        for label in fetched.labels:
            method = getattr(usable.adapter, label.value_source)
            first, second = method([0.2, 0.4], label.label_id), method([1.2, 0.4], label.label_id)
            assert math.isfinite(first) and math.isfinite(second) and first != second
            if kind == "probability":
                assert 0.0 < first < 1.0 and 0.0 < second < 1.0
        for spy in safety_methods:
            spy.assert_not_called()


def _verify_catalog_after_restart(catalog_path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    snapshots = []
    with ModelRegistry(catalog_path) as registry:
        for item in manifest:
            expected = item["metadata"]
            declared = RegisteredModelVersion.from_dict(expected)
            key = (declared.model_id, declared.model_version)
            assert registry.get_metadata(*key).to_dict() == expected
            with pytest.raises(UnattachedModelError):
                registry.resolve_usable(*key)
            loader = _ToyLoader(item["artifact"].encode())
            usable = registry.attach(
                *key, loader.classifier, loader.adapter, loader, definition=declared,
            )
            assert registry.resolve_usable(*key) is usable
            assert usable.classifier is loader.classifier and usable.adapter is loader.adapter
            snapshots.append(registry.get_metadata(*key).to_dict())
        with pytest.raises(UnknownVersionError):
            registry.get_metadata("toy-a", "latest")
    print(json.dumps({"pid": os.getpid(), "snapshots": snapshots}))


def test_review_catalog_keeps_all_exact_versions_after_subprocess_restart(
    catalog_path, synthetic_metadata, tmp_path
):
    """SC-002; US2 1–5; FR-007–009, using three models and three versions."""
    keys = (("toy-a", "v1"), ("toy-a", "v2"), ("toy-a", "v3"),
            ("toy-b", "v1"), ("toy-c", "v1"))
    manifest = []
    with ModelRegistry(catalog_path) as registry:
        for index, (model_id, version) in enumerate(keys):
            kind = "probability" if index % 2 == 0 else "continuous_score"
            loader, metadata = _example(
                synthetic_metadata, kind, 2 + index % 2, model_id, version, seed=index + 1
            )
            declared = RegisteredModelVersion.from_dict(metadata)
            registry.register(declared, loader.classifier, loader.adapter, loader)
            with pytest.raises(DuplicateRegistrationError):
                registry.register(declared, loader.classifier, loader.adapter, loader)
            manifest.append({"metadata": metadata, "artifact": loader.artifact.decode()})
            # Every earlier accepted definition remains unchanged as the catalog grows.
            for previous in manifest:
                expected = previous["metadata"]
                assert registry.get_metadata(expected["model_id"], expected["model_version"]).to_dict() == expected
    manifest_path = tmp_path / "synthetic-acceptance-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(catalog_path), str(manifest_path)],
        cwd=tmp_path, env=environment, text=True, capture_output=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["pid"] != os.getpid()
    assert report["snapshots"] == [item["metadata"] for item in manifest]


if __name__ == "__main__":
    _verify_catalog_after_restart(*sys.argv[1:])
