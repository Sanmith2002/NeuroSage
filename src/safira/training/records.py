"""Immutable Feature 005 scope, protocol, verification and outcome records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
import re
from types import MappingProxyType
from typing import Any

from safira.signals.base import SignalDimension, SignalState

_SAFE_FEATURE_OMISSIONS = frozenset({
    "no_numeric_v1_method", "unsupported_for_source", "not_applicable_for_scope", "method_not_approved",
})


def _artifact_keys(value, expected):
    if not isinstance(value, Mapping) or set(value) != set(expected):
        raise ValueError("artifact_fields")


def _reject_sensitive_keys(value):
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("artifact_field")
            normalized = key.lower()
            if any(part in normalized for part in ("patient_id", "patient_group_ref", "group_id", "row_key",
                                                    "correctness_target", "outcome", "protected",
                                                    "raw_observation", "vocabulary")):
                raise ValueError("artifact_sensitive_field")
            _reject_sensitive_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _reject_sensitive_keys(item)


def _identifier(value: str, field_name: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError(field_name)
    return value


def _freeze(value: Any, ancestors=frozenset()):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("nonfinite")
        return value
    if isinstance(value, Mapping):
        if id(value) in ancestors:
            raise ValueError("mapping")
        trail = ancestors | {id(value)}
        copied = {}
        for key, item in value.items():
            if type(key) is str:
                frozen_key = key
            elif isinstance(key, (tuple, list)) and all(type(part) is str for part in key):
                frozen_key = tuple(key)
            else:
                raise ValueError("mapping_key")
            copied[frozen_key] = _freeze(item, trail)
        return MappingProxyType(copied)
    if isinstance(value, (tuple, list)):
        if id(value) in ancestors:
            raise ValueError("sequence")
        trail = ancestors | {id(value)}
        return tuple(_freeze(item, trail) for item in value)
    raise ValueError("value")


def _plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {json.dumps(key, separators=(",", ":")) if isinstance(key, tuple) else key: _plain(item)
                for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class TrainingScope:
    model_id: str
    model_version: str
    label_id: str
    classifier_artifact_sha256: str
    adapter_id: str
    adapter_version: str
    adapter_fingerprint: str
    preprocessing_identity: object

    def __post_init__(self):
        for name in ("model_id", "model_version", "label_id"):
            _identifier(getattr(self, name), name)
        import re
        for name in ("classifier_artifact_sha256", "adapter_fingerprint"):
            if type(getattr(self, name)) is not str or re.fullmatch(r"[0-9a-f]{64}", getattr(self, name)) is None:
                raise ValueError(name)
        for name in ("adapter_id", "adapter_version"):
            _identifier(getattr(self, name), name)
        object.__setattr__(self, "preprocessing_identity", _freeze(self.preprocessing_identity))

    @property
    def source_key(self):
        return self.model_id, self.model_version, self.label_id

    def to_dict(self):
        return {"model_id": self.model_id, "model_version": self.model_version, "label_id": self.label_id,
                "classifier_artifact_sha256": self.classifier_artifact_sha256,
                "adapter_id": self.adapter_id, "adapter_version": self.adapter_version,
                "adapter_fingerprint": self.adapter_fingerprint,
                "preprocessing_identity": _plain(self.preprocessing_identity)}

    def __hash__(self):
        return hash((self.source_key, self.classifier_artifact_sha256, self.adapter_id,
                     self.adapter_version, self.adapter_fingerprint,
                     json.dumps(_plain(self.preprocessing_identity), sort_keys=True, separators=(",", ":"))))

    def __lt__(self, other):
        if not isinstance(other, TrainingScope):
            return NotImplemented
        return (self.source_key, self.classifier_artifact_sha256, self.adapter_id, self.adapter_version,
                self.adapter_fingerprint) < (other.source_key, other.classifier_artifact_sha256,
                                               other.adapter_id, other.adapter_version, other.adapter_fingerprint)


@dataclass(frozen=True)
class TrainingSupportCriteria:
    minimum_patient_groups: int
    correctness_class_minimums: Mapping[int, int] = field(default_factory=dict)

    def __post_init__(self):
        if type(self.minimum_patient_groups) is not int or self.minimum_patient_groups < 1:
            raise ValueError("adequacy")
        if not isinstance(self.correctness_class_minimums, Mapping):
            raise ValueError("adequacy")
        values = {}
        for target, minimum in self.correctness_class_minimums.items():
            if type(target) is not int or target not in (0, 1) or type(minimum) is not int or minimum < 1:
                raise ValueError("adequacy")
            values[target] = minimum
        object.__setattr__(self, "correctness_class_minimums", MappingProxyType(values))

    def to_dict(self):
        return {"minimum_patient_groups": self.minimum_patient_groups,
                "correctness_class_minimums": {str(key): value
                                                for key, value in self.correctness_class_minimums.items()}}


class FeatureKind(str, Enum):
    NUMERIC = "numeric"
    SEEN_UNSEEN = "seen_unseen"


@dataclass(frozen=True)
class FeatureSpec:
    """Protocol-approved mapping from one exact Feature 004 method to predictors."""
    method_id: str
    method_version: str
    meaning: str
    dimension: SignalDimension
    kind: FeatureKind
    method_parameters: Mapping[str, Any] = field(default_factory=dict)
    required: bool | None = None
    state_indicators: bool | None = None
    allowed_nonvalue_states: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("method_id", "method_version", "meaning"):
            _identifier(getattr(self, name), name)
        if type(self.dimension) is not SignalDimension or type(self.kind) is not FeatureKind:
            raise ValueError("feature_spec")
        if type(self.required) is not bool or type(self.state_indicators) is not bool:
            raise ValueError("feature_spec")
        object.__setattr__(self, "method_parameters", _freeze(self.method_parameters))
        states = tuple(self.allowed_nonvalue_states)
        allowed = {item.value for item in SignalState} - {SignalState.AVAILABLE.value,
                                                          SignalState.INVALID.value,
                                                          SignalState.NOT_READY.value}
        if any(type(state) is not str or state not in allowed for state in states) or len(set(states)) != len(states):
            raise ValueError("feature_states")
        object.__setattr__(self, "allowed_nonvalue_states", states)
        if states and not self.state_indicators:
            raise ValueError("feature_state_indicators_required")
        if self.kind is FeatureKind.SEEN_UNSEEN and self.dimension is not SignalDimension.DOMAIN_FAMILIARITY:
            raise ValueError("feature_kind_dimension")

    def to_dict(self):
        return {"method_id": self.method_id, "method_version": self.method_version,
                "meaning": self.meaning, "dimension": self.dimension.value, "kind": self.kind.value,
                "method_parameters": _plain(self.method_parameters), "required": self.required,
                "state_indicators": self.state_indicators,
                "allowed_nonvalue_states": list(self.allowed_nonvalue_states)}


@dataclass(frozen=True)
class FeaturePolicy:
    features: tuple[FeatureSpec, ...]
    omitted_dimensions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        features = tuple(self.features)
        if any(type(item) is not FeatureSpec for item in features):
            raise ValueError("feature_policy")
        keys = [(item.method_id, item.method_version) for item in features]
        if len(keys) != len(set(keys)) or len({item.method_id for item in features}) != len(features):
            raise ValueError("feature_policy_duplicate")
        object.__setattr__(self, "features", features)
        omissions = dict(self.omitted_dimensions)
        dimensions = {item.value for item in SignalDimension}
        if any(type(key) is not str or key not in dimensions or type(reason) is not str
               or reason not in _SAFE_FEATURE_OMISSIONS
               for key, reason in omissions.items()):
            raise ValueError("feature_omission")
        if any(item.dimension.value in omissions for item in features):
            raise ValueError("feature_omission_conflict")
        object.__setattr__(self, "omitted_dimensions", MappingProxyType(omissions))

    def to_dict(self):
        return {"features": [item.to_dict() for item in self.features],
                "omitted_dimensions": dict(self.omitted_dimensions)}


@dataclass(frozen=True)
class PreprocessingPolicy:
    """Explicit transformations approved before validation is inspected."""
    constant_features: str
    category_encoding: str
    numeric_imputation: Mapping[str, str] = field(default_factory=dict)
    numeric_scaling: Mapping[str, str] = field(default_factory=dict)
    optional_all_missing: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        for name, choices in (("numeric_imputation", {"median", "none"}),
                              ("numeric_scaling", {"standard", "none"}),
                              ("optional_all_missing", {"omit", "fail"})):
            values = dict(getattr(self, name))
            if any(type(key) is not str or not key or value not in choices
                   for key, value in values.items()):
                raise ValueError("preprocessing_policy")
            object.__setattr__(self, name, MappingProxyType(values))
        if self.constant_features not in {"keep", "drop"} or self.category_encoding != "one_hot_seen_unseen":
            raise ValueError("preprocessing_policy")

    def to_dict(self):
        return {"numeric_imputation": dict(self.numeric_imputation),
                "numeric_scaling": dict(self.numeric_scaling),
                "optional_all_missing": dict(self.optional_all_missing),
                "constant_features": self.constant_features, "category_encoding": self.category_encoding}


@dataclass(frozen=True)
class LogisticCandidateConfig:
    approved: bool
    C: float
    tol: float
    max_iter: int

    def __post_init__(self):
        if (type(self.approved) is not bool or type(self.C) not in (int, float) or not isfinite(self.C)
                or self.C <= 0 or type(self.tol) not in (int, float) or not isfinite(self.tol)
                or self.tol <= 0 or type(self.max_iter) is not int or self.max_iter < 1):
            raise ValueError("logistic_config")

    def to_dict(self):
        return {"approved": self.approved, "C": float(self.C), "tol": float(self.tol),
                "max_iter": self.max_iter, "penalty": "l2", "solver": "lbfgs",
                "class_weight": None, "fit_intercept": True, "warm_start": False}


@dataclass(frozen=True)
class ValidationSupportCriteria:
    """Protocol-declared independent-group and class support for selection."""
    minimum_patient_groups: int
    correctness_class_minimums: Mapping[int, int] = field(default_factory=dict)
    disclose_support: bool = False

    def __post_init__(self):
        if type(self.minimum_patient_groups) is not int or self.minimum_patient_groups < 1:
            raise ValueError("validation_adequacy")
        if type(self.disclose_support) is not bool or not isinstance(self.correctness_class_minimums, Mapping):
            raise ValueError("validation_adequacy")
        values = dict(self.correctness_class_minimums)
        if any(type(key) is not int or key not in (0, 1) or type(value) is not int or value < 1
               for key, value in values.items()):
            raise ValueError("validation_adequacy")
        object.__setattr__(self, "correctness_class_minimums", MappingProxyType(values))

    def to_dict(self):
        return {"minimum_patient_groups": self.minimum_patient_groups,
                "correctness_class_minimums": {str(k): v for k, v in self.correctness_class_minimums.items()},
                "disclose_support": self.disclose_support}


class CandidateFailurePolicy(str, Enum):
    REQUIRE_ALL = "require_all"
    ALLOW_REMAINING = "allow_remaining"


@dataclass(frozen=True)
class TrainingProtocol:
    protocol_id: str
    version: str
    scopes: tuple[TrainingScope, ...]
    adequacy: Mapping[tuple[str, str, str], TrainingSupportCriteria]
    required_signal_methods: Mapping[tuple[str, str, str], tuple[str, ...]]
    feature_policies: Mapping[tuple[str, str, str], FeaturePolicy] = field(default_factory=dict)
    preprocessing_policies: Mapping[tuple[str, str, str], PreprocessingPolicy] = field(default_factory=dict)
    logistic_configs: Mapping[tuple[str, str, str], LogisticCandidateConfig] = field(default_factory=dict)
    validation_adequacy: Mapping[tuple[str, str, str], ValidationSupportCriteria] = field(default_factory=dict)
    candidate_failure_policies: Mapping[tuple[str, str, str], CandidateFailurePolicy] = field(default_factory=dict)

    def __post_init__(self):
        _identifier(self.protocol_id, "protocol_id")
        _identifier(self.version, "protocol_version")
        scopes = tuple(self.scopes)
        if (not scopes or any(type(scope) is not TrainingScope for scope in scopes)
                or len({scope.source_key for scope in scopes}) != len(scopes)):
            raise ValueError("scopes")
        object.__setattr__(self, "scopes", tuple(sorted(scopes)))
        allowed = {scope.source_key for scope in scopes}
        if not isinstance(self.adequacy, Mapping):
            raise ValueError("adequacy")
        adequacy = dict(self.adequacy)
        if any(tuple(key) not in allowed or type(value) is not TrainingSupportCriteria
               for key, value in adequacy.items()):
            raise ValueError("adequacy")
        object.__setattr__(self, "adequacy", MappingProxyType({tuple(key): value for key, value in adequacy.items()}))
        if not isinstance(self.required_signal_methods, Mapping):
            raise ValueError("required_signal_methods")
        required = {}
        for key, methods in self.required_signal_methods.items():
            normalized = tuple(key)
            if normalized not in allowed or not isinstance(methods, (tuple, list)):
                raise ValueError("required_signal_methods")
            methods = tuple(_identifier(method, "required_signal_method") for method in methods)
            if len(methods) != len(set(methods)):
                raise ValueError("required_signal_methods")
            required[normalized] = methods
        object.__setattr__(self, "required_signal_methods", MappingProxyType(required))
        for name, expected in (("feature_policies", FeaturePolicy),
                               ("preprocessing_policies", PreprocessingPolicy),
                               ("logistic_configs", LogisticCandidateConfig),
                               ("validation_adequacy", ValidationSupportCriteria),
                               ("candidate_failure_policies", CandidateFailurePolicy)):
            supplied = getattr(self, name)
            if not isinstance(supplied, Mapping):
                raise ValueError(name)
            normalized = {}
            for key, value in supplied.items():
                normalized_key = tuple(key)
                if normalized_key not in allowed or (value is not expected and type(value) is not expected):
                    raise ValueError(name)
                normalized[normalized_key] = value
            object.__setattr__(self, name, MappingProxyType(normalized))

    def to_dict(self):
        encode = lambda key: json.dumps(list(key), separators=(",", ":"))
        return {
            "protocol_id": self.protocol_id, "version": self.version,
            "scopes": [scope.to_dict() for scope in self.scopes],
            "adequacy": {encode(key): value.to_dict() for key, value in self.adequacy.items()},
            "required_signal_methods": {encode(key): list(value)
                                         for key, value in self.required_signal_methods.items()},
            "feature_policies": {encode(key): value.to_dict() for key, value in self.feature_policies.items()},
            "preprocessing_policies": {encode(key): value.to_dict()
                                        for key, value in self.preprocessing_policies.items()},
            "logistic_configs": {encode(key): value.to_dict() for key, value in self.logistic_configs.items()},
            "validation_adequacy": {encode(key): value.to_dict() for key, value in self.validation_adequacy.items()},
            "candidate_failure_policies": {encode(key): value.value
                                            for key, value in self.candidate_failure_policies.items()},
        }


class TrainingStatus(str, Enum):
    ELIGIBLE_FOR_CANDIDATE_FITTING = "ELIGIBLE_FOR_CANDIDATE_FITTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_READY = "NOT_READY"
    UNAVAILABLE_REQUIRED_EVIDENCE = "UNAVAILABLE_REQUIRED_EVIDENCE"
    INVALID_INPUT = "INVALID_INPUT"
    INCOMPATIBLE_INPUT = "INCOMPATIBLE_INPUT"
    COMPARISON_UNDEFINED = "COMPARISON_UNDEFINED"
    SELECTED_BASELINE = "SELECTED_BASELINE"
    SELECTED_LOGISTIC = "SELECTED_LOGISTIC"


_SAFE_REASON_CODES = frozenset({
    "scope_protocol_incomplete", "patient_group_support_insufficient",
    "correctness_class_support_insufficient", "aligned_training_features_unavailable",
    "signal_input_invalid", "signal_provenance_not_ready", "signal_method_duplicate",
    "required_signal_unavailable", "training_rows_unavailable", "validation_rows_unavailable",
    "candidate_fitting_helpers_internal_only", "training_outcome_unavailable",
    "training_class_support_insufficient", "training_candidate_unavailable",
    "candidate_comparison_insufficient", "training_comparison_undefined",
    "training_candidate_failed", "training_features_invalid",
})


@dataclass(frozen=True)
class TrainingOutcome:
    scope: TrainingScope
    status: TrainingStatus
    reason_code: str | None = None
    limitations: tuple[str, ...] = ()
    artifact: object | None = None

    def __post_init__(self):
        if type(self.scope) is not TrainingScope or type(self.status) is not TrainingStatus:
            raise ValueError("outcome")
        if self.reason_code is not None:
            _identifier(self.reason_code, "reason_code")
            if self.reason_code not in _SAFE_REASON_CODES:
                object.__setattr__(self, "reason_code", "training_outcome_unavailable")
        limitations = tuple(self.limitations)
        if any(type(item) is not str for item in limitations):
            raise ValueError("limitations")
        object.__setattr__(self, "limitations", limitations)
        if self.status in (TrainingStatus.SELECTED_BASELINE, TrainingStatus.SELECTED_LOGISTIC):
            if type(self.artifact) is not SafetyEstimatorArtifact:
                raise ValueError("selected_artifact_required")
        elif self.artifact is not None:
            raise ValueError("non_success_artifact_forbidden")

    def to_dict(self):
        return {"scope": self.scope.to_dict(), "status": self.status.value,
                "reason_code": self.reason_code, "limitations": list(self.limitations),
                "artifact": None if self.artifact is None else self.artifact.to_dict()}


@dataclass(frozen=True)
class SafetyEstimatorArtifact:
    """Allowlisted intermediate estimator state; never a runtime inference object."""
    scope: TrainingScope
    family: str
    feature_schema: Mapping[str, Any]
    preprocessing: Mapping[str, Any]
    training_protocol: Mapping[str, Any]
    dataset_reference: Mapping[str, Any]
    signal_run_reference: Mapping[str, Any]
    estimator_state: Mapping[str, Any]
    candidate_configuration: Mapping[str, Any]
    dependency_versions: Mapping[str, str]
    training_metrics: Mapping[str, Any]
    selection_metrics: Mapping[str, Any]
    limitations: tuple[str, ...] = ()
    artifact_version: str = "safira-correctness-estimator-v1"
    lifecycle: str = "uncalibrated_non_deployable"
    calibrated: bool = False
    deployable: bool = False
    validation_spent: bool = True
    calibration_reserved: bool = True
    protected_test_accessed: bool = False
    digest: str = ""

    def __post_init__(self):
        if type(self.scope) is not TrainingScope or self.family not in ("prevalence_baseline", "l2_logistic"):
            raise ValueError("artifact_scope")
        limits = tuple(self.limitations)
        if any(type(item) is not str for item in limits):
            raise ValueError("artifact_limitations")
        object.__setattr__(self, "limitations", limits)
        _identifier(self.artifact_version, "artifact_version")
        if (self.lifecycle != "uncalibrated_non_deployable" or self.calibrated or self.deployable
                or not self.validation_spent or not self.calibration_reserved or self.protected_test_accessed):
            raise ValueError("artifact_lifecycle")
        for name in ("feature_schema", "preprocessing", "training_protocol", "dataset_reference", "signal_run_reference",
                     "estimator_state", "candidate_configuration", "dependency_versions",
                     "training_metrics", "selection_metrics"):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise ValueError("artifact_mapping")
            _reject_sensitive_keys(value)
            object.__setattr__(self, name, _freeze(value))
        _artifact_keys(self.feature_schema, ("scope", "columns", "feature_specs", "omitted_dimensions"))
        _artifact_keys(self.preprocessing, ("schema_digest", "medians", "means", "scales", "active_indices",
                                            "omissions", "policy"))
        _artifact_keys(self.training_protocol, ("protocol_id", "version", "protocol_digest"))
        if re.fullmatch(r"[0-9a-f]{64}", self.training_protocol["protocol_digest"]) is None:
            raise ValueError("artifact_protocol_digest")
        _artifact_keys(self.dataset_reference, ("dataset_id", "manifest_reference", "manifest_digest",
            "protocol_id", "protocol_version", "builder_version", "dataset_fingerprint",
            "admitted_inventory_digest"))
        _artifact_keys(self.signal_run_reference, ("run_version", "feature_set_fingerprint", "method_ids",
                                                    "fitted_state_ids", "scope_key"))
        _artifact_keys(self.training_metrics, ("role", "selected_candidate_brier"))
        _artifact_keys(self.selection_metrics, ("role", "brier_scores", "secondary", "selected_family",
            "tie_rule", "validation_spent", "disclosed_support"))
        if self.family == "prevalence_baseline":
            _artifact_keys(self.estimator_state, ("probability", "classes"))
        else:
            _artifact_keys(self.estimator_state, ("coefficients", "intercept", "classes"))
        _artifact_keys(self.candidate_configuration, ("logistic", "candidate_failure_policy", "selection_metric"))
        if set(self.dependency_versions) != {"scikit_learn", "numpy", "scipy", "joblib", "threadpoolctl"}:
            raise ValueError("artifact_dependency_versions")
        for name in ("manifest_digest", "dataset_fingerprint", "admitted_inventory_digest"):
            if re.fullmatch(r"[0-9a-f]{64}", self.dataset_reference[name]) is None:
                raise ValueError("artifact_dataset_digest")
        for name in ("feature_set_fingerprint",):
            if re.fullmatch(r"[0-9a-f]{64}", self.signal_run_reference[name]) is None:
                raise ValueError("artifact_signal_digest")
        if (tuple(self.signal_run_reference["scope_key"]) != self.scope.source_key
                or self.training_metrics["role"] != "train"
                or self.selection_metrics["role"] != "selection_evidence"
                or self.selection_metrics["selected_family"] != self.family
                or self.selection_metrics["validation_spent"] is not True
                or self.selection_metrics["tie_rule"] != "exact_equality_prefers_prevalence_baseline"):
            raise ValueError("artifact_lifecycle_metadata")
        for column in self.feature_schema["columns"]:
            _artifact_keys(column, ("name", "method_id", "method_version", "meaning", "kind", "state"))
        for spec in self.feature_schema["feature_specs"]:
            _artifact_keys(spec, ("method_id", "method_version", "meaning", "dimension", "kind",
                                  "method_parameters_sha256", "required", "state_indicators",
                                  "allowed_nonvalue_states"))
            if re.fullmatch(r"[0-9a-f]{64}", spec["method_parameters_sha256"]) is None:
                raise ValueError("artifact_feature_parameters")
        active = self.preprocessing["active_indices"]
        columns = self.feature_schema["columns"]
        if (not active or len(set(active)) != len(active)
                or any(type(index) is not int or index < 0 or index >= len(columns) for index in active)):
            raise ValueError("artifact_preprocessing_shape")
        if tuple(self.estimator_state["classes"]) != (0, 1):
            raise ValueError("artifact_estimator_classes")
        if self.family == "prevalence_baseline":
            probability = self.estimator_state["probability"]
            if type(probability) not in (int, float) or type(probability) is bool or not isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError("artifact_estimator_state")
        else:
            coefficients, intercept = self.estimator_state["coefficients"], self.estimator_state["intercept"]
            if (not isinstance(coefficients, (tuple, list)) or len(coefficients) != len(active)
                    or any(type(value) not in (int, float) or type(value) is bool or not isfinite(value)
                           for value in coefficients)
                    or type(intercept) not in (int, float) or type(intercept) is bool or not isfinite(intercept)):
                raise ValueError("artifact_estimator_state")
        for method in self.signal_run_reference["method_ids"]:
            if (len(method) != 3 or any(type(value) is not str or not value for value in method)
                    or re.fullmatch(r"[0-9a-f]{64}", method[2]) is None):
                raise ValueError("artifact_signal_method")
        if any(type(value) is not str or not value for value in self.signal_run_reference["fitted_state_ids"]):
            raise ValueError("artifact_fitted_state")
        if any(type(value) is not str or not value for value in self.dependency_versions.values()):
            raise ValueError("artifact_dependency_versions")
        if type(self.training_metrics["selected_candidate_brier"]) not in (int, float) or not (
                0 <= self.training_metrics["selected_candidate_brier"] <= 1):
            raise ValueError("artifact_training_metrics")
        if set(self.selection_metrics["brier_scores"]) - {"prevalence_baseline", "l2_logistic"}:
            raise ValueError("artifact_selection_metrics")
        if any(type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1
               for value in self.selection_metrics["brier_scores"].values()):
            raise ValueError("artifact_selection_metrics")
        for family, metrics in self.selection_metrics["secondary"].items():
            if family not in ("prevalence_baseline", "l2_logistic"):
                raise ValueError("artifact_selection_metrics")
            for metric in metrics.values():
                _artifact_keys(metric, ("value", "state", "reason_code"))
                if metric["state"] == "available":
                    if type(metric["value"]) not in (int, float) or not isfinite(metric["value"]):
                        raise ValueError("artifact_selection_metrics")
                elif metric["state"] != "undefined" or metric["value"] is not None:
                    raise ValueError("artifact_selection_metrics")
        for name, value in self.dependency_versions.items():
            _identifier(value, "dependency_version")
        disclosed = self.selection_metrics["disclosed_support"]
        if disclosed:
            _artifact_keys(disclosed, ("patient_group_count", "correctness_class_support"))
            _artifact_keys(disclosed["correctness_class_support"], ("0", "1"))
            if (type(disclosed["patient_group_count"]) is not int or disclosed["patient_group_count"] < 0
                    or any(type(value) is not int or value < 0
                           for value in disclosed["correctness_class_support"].values())):
                raise ValueError("artifact_disclosed_support")
        safe_limitations = {"uncalibrated", "non_deployable", "validation_selection_not_final_performance",
                            "future_policy_evidence_not_authorized"}
        if any(item not in safe_limitations for item in limits):
            raise ValueError("artifact_limitations")
        body = self._body()
        expected = sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        if self.digest and self.digest != expected:
            raise ValueError("artifact_digest")
        object.__setattr__(self, "digest", expected)

    def _body(self):
        return {"artifact_version": self.artifact_version, "scope": self.scope.to_dict(),
                "family": self.family, "feature_schema": _plain(self.feature_schema),
                "preprocessing": _plain(self.preprocessing), "training_protocol": _plain(self.training_protocol),
                "dataset_reference": _plain(self.dataset_reference),
                "signal_run_reference": _plain(self.signal_run_reference),
                "estimator_state": _plain(self.estimator_state),
                "candidate_configuration": _plain(self.candidate_configuration),
                "dependency_versions": _plain(self.dependency_versions),
                "training_metrics": _plain(self.training_metrics),
                "selection_metrics": _plain(self.selection_metrics), "limitations": list(self.limitations),
                "lifecycle": self.lifecycle, "calibrated": False, "deployable": False,
                "validation_spent": True, "calibration_reserved": True, "protected_test_accessed": False}

    def to_dict(self):
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, Mapping):
            raise ValueError("artifact_payload")
        scope_data = payload.get("scope")
        if not isinstance(scope_data, Mapping):
            raise ValueError("artifact_scope")
        scope = TrainingScope(**dict(scope_data))
        allowed = {"artifact_version", "scope", "family", "feature_schema", "preprocessing",
                   "training_protocol", "dataset_reference", "signal_run_reference", "estimator_state", "candidate_configuration",
                   "dependency_versions", "training_metrics", "selection_metrics", "limitations", "lifecycle",
                   "calibrated", "deployable", "validation_spent", "calibration_reserved",
                   "protected_test_accessed", "digest"}
        if set(payload) != allowed:
            raise ValueError("artifact_fields")
        return cls(scope=scope, family=payload["family"], feature_schema=payload["feature_schema"],
                   preprocessing=payload["preprocessing"], training_protocol=payload["training_protocol"],
                   dataset_reference=payload["dataset_reference"],
                   signal_run_reference=payload["signal_run_reference"], estimator_state=payload["estimator_state"],
                   candidate_configuration=payload["candidate_configuration"],
                   dependency_versions=payload["dependency_versions"], training_metrics=payload["training_metrics"],
                   selection_metrics=payload["selection_metrics"], limitations=tuple(payload["limitations"]),
                   artifact_version=payload["artifact_version"], lifecycle=payload["lifecycle"],
                   calibrated=payload["calibrated"], deployable=payload["deployable"],
                   validation_spent=payload["validation_spent"], calibration_reserved=payload["calibration_reserved"],
                   protected_test_accessed=payload["protected_test_accessed"], digest=payload["digest"])


@dataclass(frozen=True)
class TrainingInputCheck:
    """Provider response compared with actual content; not a credential by itself."""

    dataset_fingerprint: str
    feature_set_fingerprint: str
    dataset_id: str
    protocol_id: str
    protocol_version: str
    manifest_reference: str
    manifest_digest: str
    builder_version: str
    feature_run_version: str
    feature_method_ids: tuple[tuple[str, str, str], ...]
    fitted_state_ids: tuple[str, ...]
    row_inventory: tuple[tuple[object, ...], ...] = field(repr=False)
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""

    def __post_init__(self):
        for name in ("dataset_fingerprint", "feature_set_fingerprint", "dataset_id", "protocol_id",
                     "protocol_version", "manifest_reference", "manifest_digest", "builder_version",
                     "feature_run_version", "authority", "method", "evidence_ref"):
            _identifier(getattr(self, name), name)
        if re.fullmatch(r"[0-9a-f]{64}", self.manifest_digest) is None:
            raise ValueError("manifest_digest")
        methods = tuple(tuple(item) for item in self.feature_method_ids)
        if any(len(item) != 3 or any(type(value) is not str or not value for value in item) for item in methods):
            raise ValueError("feature_methods")
        object.__setattr__(self, "feature_method_ids", methods)
        states = tuple(self.fitted_state_ids)
        if any(type(value) is not str or not value for value in states):
            raise ValueError("fitted_states")
        object.__setattr__(self, "fitted_state_ids", states)
        inventory = tuple(_freeze(tuple(item)) for item in self.row_inventory)
        if any(len(item) != 5 for item in inventory):
            raise ValueError("row_inventory")
        object.__setattr__(self, "row_inventory", inventory)
