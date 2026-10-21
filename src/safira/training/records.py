"""Immutable Feature 005 scope, protocol, verification and outcome records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import json
from math import isfinite
import re
from types import MappingProxyType
from typing import Any


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


@dataclass(frozen=True)
class TrainingProtocol:
    protocol_id: str
    version: str
    scopes: tuple[TrainingScope, ...]
    adequacy: Mapping[tuple[str, str, str], TrainingSupportCriteria]
    required_signal_methods: Mapping[tuple[str, str, str], tuple[str, ...]]

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

    def to_dict(self):
        encode = lambda key: json.dumps(list(key), separators=(",", ":"))
        return {
            "protocol_id": self.protocol_id, "version": self.version,
            "scopes": [scope.to_dict() for scope in self.scopes],
            "adequacy": {encode(key): value.to_dict() for key, value in self.adequacy.items()},
            "required_signal_methods": {encode(key): list(value)
                                         for key, value in self.required_signal_methods.items()},
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
    "candidate_fitting_not_implemented_in_batch_a", "training_outcome_unavailable",
})


@dataclass(frozen=True)
class TrainingOutcome:
    scope: TrainingScope
    status: TrainingStatus
    reason_code: str | None = None
    limitations: tuple[str, ...] = ()
    artifact: None = None

    def __post_init__(self):
        if type(self.scope) is not TrainingScope or type(self.status) is not TrainingStatus:
            raise ValueError("outcome")
        if self.reason_code is not None:
            _identifier(self.reason_code, "reason_code")
            if self.reason_code not in _SAFE_REASON_CODES:
                object.__setattr__(self, "reason_code", "training_outcome_unavailable")
        if self.status in (TrainingStatus.SELECTED_BASELINE, TrainingStatus.SELECTED_LOGISTIC):
            raise ValueError("batch_a_success_status_forbidden")
        limitations = tuple(self.limitations)
        if any(type(item) is not str for item in limitations):
            raise ValueError("limitations")
        object.__setattr__(self, "limitations", limitations)
        if self.artifact is not None:
            raise ValueError("batch_a_artifact_forbidden")

    def to_dict(self):
        return {"scope": self.scope.to_dict(), "status": self.status.value,
                "reason_code": self.reason_code, "limitations": list(self.limitations)}


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
