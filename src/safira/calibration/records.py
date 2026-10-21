"""Immutable Feature 006 protocol and status records.

These records describe admission/readiness only in Batch A; they do not expose
calibrated predictions or fitting behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
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
            if self.artifact is None:
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
