"""Deeply immutable, privacy-conscious Feature 004 contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import ClassVar
import unicodedata

from safira.signals.base import SignalDimension, SignalState


def _freeze(value, field, ancestors=frozenset()):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError(field)
        return value
    if isinstance(value, Mapping):
        if id(value) in ancestors:
            raise ValueError(field)
        ancestors = ancestors | {id(value)}
        copied = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(field)
            copied[key] = _freeze(item, field, ancestors)
        return MappingProxyType(copied)
    if isinstance(value, (tuple, list)):
        if id(value) in ancestors:
            raise ValueError(field)
        ancestors = ancestors | {id(value)}
        return tuple(_freeze(item, field, ancestors) for item in value)
    raise ValueError(field)


def _plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _identifier(value, field):
    if (type(value) is not str or not value.strip() or value != value.strip()
            or any(unicodedata.category(ch) == "Cc" for ch in value)):
        raise ValueError(field)
    return value


@dataclass(frozen=True, order=True)
class SignalSourceKey:
    model_id: str
    model_version: str
    label_id: str

    def __post_init__(self):
        for name in ("model_id", "model_version", "label_id"):
            _identifier(getattr(self, name), "source_key")

    def to_tuple(self):
        return self.model_id, self.model_version, self.label_id

    def to_dict(self):
        return {"model_id": self.model_id, "model_version": self.model_version, "label_id": self.label_id}


@dataclass(frozen=True)
class SignalMethodConfig:
    method_id: str
    method_version: str
    parameters: Mapping[str, object]

    def __post_init__(self):
        _identifier(self.method_id, "method_id")
        _identifier(self.method_version, "method_version")
        try:
            object.__setattr__(self, "parameters", _freeze(self.parameters, "parameters"))
        except Exception:
            raise ValueError("parameters") from None

    def to_dict(self):
        return {"method_id": self.method_id, "method_version": self.method_version,
                "parameters": _plain(self.parameters)}


@dataclass(frozen=True)
class SignalProtocol:
    protocol_id: str
    protocol_version: str
    source_keys: tuple[SignalSourceKey, ...]
    method_configs: Mapping[str, SignalMethodConfig]
    evidence_prerequisites: Mapping[str, tuple[str, ...]]

    def __post_init__(self):
        _identifier(self.protocol_id, "protocol_id")
        _identifier(self.protocol_version, "protocol_version")
        if not isinstance(self.source_keys, (tuple, list)) or not self.source_keys:
            raise ValueError("source_keys")
        keys = tuple(self.source_keys)
        if any(type(key) is not SignalSourceKey for key in keys) or len(set(keys)) != len(keys):
            raise ValueError("source_keys")
        object.__setattr__(self, "source_keys", keys)
        if not isinstance(self.method_configs, Mapping):
            raise ValueError("method_configs")
        configs = dict(self.method_configs)
        if any(type(key) is not str or type(cfg) is not SignalMethodConfig or key != cfg.method_id
               for key, cfg in configs.items()):
            raise ValueError("method_configs")
        object.__setattr__(self, "method_configs", MappingProxyType(configs))
        if not isinstance(self.evidence_prerequisites, Mapping):
            raise ValueError("evidence_prerequisites")
        try:
            prerequisites = {}
            for key, categories in self.evidence_prerequisites.items():
                _identifier(key, "evidence_prerequisites")
                if not isinstance(categories, (tuple, list)):
                    raise ValueError
                values = tuple(_identifier(c, "evidence_prerequisites") for c in categories)
                if len(values) != len(set(values)):
                    raise ValueError
                prerequisites[key] = values
            object.__setattr__(self, "evidence_prerequisites", MappingProxyType(prerequisites))
        except Exception:
            raise ValueError("evidence_prerequisites") from None

    def to_dict(self):
        return {"protocol_id": self.protocol_id, "protocol_version": self.protocol_version,
                "source_keys": [key.to_dict() for key in self.source_keys],
                "method_configs": {key: cfg.to_dict() for key, cfg in self.method_configs.items()},
                "evidence_prerequisites": _plain(self.evidence_prerequisites)}


@dataclass(frozen=True)
class SignalInputCheck:
    record_fingerprint: str
    source_key: tuple[str, str, str]
    association: tuple[str, str, str]
    provenance_mode: str
    state: str
    authority: str
    method: str
    evidence_ref: str
    input_scope: str

    def __post_init__(self):
        _identifier(self.record_fingerprint, "verification")
        for name in ("authority", "method", "evidence_ref", "input_scope", "provenance_mode", "state"):
            _identifier(getattr(self, name), "verification")
        if not isinstance(self.source_key, (tuple, list)) or len(self.source_key) != 3:
            raise ValueError("verification")
        if not isinstance(self.association, (tuple, list)) or len(self.association) != 3:
            raise ValueError("verification")
        object.__setattr__(self, "source_key", tuple(_identifier(v, "verification") for v in self.source_key))
        object.__setattr__(self, "association", tuple(_identifier(v, "verification") for v in self.association))


@dataclass(frozen=True)
class FittedStateReference:
    state_id: str
    source_key: SignalSourceKey
    method_id: str
    method_version: str
    dataset_id: str
    protocol_id: str
    protocol_version: str
    manifest_reference: str
    preprocessing_identity: str
    metadata: Mapping[str, object]

    def __post_init__(self):
        for name in ("state_id", "method_id", "method_version", "dataset_id", "protocol_id",
                     "protocol_version", "manifest_reference", "preprocessing_identity"):
            _identifier(getattr(self, name), name)
        if type(self.source_key) is not SignalSourceKey:
            raise ValueError("source_key")
        try:
            object.__setattr__(self, "metadata", _freeze(self.metadata, "metadata"))
        except Exception:
            raise ValueError("metadata") from None

    def to_dict(self):
        return {"state_id": self.state_id, "source_key": self.source_key.to_dict(),
                "method_id": self.method_id, "method_version": self.method_version,
                "dataset_id": self.dataset_id, "protocol_id": self.protocol_id,
                "protocol_version": self.protocol_version, "manifest_reference": self.manifest_reference,
                "preprocessing_identity": self.preprocessing_identity, "metadata": _plain(self.metadata)}


@dataclass(frozen=True)
class SignalResult:
    source_key: SignalSourceKey
    dimension: SignalDimension
    method_id: str
    method_version: str
    method_parameters: Mapping[str, object]
    state: SignalState
    value: object
    meaning: str
    evidence_sources: tuple[str, ...]
    provenance: Mapping[str, object]
    reason_code: str | None = None

    _SAFE_REASONS: ClassVar[frozenset[str]] = frozenset({
        "evidence_missing", "evidence_unsupported", "evidence_unavailable", "evidence_invalid",
        "primary_output_not_probability", "primary_probability_invalid",
        "fewer_than_two_modalities", "comparison_semantics_incomplete",
        "comparison_semantics_invalid", "modality_semantics_mismatch",
        "modality_semantics_incomparable", "modality_probability_invalid",
        "repeat_provenance_incomplete", "repeat_probability_invalid",
        "repeat_identity_invalid", "fewer_than_two_repeats",
    })

    def __post_init__(self):
        if type(self.source_key) is not SignalSourceKey:
            raise ValueError("source_key")
        if type(self.dimension) is not SignalDimension or type(self.state) is not SignalState:
            raise ValueError("signal_contract")
        _identifier(self.method_id, "method_id")
        _identifier(self.method_version, "method_version")
        _identifier(self.meaning, "meaning")
        if self.state is SignalState.AVAILABLE and self.value is None:
            raise ValueError("value")
        if self.state is not SignalState.AVAILABLE and self.value is not None:
            raise ValueError("value")
        if self.state is not SignalState.AVAILABLE and self.reason_code is None:
            raise ValueError("reason_code")
        if self.reason_code is not None:
            _identifier(self.reason_code, "reason_code")
            if self.reason_code not in self._SAFE_REASONS:
                raise ValueError("reason_code")
        if not isinstance(self.evidence_sources, (tuple, list)):
            raise ValueError("evidence_sources")
        sources = tuple(_identifier(v, "evidence_sources") for v in self.evidence_sources)
        object.__setattr__(self, "evidence_sources", sources)
        try:
            object.__setattr__(self, "method_parameters", _freeze(self.method_parameters, "parameters"))
            object.__setattr__(self, "value", _freeze(self.value, "value"))
            object.__setattr__(self, "provenance", _freeze(self.provenance, "provenance"))
        except Exception:
            raise ValueError("signal_contract") from None

    def to_dict(self):
        return {"source_key": self.source_key.to_dict(), "dimension": self.dimension.value,
                "method_id": self.method_id, "method_version": self.method_version,
                "method_parameters": _plain(self.method_parameters), "state": self.state.value,
                "value": _plain(self.value), "meaning": self.meaning,
                "evidence_sources": list(self.evidence_sources), "provenance": _plain(self.provenance),
                "reason_code": self.reason_code}
