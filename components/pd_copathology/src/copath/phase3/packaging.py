"""Phase 4A.0: provenance packaging of the frozen final bundle (``package-final-bundle``) and the explainer check
(``verify-explainer-spec``).

This is a deployment/provenance step, not modelling. ``package-final-bundle`` is ADDITIVE ONLY: it writes
``bundle_manifest.json`` and ``explainer_specs.json`` into ``<models>/<version>/packaging/`` and never modifies a
bundle file, the final-evaluation lock or any threshold. It reads no participant-level data, never touches the
held-out set and never calls fit, partial_fit, tune, calibrate or predict (it only loads the two scikit-learn
artifacts, with ``InconsistentVersionWarning`` promoted to an error, to check them structurally).

``verify-explainer-spec`` reads the DEVELOPMENT set only and prints aggregate scalars.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import warnings
from pathlib import Path

import joblib
import numpy as np
import yaml

from .core import Paths, Phase3Error, load_context, now, prepare, sha256

FROZEN_SELECTED_SHA256 = "07ff5edb0b0aafcacf5b8e34551ef7266fc909809ca944256714e3c61d090646"
MANIFEST_SCHEMA_VERSION = "1.0"
EXPLAINER_SPEC_VERSION = "1.0"
MANIFEST_FILE, SPECS_FILE = "bundle_manifest.json", "explainer_specs.json"
SIGNALS = {"pd_type_v1": "pd_type", "ad_like_v1": "ad_like", "vascular_v1": "vascular_risk"}
BUNDLE_FILES = ("pipeline.joblib", "calibrator.joblib", "features.json", "config.json", "metrics.json", "model_card.md")
TRACKED_LIBRARIES = ("scikit-learn", "numpy", "scipy", "joblib", "shap", "xgboost")
PROVENANCE = ("Manifest created after final evaluation for deployment/inference provenance only; no model fitting, "
              "prediction, thresholding or evaluation was performed.")
JUSTIFICATION = ("The inference explanation reference is the mean of the final model's training representation, which is zero in "
                 "scaled space. This matches the Phase 3 LinearExplainer convention (mean of the training background) without using "
                 "any development data at inference time.")
LINEAR_FAMILIES = ("lr_enet", "lr_l2")


class PackagingError(Phase3Error):
    """The bundle cannot be packaged or verified (the message never contains data)."""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def packaging_dir(paths: Paths, version: str) -> Path:
    return paths.models / version / "packaging"


def feature_list_sha256(features: list[str]) -> str:
    """SHA-256 of the canonical serialisation of the ORDERED raw feature-name list."""
    return hashlib.sha256(json.dumps(list(features), separators=(",", ":")).encode("utf-8")).hexdigest()


def runtime_versions() -> dict[str, str]:
    out = {}
    for name in TRACKED_LIBRARIES:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = "not installed"
    return out


def load_artifact(path: Path):
    """Load a frozen scikit-learn artifact with ``InconsistentVersionWarning`` promoted to an error."""
    from sklearn.exceptions import InconsistentVersionWarning

    with warnings.catch_warnings():
        warnings.simplefilter("error", InconsistentVersionWarning)
        try:
            return joblib.load(path)
        except InconsistentVersionWarning as exc:
            raise PackagingError(f"{path.name} was saved with another scikit-learn version than the one installed "
                                 f"({exc.original_sklearn_version} versus {exc.current_sklearn_version})") from None


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_pipeline(label: str, family: str, pipeline, features: list[str]) -> dict:
    """Structural checks of a frozen pipeline (no data). Raises PackagingError when the explainer reference would not be valid."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    steps = [name for name, _ in pipeline.steps]
    drop = pipeline.named_steps.get("drop")
    if drop is None or list(drop.columns_in_) != list(features):
        raise PackagingError(f"{label}: the pipeline's first step does not take exactly the raw features of features.json")
    kept = int(drop.keep_.sum())
    model = pipeline.named_steps.get("model")
    if family == "rf":
        if steps != ["drop", "impute", "model"] or not isinstance(model, RandomForestClassifier):
            raise PackagingError(f"{label}: unexpected random-forest pipeline structure ({'>'.join(steps)})")
        if list(model.classes_) != [0, 1]:
            raise PackagingError(f"{label}: the random forest classes are not [0, 1]")
        return {"pipeline_steps": steps, "n_estimator_inputs": kept}
    if family in LINEAR_FAMILIES:
        if steps != ["drop", "impute", "scale", "model"] or not isinstance(model, LogisticRegression):
            raise PackagingError(f"{label}: unexpected linear pipeline structure ({'>'.join(steps)}); the zero-vector explanation "
                                 "reference is not valid")
        scaler, imputer = pipeline.named_steps["scale"], pipeline.named_steps["impute"]
        if not isinstance(scaler, StandardScaler) or not scaler.with_mean:
            raise PackagingError(f"{label}: the scaler does not centre its inputs (with_mean is off); the zero-vector reference "
                                 "is not valid")
        if getattr(imputer, "add_indicator", False):
            raise PackagingError(f"{label}: the imputer adds missing-indicator columns, which no scaler centres")
        width = {kept, scaler.n_features_in_, imputer.n_features_in_ if hasattr(imputer, "n_features_in_") else kept,
                 model.coef_.shape[1], len(scaler.mean_)}
        if len(width) != 1:
            raise PackagingError(f"{label}: some estimator input column is not produced by the fitted scaler "
                                 "(column counts differ between steps); the zero-vector reference is not valid")
        if model.coef_.shape[0] != 1 or list(model.classes_) != [0, 1]:
            raise PackagingError(f"{label}: the linear model is not a binary classifier with classes [0, 1]")
        return {"pipeline_steps": steps, "n_estimator_inputs": kept, "scaler_with_mean": True}
    raise PackagingError(f"{label}: estimator family {family} is not supported by the packaging step")


def explainer_spec(label: str, family: str, structure: dict) -> dict:
    """The explanation convention of Phase 3 ``explain`` for this signal, written down (versioned)."""
    base = {"target_definition": label, "estimator_family": family, "explains": "uncalibrated fitted model (pipeline.joblib), not the calibrator",
            "pipeline_steps": structure["pipeline_steps"], "n_estimator_inputs": structure["n_estimator_inputs"],
            "feature_names": "mapped back to the original raw feature names (features.json); a feature dropped as degenerate has zero contribution",
            "phase3_source": "copath.explain.shap_explainer.explain"}
    if family == "rf":
        return {**base, "explainer": "shap.TreeExplainer", "explainer_input": "uncalibrated fitted RandomForestClassifier taken from pipeline.joblib "
                "(step 'model'), applied to the output of the preceding pipeline steps",
                "feature_perturbation": "tree_path_dependent", "background_data": None,
                "model_output": "raw output of the forest = probability of class 1", "output_space": "probability (of the uncalibrated model)",
                "class_index": 1, "class_label": 1,
                "note": "Phase 3 calls TreeExplainer(estimator) without data, which shap resolves to tree_path_dependent."}
    return {**base, "explainer": "linear additive explanation, equivalent to shap.LinearExplainer with the full, unsubsampled final-training "
            "background (independent / interventional masker)",
            "output_space": "log-odds (raw margin of the uncalibrated model; decision_function)", "class_index": 1, "class_label": 1,
            "reference": "zero vector in post-pipeline scaled space (the mean of the final model's own training representation)",
            "reference_valid_because": "the estimator inputs are exactly the columns of a StandardScaler(with_mean=True) fitted on the same "
                                       "(imputed) training rows as the estimator; checked structurally at packaging time",
            "contribution": "coef_j * scaled_value_j", "base_value": "intercept_",
            "justification": JUSTIFICATION,
            "absent_features": "An absent feature is imputed by the pipeline, so its scaled value is generally not zero and it can carry a "
                               "non-zero contribution; such features are still excluded from top_features (observed features only)."}


def _frozen_inputs(paths: Paths, expected_selected: str) -> tuple[dict, str, str]:
    cfg = yaml.safe_load(Path(paths.config).read_text(encoding="utf-8"))
    version = str(cfg["final"]["version"])
    if not paths.selected.is_file():
        raise PackagingError("configs/frozen/selected_models_v1.yaml not found")
    if sha256(paths.selected) != expected_selected:
        raise PackagingError("selected_models_v1.yaml does not have the frozen SHA-256: the selection changed")
    if not paths.lock.is_file():
        raise PackagingError("the final-evaluation lock does not exist: `final` has not run, nothing to package")
    lock = _read_json(paths.lock)
    runs = lock.get("runs") or []
    if not lock.get("locked") or not runs or runs[-1].get("selected_models_sha256") != expected_selected:
        raise PackagingError("the final-evaluation lock does not refer to the frozen selection")
    selected = yaml.safe_load(paths.selected.read_text(encoding="utf-8"))
    return selected, version, runs


def _training_versions(paths: Paths, selected: dict, runs: list, configs: dict) -> tuple[dict, str, list[str]]:
    """Reference training library versions and where they come from. Never invents versions."""
    from_configs = [c.get("library_versions") for c in configs.values()]
    if all(isinstance(v, dict) and v for v in from_configs) and all(v == from_configs[0] for v in from_configs):
        return dict(from_configs[0]), "final_run_metadata", []
    from_lock = runs[-1].get("library_versions")
    if isinstance(from_lock, dict) and from_lock:
        return dict(from_lock), "final_run_metadata", []
    ids, versions = [], []
    for label in SIGNALS:
        run_id = selected["labels"][label]["cv_run_id"]
        path = paths.runs / f"{run_id}.json"
        if not path.is_file():
            raise PackagingError(f"no library versions: the final run did not store any and the selected cv run record for {label} is missing")
        recorded = _read_json(path).get("library_versions")
        if not isinstance(recorded, dict) or not recorded:
            raise PackagingError(f"no library versions: neither the final run nor the selected cv run record for {label} has them")
        ids.append(run_id)
        versions.append(recorded)
    if any(v != versions[0] for v in versions):
        raise PackagingError("the selected cv run records disagree about the library versions")
    return dict(versions[0]), "selected_cv_run_metadata", ids


def build(paths: Paths, expected_selected: str | None = None) -> tuple[dict, dict]:
    """Manifest (without ``packaged_at``) and explainer specs. Raises PackagingError on anything inconsistent; writes nothing."""
    expected_selected = expected_selected or FROZEN_SELECTED_SHA256
    selected, version, runs = _frozen_inputs(paths, expected_selected)
    root = paths.models / version
    signals, configs, specs = {}, {}, {}
    for label, signal in SIGNALS.items():
        choice = (selected.get("labels") or {}).get(label)
        folder = root / label
        if choice is None or not folder.is_dir():
            raise PackagingError(f"{label}: no selected model or no bundle folder")
        missing = [name for name in BUNDLE_FILES if not (folder / name).is_file()]
        if missing:
            raise PackagingError(f"{label}: bundle file(s) missing: {', '.join(missing)}")
        config, features = _read_json(folder / "config.json"), _read_json(folder / "features.json")
        if (config.get("label"), config.get("model")) != (label, choice["model"]) or config.get("selected_models_sha256") != expected_selected:
            raise PackagingError(f"{label}: config.json does not match the frozen selection")
        if str((config.get("phase3_config") or {}).get("final", {}).get("version")) != version:
            raise PackagingError(f"{label}: config.json belongs to another final bundle version")
        configs[label] = config
        pipeline, _calibrator = load_artifact(folder / "pipeline.joblib"), load_artifact(folder / "calibrator.joblib")
        structure = check_pipeline(label, choice["model"], pipeline, features)
        specs[signal] = explainer_spec(label, choice["model"], structure)
        signals[signal] = {
            "target_definition": label, "estimator_family": choice["model"], "tier": config.get("tier"),
            "calibration_method": (config.get("calibration") or {}).get("method"),
            "files_sha256": {name: sha256(folder / name) for name in BUNDLE_FILES},
            "raw_feature_list_sha256": feature_list_sha256(features), "n_raw_features": len(features),
            **{k: config.get(k) for k in ("label_card_sha256", "fold_scheme_sha256", "dataset_sha256", "config_sha256")}}
    reference, source, run_ids = _training_versions(paths, selected, runs, configs)
    runtime = runtime_versions()
    if reference.get("scikit-learn") != runtime["scikit-learn"]:
        raise PackagingError(f"scikit-learn mismatch: training {reference.get('scikit-learn')}, installed {runtime['scikit-learn']}; "
                             "the exact version is required")
    specs_doc = {"explainer_spec_version": EXPLAINER_SPEC_VERSION, "model_version": f"pd-copathology-{version}", "signals": specs}
    specs_text = json.dumps(specs_doc, indent=1, sort_keys=True) + "\n"
    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION, "model_version": f"pd-copathology-{version}", "final_bundle_version": version,
        "selected_models_sha256": expected_selected, "final_lock": {"present": True, "sha256": sha256(paths.lock)},
        "signals": signals,
        "reference_training_library_versions": reference, "version_source": source,
        "version_source_detail": ("selected cv run records (" + ", ".join(run_ids) + "); these are the versions of the cross-validation runs "
                                  "that produced the selected hyperparameters, not directly observed final-fit versions"
                                  if source == "selected_cv_run_metadata" else "library versions stored by the final run itself"),
        "packaging_runtime_versions": runtime,
        "explainer_specs": {"file": SPECS_FILE, "sha256": hashlib.sha256(specs_text.encode("utf-8")).hexdigest()},
        "provenance_note": PROVENANCE}
    return manifest, {"doc": specs_doc, "text": specs_text}


def _substance(manifest: dict) -> dict:
    return {k: v for k, v in manifest.items() if k not in ("packaged_at", "packaging_runtime_versions")}


def _write_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, path)


def cmd_package(paths: Paths | None = None, expected_selected: str | None = None, log=print) -> dict:
    """Create the manifest and explainer specs (idempotent; never overwrites different content)."""
    paths = paths or Paths()
    expected_selected = expected_selected or FROZEN_SELECTED_SHA256
    manifest, specs = build(paths, expected_selected)
    folder = packaging_dir(paths, manifest["final_bundle_version"])
    target_manifest, target_specs = folder / MANIFEST_FILE, folder / SPECS_FILE
    existing = [p for p in (target_manifest, target_specs) if p.is_file()]
    for name, version in manifest["packaging_runtime_versions"].items():
        reference = manifest["reference_training_library_versions"].get(name)
        if reference is not None and reference != version and name != "scikit-learn":
            log(f"WARNING: {name} differs between training ({reference}) and this environment ({version})")
    if len(existing) == 2:
        old = _read_json(target_manifest)
        if _substance(old) != _substance(manifest) or target_specs.read_text(encoding="utf-8") != specs["text"]:
            raise PackagingError("a packaging manifest already exists with different content; it is never overwritten. "
                                 "Investigate the difference (run with --verify) instead of repackaging.")
        log(f"already packaged (packaged_at {old.get('packaged_at')}); nothing rewritten")
        return old
    if existing:
        raise PackagingError("only one of the two packaging files exists; refusing to continue. Investigate before repackaging.")
    manifest["packaged_at"] = now()
    _write_new(target_specs, specs["text"])
    _write_new(target_manifest, json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    log(f"packaged: {target_manifest.name} and {target_specs.name} written to {folder.name}/ inside the bundle folder")
    return manifest


def verify(paths: Paths | None = None, expected_selected: str | None = None) -> list[str]:
    """Recompute every hash and compare with the manifest. Writes nothing. Returns the list of problems (empty = verified)."""
    paths = paths or Paths()
    expected_selected = expected_selected or FROZEN_SELECTED_SHA256
    cfg = yaml.safe_load(Path(paths.config).read_text(encoding="utf-8"))
    folder = packaging_dir(paths, str(cfg["final"]["version"]))
    if not (folder / MANIFEST_FILE).is_file() or not (folder / SPECS_FILE).is_file():
        return ["the packaging files do not exist: run `package-final-bundle` first"]
    saved, problems = _read_json(folder / MANIFEST_FILE), []
    try:
        fresh, specs = build(paths, expected_selected)
    except PackagingError as exc:
        return [str(exc)]
    except Exception as exc:  # noqa: BLE001 - an artifact that cannot even be loaded is a verification failure
        return [f"a frozen artifact could not be loaded ({type(exc).__name__})"]
    if sha256(folder / SPECS_FILE) != saved["explainer_specs"]["sha256"] or specs["text"] != (folder / SPECS_FILE).read_text(encoding="utf-8"):
        problems.append("explainer_specs.json does not match its recorded SHA-256 or the frozen pipelines")
    for signal, item in saved["signals"].items():
        mine = fresh["signals"].get(signal, {})
        for name, digest in item["files_sha256"].items():
            if mine.get("files_sha256", {}).get(name) != digest:
                problems.append(f"{signal}: {name} does not match the manifest")
        for key in ("raw_feature_list_sha256", "n_raw_features", "label_card_sha256", "fold_scheme_sha256", "dataset_sha256", "config_sha256",
                    "estimator_family", "calibration_method", "target_definition"):
            if mine.get(key) != item.get(key):
                problems.append(f"{signal}: {key} does not match the manifest")
    if _substance(saved) != _substance({**fresh, "explainer_specs": saved["explainer_specs"]}):
        problems.append("the manifest header (versions, lock hash, selection hash) differs from the current state")
    return sorted(set(problems))


# --------------------------------------------------------------------------
# verify-explainer-spec (development set only)
# --------------------------------------------------------------------------

def cmd_verify_explainer_spec(paths: Paths | None = None, log=print, max_rows: int = 1000, tolerance: float = 1e-6) -> dict:
    """Compare the packaged explanation convention with shap on the DEVELOPMENT set. Prints aggregate scalars only."""
    import shap

    from ..explain import shap_explainer

    paths = paths or Paths()
    ctx = load_context(paths)  # development rows only
    version = str(ctx.cfg["final"]["version"])
    specs_path = packaging_dir(paths, version) / SPECS_FILE
    if not specs_path.is_file():
        raise PackagingError("explainer_specs.json not found: run `package-final-bundle` first")
    specs = _read_json(specs_path)["signals"]
    results = {}
    for label, signal in SIGNALS.items():
        spec, folder = specs[signal], paths.models / version / label
        features = _read_json(folder / "features.json")
        pipeline = load_artifact(folder / "pipeline.joblib")
        data = prepare(ctx, label, ctx.cfg.get("main_tier", "primary"), features=features)
        X = data["X"]
        rng = np.random.default_rng(ctx.seed)
        rows = np.sort(rng.choice(len(X), min(max_rows, len(X)), replace=False))
        if spec["estimator_family"] in LINEAR_FAMILIES:
            estimator, scaled = pipeline.named_steps["model"], np.asarray(pipeline[:-1].transform(X), dtype=float)
            masker = shap.maskers.Independent(scaled, max_samples=len(scaled))  # the full background, no subsampling
            explainer = shap.LinearExplainer(estimator, masker)
            values = np.asarray(explainer.shap_values(scaled[rows]))
            formula = scaled[rows] * estimator.coef_[0]
            diff = max(float(np.max(np.abs(values - formula))), float(np.max(np.abs(np.atleast_1d(explainer.expected_value) - estimator.intercept_))))
            extra = {"max_abs_mean_scaled_background": float(np.max(np.abs(scaled.mean(axis=0))))}
        else:
            result = shap_explainer.explain("rf", pipeline, X, X.iloc[rows])
            if not result["space"].startswith("probability"):
                raise PackagingError(f"{signal}: the random-forest SHAP values do not add up in probability space")
            diff, extra = float(result["additivity_error"]), {}
        results[signal] = {"max_abs_difference": diff, **extra, "pass": bool(diff < tolerance)}
        log(f"{signal}: max |difference| = {diff:.3e}" + "".join(f"; {k} = {v:.3e}" for k, v in extra.items()) + ("  PASS" if diff < tolerance else "  FAIL"))
    if not all(r["pass"] for r in results.values()):
        raise PackagingError(f"verify-explainer-spec: a signal exceeds the tolerance {tolerance:g}")
    return results
