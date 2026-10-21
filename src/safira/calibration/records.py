"""Immutable Feature 006 protocol and status records.

These records describe admission/readiness only in Batch A; they do not expose
calibrated predictions or fitting behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any

from safira.training.records import TrainingScope


def _freeze(value: Any, ancestors=frozenset()):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("protocol_value")
        return value
    if isinstance(value, Mapping):
        if id(value) in ancestors:
            raise ValueError("protocol_value")
        trail = ancestors | {id(value)}
        copied = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("protocol_value")
            copied[key] = _freeze(item, trail)
        return MappingProxyType(copied)
    if isinstance(value, (tuple, list)):
        if id(value) in ancestors:
            raise ValueError("protocol_value")
        trail = ancestors | {id(value)}
        return tuple(_freeze(item, trail) for item in value)
    raise ValueError("protocol_value")


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


class CalibrationStatus(str, Enum):
    CALIBRATOR_FITTED_UNEVALUATED = "CALIBRATOR_FITTED_UNEVALUATED"
    NOT_READY = "NOT_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNAVAILABLE_REQUIRED_EVIDENCE = "UNAVAILABLE_REQUIRED_EVIDENCE"
    INVALID_INPUT = "INVALID_INPUT"
    INCOMPATIBLE_INPUT = "INCOMPATIBLE_INPUT"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"


_SAFE_REASONS = frozenset({
    "approval_missing", "support_insufficient", "required_evidence_unavailable",
    "input_invalid", "verification_rejected", "scope_incompatible", "numerical_failure",
    "admission_complete",
})


@dataclass(frozen=True)
class CalibrationProtocol:
    """Versioned exact-scope protocol; empty configuration is explicitly unapproved."""

    protocol_id: str
    version: str
    scopes: tuple[TrainingScope, ...]
    configuration: Mapping[str, Any] = field(default_factory=dict)
    lifecycle: str = "calibration_only"
    required_settings: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("protocol_id", "version"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip() or value != value.strip():
                raise ValueError("protocol_identity")
        scopes = tuple(self.scopes)
        if not scopes or any(type(item) is not TrainingScope for item in scopes):
            raise ValueError("protocol_scopes")
        keys = [scope.source_key for scope in scopes]
        if len(keys) != len(set(keys)):
            raise ValueError("protocol_scopes")
        if self.lifecycle != "calibration_only":
            raise ValueError("protocol_lifecycle")
        settings = tuple(self.required_settings)
        if any(type(item) is not str or not item.strip() for item in settings) or len(settings) != len(set(settings)):
            raise ValueError("protocol_settings")
        object.__setattr__(self, "scopes", scopes)
        object.__setattr__(self, "required_settings", settings)
        object.__setattr__(self, "configuration", _freeze(self.configuration))

    @property
    def ready(self) -> bool:
        return bool(self.required_settings) and all(
            key in self.configuration and self.configuration[key] is not None
            for key in self.required_settings
        )

    def to_dict(self):
        return {"protocol_id": self.protocol_id, "version": self.version,
                "scopes": [scope.to_dict() for scope in self.scopes],
                "configuration": _plain(self.configuration), "lifecycle": self.lifecycle,
                "required_settings": list(self.required_settings)}


@dataclass(frozen=True)
class CalibrationOutcome:
    scope: TrainingScope
    status: CalibrationStatus
    reason_code: str
    artifact: object | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.scope) is not TrainingScope or type(self.status) is not CalibrationStatus:
            raise ValueError("outcome")
        if type(self.reason_code) is not str or self.reason_code not in _SAFE_REASONS:
            raise ValueError("outcome_reason")
        if self.status is CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED:
            if type(self.artifact) is not CalibratorArtifact:
                raise ValueError("outcome_artifact_required")
        elif self.artifact is not None:
            raise ValueError("outcome_non_success_artifact")
        limitations = tuple(self.limitations)
        if any(item not in {"unevaluated", "non_deployable", "not_clinically_validated"}
               for item in limitations):
            raise ValueError("outcome_limitations")
        object.__setattr__(self, "limitations", limitations)

    def to_dict(self):
        return {"scope": self.scope.to_dict(), "status": self.status.value,
                "reason_code": self.reason_code, "limitations": list(self.limitations),
                "artifact": None if self.artifact is None else self.artifact.to_dict()}


@dataclass(frozen=True, repr=False)
class CalibratorArtifact:
    """Safe, immutable record of one fitted but unevaluated calibration mapping."""

    scope: TrainingScope
    base_artifact_digest: str
    base_artifact_version: str
    base_family: str
    base_feature_schema_digest: str
    base_preprocessing_digest: str
    dataset_reference: Mapping[str, Any]
    signal_run_reference: Mapping[str, Any]
    calibration_protocol: Mapping[str, Any]
    method_id: str
    method_version: str
    mapping: Mapping[str, Any]
    fitting_configuration: Mapping[str, Any]
    dependency_versions: Mapping[str, str]
    lifecycle: Mapping[str, Any]
    artifact_version: str = "safira-calibrator-v1"
    digest: str = ""

    def __post_init__(self):
        if type(self.scope) is not TrainingScope:
            raise ValueError("artifact_scope")
        for name in ("base_artifact_digest", "base_feature_schema_digest",
                     "base_preprocessing_digest"):
            if type(getattr(self, name)) is not str or re.fullmatch(r"[0-9a-f]{64}", getattr(self, name)) is None:
                raise ValueError("artifact_identity")
        for name in ("base_artifact_version", "method_id", "method_version", "artifact_version"):
            if type(getattr(self, name)) is not str or not getattr(self, name).strip():
                raise ValueError("artifact_identity")
        if self.base_family not in ("l2_logistic", "prevalence_baseline"):
            raise ValueError("artifact_family")
        if (self.artifact_version != "safira-calibrator-v1"
                or self.base_artifact_version != "safira-correctness-estimator-v1"
                or self.method_version != "1"):
            raise ValueError("artifact_version")
        for name in ("dataset_reference", "signal_run_reference", "calibration_protocol",
                     "mapping", "fitting_configuration", "dependency_versions", "lifecycle"):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise ValueError("artifact_mapping")
            object.__setattr__(self, name, _freeze(value))
        _exact_keys(self.dataset_reference, {"dataset_id", "manifest_reference", "manifest_digest",
            "protocol_id", "protocol_version", "builder_version", "inventory_digest"})
        _exact_keys(self.signal_run_reference, {"run_version", "feature_set_fingerprint", "method_ids",
            "fitted_state_ids", "scope_key"})
        _exact_keys(self.calibration_protocol, {"protocol_id", "version", "configuration_digest"})
        _exact_keys(self.lifecycle, {"status", "not_independently_evaluated", "non_deployable",
            "not_clinically_validated", "calibration_partition_spent", "protected_test_accessed",
            "validation_selection_spent"})
        if (tuple(self.signal_run_reference["scope_key"]) != self.scope.source_key
                or not all(type(self.dataset_reference[k]) is str and self.dataset_reference[k]
                           for k in ("dataset_id", "manifest_reference", "protocol_id", "protocol_version", "builder_version"))
                or not all(type(self.calibration_protocol[k]) is str and self.calibration_protocol[k]
                           for k in ("protocol_id", "version"))):
            raise ValueError("artifact_provenance")
        for name in ("manifest_digest", "inventory_digest"):
            if re.fullmatch(r"[0-9a-f]{64}", self.dataset_reference[name]) is None:
                raise ValueError("artifact_provenance")
        if (re.fullmatch(r"[0-9a-f]{64}", self.signal_run_reference["feature_set_fingerprint"]) is None
                or re.fullmatch(r"[0-9a-f]{64}", self.calibration_protocol["configuration_digest"]) is None):
            raise ValueError("artifact_provenance")
        if any(type(item) is not str or not item for item in self.signal_run_reference["fitted_state_ids"]):
            raise ValueError("artifact_provenance")
        if any(len(item) != 3 or any(type(part) is not str or not part for part in item)
               or re.fullmatch(r"[0-9a-f]{64}", item[2]) is None
               for item in self.signal_run_reference["method_ids"]):
            raise ValueError("artifact_provenance")
        if (self.lifecycle["status"] != CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED.value
                or self.lifecycle["not_independently_evaluated"] is not True
                or self.lifecycle["non_deployable"] is not True
                or self.lifecycle["not_clinically_validated"] is not True
                or self.lifecycle["calibration_partition_spent"] is not True
                or self.lifecycle["protected_test_accessed"] is not False
                or self.lifecycle["validation_selection_spent"] is not True):
            raise ValueError("artifact_lifecycle")
        if self.base_family == "l2_logistic":
            _exact_keys(self.mapping, {"intercept", "slope", "input_semantics"})
            if (self.mapping["input_semantics"] != "feature005_logistic_linear_predictor"
                    or not _finite(self.mapping["intercept"])
                    or not _finite(self.mapping["slope"]) or self.mapping["slope"] <= 0):
                raise ValueError("artifact_parameters")
            _exact_keys(self.fitting_configuration, {"solver", "penalty", "fit_intercept", "class_weight",
                "warm_start", "tol", "max_iter", "occurrence_weighting", "convergence_criterion",
                "deterministic_expectation", "score_identifiability_criterion", "separation_criterion",
                "slope_rule", "converged", "iterations"})
            if (self.method_id != "logistic_calibration_v1" or self.fitting_configuration["solver"] != "lbfgs"
                    or self.fitting_configuration["penalty"] is not None
                    or self.fitting_configuration["fit_intercept"] is not True
                    or self.fitting_configuration["class_weight"] is not None
                    or self.fitting_configuration["warm_start"] is not False
                    or self.fitting_configuration["occurrence_weighting"] != "unit_per_occurrence"
                    or not _finite(self.fitting_configuration["tol"])
                    or self.fitting_configuration["tol"] <= 0
                    or type(self.fitting_configuration["max_iter"]) is not int
                    or self.fitting_configuration["max_iter"] < 1
                    or self.fitting_configuration["convergence_criterion"] != "warning_and_iteration_limit_v1"
                    or self.fitting_configuration["deterministic_expectation"] != "same_environment_repeat_v1"
                    or self.fitting_configuration["score_identifiability_criterion"] != "intercept_plus_score_full_rank_v1"
                    or self.fitting_configuration["separation_criterion"] != "scalar_range_ordering_v1"
                    or self.fitting_configuration["slope_rule"] != "strictly_positive"
                    or self.fitting_configuration["converged"] is not True
                    or type(self.fitting_configuration["iterations"]) is not int
                    or not 1 <= self.fitting_configuration["iterations"] <= self.fitting_configuration["max_iter"]):
                raise ValueError("artifact_configuration")
        else:
            _exact_keys(self.mapping, {"base_probability", "offset", "constant_probability",
                "constant_output", "no_individualized_discrimination"})
            if (not _finite(self.mapping["base_probability"]) or not 0 < self.mapping["base_probability"] < 1
                    or not _finite(self.mapping["offset"])
                    or not _finite(self.mapping["constant_probability"])
                    or not 0 < self.mapping["constant_probability"] < 1
                    or self.mapping["constant_output"] is not True
                    or self.mapping["no_individualized_discrimination"] is not True
                    or self.method_id != "prevalence_offset_v1"):
                raise ValueError("artifact_parameters")
            _exact_keys(self.fitting_configuration, {"occurrence_weighting", "closed_form", "converged", "iterations"})
            if (self.fitting_configuration["occurrence_weighting"] != "unit_per_occurrence"
                    or self.fitting_configuration["closed_form"] is not True
                    or self.fitting_configuration["converged"] is not True
                    or self.fitting_configuration["iterations"] != 0):
                raise ValueError("artifact_configuration")
        if (not self.dependency_versions or any(type(k) is not str or not k
                or type(v) is not str or not v for k, v in self.dependency_versions.items())):
            raise ValueError("artifact_dependencies")
        expected = _artifact_digest(self._body())
        if self.digest and self.digest != expected:
            raise ValueError("artifact_digest")
        object.__setattr__(self, "digest", expected)

    def _body(self):
        return {"artifact_version": self.artifact_version, "scope": self.scope.to_dict(),
            "base_artifact_digest": self.base_artifact_digest,
            "base_artifact_version": self.base_artifact_version, "base_family": self.base_family,
            "base_feature_schema_digest": self.base_feature_schema_digest,
            "base_preprocessing_digest": self.base_preprocessing_digest,
            "dataset_reference": _plain(self.dataset_reference),
            "signal_run_reference": _plain(self.signal_run_reference),
            "calibration_protocol": _plain(self.calibration_protocol), "method_id": self.method_id,
            "method_version": self.method_version, "mapping": _plain(self.mapping),
            "fitting_configuration": _plain(self.fitting_configuration),
            "dependency_versions": _plain(self.dependency_versions), "lifecycle": _plain(self.lifecycle)}

    def to_dict(self):
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, Mapping) or set(payload) != {
            "artifact_version", "scope", "base_artifact_digest", "base_artifact_version", "base_family",
            "base_feature_schema_digest", "base_preprocessing_digest", "dataset_reference",
            "signal_run_reference", "calibration_protocol", "method_id", "method_version", "mapping",
            "fitting_configuration", "dependency_versions", "lifecycle", "digest"}:
            raise ValueError("artifact_payload")
        values = dict(payload)
        values["scope"] = TrainingScope(**dict(values["scope"]))
        return cls(**values)

    def __repr__(self):
        return (f"CalibratorArtifact(scope={self.scope.source_key!r}, method_id={self.method_id!r}, "
                f"status={self.lifecycle['status']!r}, digest={self.digest!r})")


def _exact_keys(mapping, expected):
    if set(mapping) != set(expected):
        raise ValueError("artifact_fields")


def _finite(value):
    return type(value) in (int, float) and type(value) is not bool and isfinite(value)


def _artifact_digest(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
