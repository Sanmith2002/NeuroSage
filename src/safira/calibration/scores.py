"""Private reconstruction of admitted Feature 005 calibration inputs.

This module has no public prediction API. Callers must first pass Feature 006's
complete shared admission gate. It only reconstructs stored training state and
applies the existing Feature 005 production encoder and frozen transform.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from collections.abc import Mapping

from safira.training.features import (
    FeatureColumn, FrozenFeatureSchema, FrozenPreprocessingState, _schema_digest,
)
from safira.training.records import (
    FeatureKind, FeatureSpec, PreprocessingPolicy, SafetyEstimatorArtifact,
    TrainingScope,
)
from safira.signals.base import SignalDimension


def _canonical_digest(value) -> str:
    def plain(item):
        if isinstance(item, Mapping):
            return {key: plain(value) for key, value in item.items()}
        if isinstance(item, (tuple, list)):
            return [plain(value) for value in item]
        return item
    return sha256(json.dumps(plain(value), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, repr=False)
class _ReconstructedFeatureState:
    artifact_digest: str
    scope: TrainingScope
    family: str
    schema: FrozenFeatureSchema
    preprocessing: FrozenPreprocessingState
    estimator_classes: tuple[int, int]
    coefficients: tuple[float, ...] = ()
    intercept: float | None = None
    probability: float | None = None


@dataclass(frozen=True, repr=False)
class _ScoreReconstruction:
    scores: tuple[float, ...]
    status: object | None = None
    reason_code: str = ""
    artifact_digest: str = ""
    source_key: tuple[str, str, str] = ()
    row_keys: tuple[str, ...] = ()


def _reconstruct_feature_state(artifact: SafetyEstimatorArtifact,
                               admitted_method_parameters: Mapping[str, Mapping]):
    """Rebuild typed frozen state from an already admitted allowlisted artifact.

    Feature 005 stores method-parameter digests, not raw method parameters. The
    supplied parameter values therefore come only from the independently
    admitted Feature 004 manifest and must reproduce each stored digest.
    """
    if type(artifact) is not SafetyEstimatorArtifact or not isinstance(admitted_method_parameters, Mapping):
        raise ValueError("artifact_input")
    payload = artifact.to_dict()
    if payload["artifact_version"] != "safira-correctness-estimator-v1":
        raise ValueError("artifact_version")
    if payload["lifecycle"] != "uncalibrated_non_deployable" or payload["calibrated"] or payload["deployable"]:
        raise ValueError("artifact_lifecycle")
    body_fields = set(payload) - {"digest"}
    allowed = {"artifact_version", "scope", "family", "feature_schema", "preprocessing",
               "training_protocol", "dataset_reference", "signal_run_reference", "estimator_state",
               "candidate_configuration", "dependency_versions", "training_metrics", "selection_metrics",
               "limitations", "lifecycle", "calibrated", "deployable", "validation_spent",
               "calibration_reserved", "protected_test_accessed"}
    if body_fields != allowed:
        raise ValueError("artifact_fields")

    frozen_schema = payload["feature_schema"]
    frozen_preprocessing = payload["preprocessing"]
    if set(frozen_schema) != {"scope", "columns", "feature_specs", "omitted_dimensions"}:
        raise ValueError("schema_fields")
    if set(frozen_preprocessing) != {"schema_digest", "medians", "means", "scales",
                                     "active_indices", "omissions", "policy"}:
        raise ValueError("preprocessing_fields")
    if frozen_schema["scope"] != artifact.scope.to_dict():
        raise ValueError("scope_mismatch")

    dimensions = {item.value: item for item in SignalDimension}
    specs = []
    for item in frozen_schema["feature_specs"]:
        fields = {"method_id", "method_version", "meaning", "dimension", "kind",
                  "method_parameters_sha256", "required", "state_indicators", "allowed_nonvalue_states"}
        if not isinstance(item, Mapping) or set(item) != fields:
            raise ValueError("feature_spec_fields")
        params = admitted_method_parameters.get(item["method_id"])
        if not isinstance(params, Mapping) or _canonical_digest(params) != item["method_parameters_sha256"]:
            raise ValueError("feature_parameters")
        if item["dimension"] not in dimensions:
            raise ValueError("feature_dimension")
        try:
            kind = FeatureKind(item["kind"])
        except Exception:
            raise ValueError("feature_kind") from None
        specs.append(FeatureSpec(
            item["method_id"], item["method_version"], item["meaning"],
            dimensions[item["dimension"]], kind, params,
            item["required"], item["state_indicators"], tuple(item["allowed_nonvalue_states"]),
        ))

    columns = []
    for item in frozen_schema["columns"]:
        fields = {"name", "method_id", "method_version", "meaning", "kind", "state"}
        if not isinstance(item, Mapping) or set(item) != fields:
            raise ValueError("column_fields")
        columns.append(FeatureColumn(item["name"], item["method_id"], item["method_version"],
                                     item["meaning"], item["kind"], item["state"]))
    schema = FrozenFeatureSchema(artifact.scope, tuple(columns), tuple(specs),
                                 frozen_schema["omitted_dimensions"])
    if _schema_digest(schema) != frozen_preprocessing["schema_digest"]:
        raise ValueError("schema_digest")
    active = tuple(frozen_preprocessing["active_indices"])
    if (not active or len(set(active)) != len(active)
            or any(type(index) is not int or index < 0 or index >= len(columns) for index in active)):
        raise ValueError("active_indices")
    policy_payload = frozen_preprocessing["policy"]
    if set(policy_payload) != {"numeric_imputation", "numeric_scaling", "optional_all_missing",
                               "constant_features", "category_encoding"}:
        raise ValueError("preprocessing_policy")
    policy = PreprocessingPolicy(**policy_payload)
    preprocessing = FrozenPreprocessingState(
        frozen_preprocessing["schema_digest"], frozen_preprocessing["medians"],
        frozen_preprocessing["means"], frozen_preprocessing["scales"], active,
        frozen_preprocessing["omissions"], policy,
    )
    estimator = payload["estimator_state"]
    if tuple(estimator.get("classes", ())) != (0, 1):
        raise ValueError("estimator_classes")
    if artifact.family == "l2_logistic":
        coefficients = tuple(float(value) for value in estimator["coefficients"])
        intercept = float(estimator["intercept"])
        if len(coefficients) != len(active) or any(not isfinite(value) for value in coefficients) or not isfinite(intercept):
            raise ValueError("estimator_shape")
        return _ReconstructedFeatureState(artifact.digest, artifact.scope, artifact.family,
                                           schema, preprocessing, (0, 1), coefficients, intercept)
    if artifact.family == "prevalence_baseline":
        probability = estimator["probability"]
        if type(probability) not in (int, float) or type(probability) is bool or not isfinite(probability):
            raise ValueError("estimator_probability")
        return _ReconstructedFeatureState(artifact.digest, artifact.scope, artifact.family,
                                           schema, preprocessing, (0, 1), probability=float(probability))
    raise ValueError("estimator_family")


def _reconstruct_scores(state: _ReconstructedFeatureState, rows):
    """Apply exact frozen Feature 005 transforms and privately reconstruct z/p0."""
    from safira.calibration.records import CalibrationStatus
    from safira.signals.base import SignalState
    from safira.signals.records import SignalFeatureRecord
    from safira.training.features import transform_rows

    if type(state) is not _ReconstructedFeatureState:
        raise ValueError("frozen_state")
    rows = tuple(rows)
    for row in rows:
        if type(row) is not SignalFeatureRecord or row.source_key.to_tuple() != state.scope.source_key:
            return _ScoreReconstruction((), CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
        indexed = {(item.method_id, item.method_version): item for item in row.predictors}
        for spec in state.schema.feature_specs:
            item = indexed.get((spec.method_id, spec.method_version))
            if item is None:
                if spec.required:
                    return _ScoreReconstruction((), CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE,
                                                "required_evidence_unavailable")
                continue
            if item.state is SignalState.INVALID:
                return _ScoreReconstruction((), CalibrationStatus.INVALID_INPUT, "input_invalid")
            if item.state is SignalState.NOT_READY:
                return _ScoreReconstruction((), CalibrationStatus.NOT_READY, "approval_missing")
            if item.state is not SignalState.AVAILABLE:
                allowed = (item.state.value in spec.allowed_nonvalue_states and spec.state_indicators)
                imputed = spec.kind is FeatureKind.NUMERIC and spec.method_id in state.preprocessing.medians
                usable = imputed if spec.kind is FeatureKind.NUMERIC else allowed
                if spec.required and not usable:
                    return _ScoreReconstruction((), CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE,
                                                "required_evidence_unavailable")
    try:
        transformed = transform_rows(state.preprocessing, state.schema, rows)
    except Exception:
        return _ScoreReconstruction((), CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    if any(len(item) != len(state.preprocessing.active_indices) for item in transformed):
        return _ScoreReconstruction((), CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    if state.family == "prevalence_baseline":
        p0 = state.probability
        if p0 is None or not isfinite(p0) or not 0.0 < p0 < 1.0:
            return _ScoreReconstruction((), CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure")
        return _ScoreReconstruction((p0,) * len(rows), artifact_digest=state.artifact_digest,
                                    source_key=state.scope.source_key,
                                    row_keys=tuple(row.row_key.value for row in rows))
    if state.family != "l2_logistic" or state.intercept is None:
        return _ScoreReconstruction((), CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    if (len(state.coefficients) != len(state.preprocessing.active_indices)
            or not isfinite(state.intercept)
            or any(not isfinite(value) for value in state.coefficients)):
        return _ScoreReconstruction((), CalibrationStatus.INVALID_INPUT, "input_invalid")
    scores = tuple(state.intercept + sum(coefficient * value
                                         for coefficient, value in zip(state.coefficients, row))
                   for row in transformed)
    if any(not isfinite(value) for value in scores):
        return _ScoreReconstruction((), CalibrationStatus.NUMERICAL_FAILURE, "numerical_failure")
    return _ScoreReconstruction(scores, artifact_digest=state.artifact_digest,
                                source_key=state.scope.source_key,
                                row_keys=tuple(row.row_key.value for row in rows))
