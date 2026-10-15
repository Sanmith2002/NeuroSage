"""Local explanations that follow the packaged ``explainer_specs.json`` exactly. There is no fallback explainer.

* Random forest (pd_type_v1, vascular_v1): ``shap.TreeExplainer`` on the frozen uncalibrated forest, ``tree_path_dependent``,
  no background data, probability of the recorded class.
* Elastic-net logistic regression (ad_like_v1): contribution_j = coef_j * scaled_value_j, base value = intercept, in the
  uncalibrated log-odds (decision-function) space. The reference is the zero vector in scaled space (see the spec).

Contributions are computed for ALL estimator columns, checked to add up to the uncalibrated model output (1e-6), mapped back to
the raw feature names (a feature dropped as degenerate has contribution 0) and only then restricted to the observed features.
They explain the uncalibrated model score, so they do NOT sum to the calibrated probability.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..phase3 import packaging

ADDITIVITY_TOLERANCE = 1e-6
TOP_K = 5


class SpecError(RuntimeError):
    """explainer_specs.json is invalid, unsupported or inconsistent with the frozen pipeline."""


class AdditivityError(RuntimeError):
    """Base value plus contributions does not equal the uncalibrated model output. No explanation is returned."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise SpecError(message)


def validate_spec(spec: dict, label: str, family: str) -> None:
    _require(isinstance(spec, dict) and spec.get("target_definition") == label and spec.get("estimator_family") == family,
             f"{label}: the explainer spec does not describe this signal / estimator family")
    if family == "rf":
        _require(spec.get("explainer") == "shap.TreeExplainer" and spec.get("feature_perturbation") == "tree_path_dependent"
                 and spec.get("background_data") is None and str(spec.get("output_space", "")).startswith("probability")
                 and spec.get("class_index") in (0, 1), f"{label}: unsupported random-forest explainer specification")
    elif family in packaging.LINEAR_FAMILIES:
        _require(str(spec.get("explainer", "")).startswith("linear additive") and str(spec.get("output_space", "")).startswith("log-odds")
                 and str(spec.get("reference", "")).startswith("zero vector in post-pipeline scaled space")
                 and spec.get("contribution") == "coef_j * scaled_value_j" and spec.get("base_value") == "intercept_",
                 f"{label}: unsupported linear explainer specification")
    else:
        raise SpecError(f"{label}: estimator family {family} has no supported explainer specification")


def to_raw_contributions(pipeline, values: np.ndarray) -> np.ndarray:
    """Map estimator-column contributions (1 x m) to one value per RAW feature (1 x n_raw).

    A feature dropped as degenerate has contribution 0. If one raw feature produced several estimator columns (a value
    column plus a missing-indicator column), their contributions are summed per raw feature.
    """
    keep = pipeline.named_steps["drop"].keep_
    kept = int(keep.sum())
    values = np.asarray(values, dtype=float).reshape(1, -1)
    per_kept = values[:, :kept].copy()
    if values.shape[1] > kept:
        imputer = pipeline.named_steps.get("impute")
        indicator = getattr(imputer, "indicator_", None)
        if indicator is None or values.shape[1] != kept + len(indicator.features_):
            raise SpecError("the estimator has more input columns than the kept raw features and they cannot be mapped to raw features")
        for column, source in enumerate(indicator.features_):
            per_kept[:, source] += values[:, kept + column]
    elif values.shape[1] < kept:
        raise SpecError("the estimator has fewer input columns than the kept raw features")
    full = np.zeros((1, len(keep)))
    full[:, keep] = per_kept
    return full


class SignalExplainer:
    """Built once per bundle load from the (verified) spec and the frozen pipeline."""

    def __init__(self, signal: str, label: str, family: str, spec: dict, pipeline, features: list[str]):
        validate_spec(spec, label, family)
        try:
            structure = packaging.check_pipeline(label, family, pipeline, features)
        except packaging.PackagingError as exc:
            raise SpecError(str(exc)) from None
        _require(structure["pipeline_steps"] == spec.get("pipeline_steps") and structure["n_estimator_inputs"] == spec.get("n_estimator_inputs"),
                 f"{label}: the frozen pipeline structure disagrees with explainer_specs.json")
        self.signal, self.label, self.family, self.spec, self.pipeline = signal, label, family, spec, pipeline
        self.space, self.class_index = spec["output_space"], int(spec.get("class_index", 1))
        self.estimator = pipeline.named_steps["model"]
        self._tree = None
        if family == "rf":
            import shap

            self._tree = shap.TreeExplainer(self.estimator)  # no data: tree_path_dependent

    def explain(self, X: pd.DataFrame) -> dict:
        """Contributions per RAW feature for the one-row frame ``X`` (estimator columns checked to add up first)."""
        data = np.asarray(self.pipeline[:-1].transform(X), dtype=float)
        if self.family == "rf":
            values = self._tree.shap_values(data, check_additivity=False)
            values = values[self.class_index] if isinstance(values, list) else np.asarray(values)
            if values.ndim == 3:
                values = values[:, :, self.class_index]
            base = float(np.atleast_1d(np.asarray(self._tree.expected_value, dtype=float))[self.class_index])
            output = float(self.estimator.predict_proba(data)[0, self.class_index])
        else:
            values = data * self.estimator.coef_[0]
            base = float(self.estimator.intercept_[0])
            output = float(self.estimator.decision_function(data)[0])
        values = np.asarray(values, dtype=float).reshape(1, -1)
        if not np.isfinite(values).all() or abs(base + float(values.sum()) - output) > ADDITIVITY_TOLERANCE:
            raise AdditivityError(f"{self.signal}: the contributions do not add up to the uncalibrated model output; no explanation is returned")
        return {"contributions": to_raw_contributions(self.pipeline, values)[0], "base_value": base, "output": output}


def top_features(contributions: np.ndarray, features: list[str], observed: set[str], modality: dict[str, str], k: int = TOP_K) -> list[dict]:
    """Up to ``k`` OBSERVED features ranked by |contribution| (ties by feature name); zero contributions are left out."""
    rows = [(f, float(c)) for f, c in zip(features, contributions) if f in observed and c != 0.0]
    rows.sort(key=lambda r: (-abs(r[1]), r[0]))
    return [{"feature": f, "modality": modality.get(f, "unclassified"), "shap": c, "direction": "increases" if c > 0 else "decreases"}
            for f, c in rows[:k]]
