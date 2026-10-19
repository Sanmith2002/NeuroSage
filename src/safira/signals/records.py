"""Deeply immutable, privacy-conscious Feature 004 contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import ClassVar
import unicodedata
import re

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
class Feature003DatasetReference:
    """Opaque, exact Feature 003 development dataset scope."""
    dataset_id: str
    protocol_id: str
    protocol_version: str
    manifest_reference: str
    builder_version: str
    manifest_digest: str = ""

    def __post_init__(self):
        for name in ("dataset_id", "protocol_id", "protocol_version", "manifest_reference", "builder_version"):
            _identifier(getattr(self, name), name)
        if self.manifest_digest:
            if type(self.manifest_digest) is not str or re.fullmatch(r"[0-9a-f]{64}", self.manifest_digest) is None:
                raise ValueError("manifest_digest")


@dataclass(frozen=True)
class SignalDatasetRowCheck:
    """One independently checked prediction row within a verified dataset."""
    record_fingerprint: str
    source_key: tuple[str, str, str]
    association: tuple[str, str, str]
    partition: str

    def __post_init__(self):
        _identifier(self.record_fingerprint, "dataset_row")
        for name in ("source_key", "association"):
            value = getattr(self, name)
            if not isinstance(value, (tuple, list)) or len(value) != 3:
                raise ValueError("dataset_row")
            object.__setattr__(self, name, tuple(_identifier(v, "dataset_row") for v in value))
        if self.partition not in ("train", "validation", "calibration"):
            raise ValueError("dataset_row")


@dataclass(frozen=True)
class SignalDatasetCheck:
    """Executed host verification of the complete Feature 003 development input."""
    dataset_fingerprint: str
    dataset_id: str
    protocol_id: str
    protocol_version: str
    manifest_reference: str
    builder_version: str
    readiness: str
    authority: str
    method: str
    evidence_ref: str
    rows: tuple[SignalDatasetRowCheck, ...]
    manifest_digest: str = ""
    authorized_partitions: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("dataset_fingerprint", "dataset_id", "protocol_id", "protocol_version",
                     "manifest_reference", "builder_version", "readiness", "authority", "method", "evidence_ref"):
            _identifier(getattr(self, name), "dataset_verification")
        if self.manifest_digest:
            if re.fullmatch(r"[0-9a-f]{64}", self.manifest_digest) is None:
                raise ValueError("dataset_manifest_digest")
        if not isinstance(self.rows, (tuple, list)) or any(type(row) is not SignalDatasetRowCheck for row in self.rows):
            raise ValueError("dataset_verification")
        object.__setattr__(self, "rows", tuple(self.rows))
        parts = tuple(self.authorized_partitions)
        if any(part not in ("train", "validation", "calibration") for part in parts):
            raise ValueError("dataset_partitions")
        object.__setattr__(self, "authorized_partitions", parts)

    @property
    def verified_row_count(self):
        return len(self.rows)


@dataclass(frozen=True, order=True)
class SignalRowKey:
    """Run-scoped opaque alignment key; it contains no patient identity."""
    value: str

    def __post_init__(self):
        _identifier(self.value, "row_key")


@dataclass(frozen=True)
class SignalFeatureRecord:
    row_key: SignalRowKey
    source_key: SignalSourceKey
    predictors: tuple[SignalResult, ...]

    def __post_init__(self):
        if type(self.row_key) is not SignalRowKey or type(self.source_key) is not SignalSourceKey:
            raise ValueError("feature_record")
        if not isinstance(self.predictors, (tuple, list)) or any(type(v) is not SignalResult for v in self.predictors):
            raise ValueError("feature_record")
        if any(v.source_key != self.source_key for v in self.predictors):
            raise ValueError("feature_source_mismatch")
        object.__setattr__(self, "predictors", tuple(self.predictors))

    def to_dict(self):
        return {"row_key": self.row_key.value, "source_key": self.source_key.to_dict(),
                "predictors": [item.to_dict() for item in self.predictors]}


@dataclass(frozen=True)
class SignalRunManifest:
    dataset_reference: Feature003DatasetReference
    source_keys: tuple[SignalSourceKey, ...]
    method_configs: tuple[SignalMethodConfig, ...]
    fitted_state_references: tuple[FittedStateReference, ...] = ()
    exclusions: tuple[str, ...] = ()
    fold_seed: str = ""
    fold_count: int = 0
    fold_algorithm: str = "sha256_seed_nul_group_mod_v1"
    run_version: str = "signals-v1"

    def __post_init__(self):
        if type(self.dataset_reference) is not Feature003DatasetReference:
            raise ValueError("manifest_scope")
        for name in ("source_keys", "method_configs", "fitted_state_references", "exclusions"):
            values = tuple(getattr(self, name))
            object.__setattr__(self, name, values)
        if any(type(v) is not SignalSourceKey for v in self.source_keys):
            raise ValueError("manifest_sources")
        if any(type(v) is not SignalMethodConfig for v in self.method_configs):
            raise ValueError("manifest_methods")
        if any(type(v) is not FittedStateReference for v in self.fitted_state_references):
            raise ValueError("manifest_states")
        if any(type(v) is not str or v not in {"row_excluded", "signal_unavailable", "reference_insufficient"}
               for v in self.exclusions):
            raise ValueError("manifest_exclusion")
        if self.fold_count and (type(self.fold_count) is not int or self.fold_count < 2):
            raise ValueError("manifest_fold_count")
        if self.fold_seed:
            _identifier(self.fold_seed, "manifest_seed")
        if self.fold_algorithm not in ("", "sha256_seed_nul_group_mod_v1"):
            raise ValueError("manifest_fold_algorithm")
        _identifier(self.run_version, "run_version")

    def to_dict(self):
        return {"dataset_reference": {name: getattr(self.dataset_reference, name) for name in
                ("dataset_id", "protocol_id", "protocol_version", "manifest_reference", "builder_version",
                 "manifest_digest")}, "source_keys": [x.to_dict() for x in self.source_keys],
                "method_configs": [x.to_dict() for x in self.method_configs],
                "fitted_state_references": [x.to_dict() for x in self.fitted_state_references],
                "exclusions": list(self.exclusions), "fold_seed": self.fold_seed,
                "fold_count": self.fold_count, "fold_algorithm": self.fold_algorithm,
                "run_version": self.run_version}


@dataclass(frozen=True)
class SignalFeatureSet:
    dataset_reference: Feature003DatasetReference
    training: tuple[SignalFeatureRecord, ...]
    validation: tuple[SignalFeatureRecord, ...]
    calibration: tuple[SignalFeatureRecord, ...]
    manifest: SignalRunManifest
    cohort_support: Mapping[str, object]

    def __post_init__(self):
        for name in ("training", "validation", "calibration"):
            values = tuple(getattr(self, name))
            if any(type(value) is not SignalFeatureRecord for value in values):
                raise ValueError("feature_set")
            object.__setattr__(self, name, values)
        if type(self.dataset_reference) is not Feature003DatasetReference or type(self.manifest) is not SignalRunManifest:
            raise ValueError("feature_set")
        if self.manifest.dataset_reference != self.dataset_reference:
            raise ValueError("feature_set_scope")
        keys = [row.row_key for role in (self.training, self.validation, self.calibration) for row in role]
        if len(keys) != len(set(keys)):
            raise ValueError("feature_set_row_key_duplicate")
        object.__setattr__(self, "cohort_support", _freeze(self.cohort_support, "cohort_support"))

    def to_dict(self):
        return {"dataset_reference": {"dataset_id": self.dataset_reference.dataset_id,
                "protocol_id": self.dataset_reference.protocol_id,
                "protocol_version": self.dataset_reference.protocol_version,
                "manifest_reference": self.dataset_reference.manifest_reference,
                "builder_version": self.dataset_reference.builder_version,
                "manifest_digest": self.dataset_reference.manifest_digest},
                "training": [v.to_dict() for v in self.training],
                "validation": [v.to_dict() for v in self.validation],
                "calibration": [v.to_dict() for v in self.calibration],
                "manifest": self.manifest.to_dict(), "cohort_support": _plain(self.cohort_support)}


@dataclass(frozen=True)
class ProtectedApplyRequest:
    """Apply-only request; holds references and scope, never protected payloads."""
    fitted_state_references: tuple[FittedStateReference, ...]
    dataset_reference: Feature003DatasetReference
    method_scope: tuple[str, ...]
    fingerprint: str = ""

    def __post_init__(self):
        refs, methods = tuple(self.fitted_state_references), tuple(self.method_scope)
        if not refs or any(type(v) is not FittedStateReference for v in refs):
            raise ValueError("protected_scope")
        if type(self.dataset_reference) is not Feature003DatasetReference:
            raise ValueError("protected_scope")
        if not methods or any(type(v) is not str or not v for v in methods):
            raise ValueError("protected_scope")
        if len(methods) != len(set(methods)) or len({ref.state_id for ref in refs}) != len(refs):
            raise ValueError("protected_scope")
        if set(methods) != {ref.method_id for ref in refs}:
            raise ValueError("protected_scope")
        for ref in refs:
            if (ref.dataset_id != self.dataset_reference.dataset_id
                    or ref.protocol_id != self.dataset_reference.protocol_id
                    or ref.protocol_version != self.dataset_reference.protocol_version
                    or ref.manifest_reference != self.dataset_reference.manifest_reference):
                raise ValueError("protected_scope")
            if set(ref.metadata) - {"digest", "evidence_schema", "reference_cohort"}:
                raise ValueError("protected_state_reference_invalid")
        object.__setattr__(self, "fitted_state_references", refs)
        object.__setattr__(self, "method_scope", methods)
        calculated = self.calculate_fingerprint()
        if self.fingerprint and self.fingerprint != calculated:
            raise ValueError("protected_request_fingerprint")
        object.__setattr__(self, "fingerprint", calculated)

    def _body(self):
        return {"fitted_state_references": [r.to_dict() for r in self.fitted_state_references],
                "dataset_reference": {name: getattr(self.dataset_reference, name) for name in
                    ("dataset_id", "protocol_id", "protocol_version", "manifest_reference", "builder_version",
                     "manifest_digest")}, "method_scope": list(self.method_scope)}

    def calculate_fingerprint(self):
        import hashlib, json
        return hashlib.sha256(json.dumps(self._body(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def to_dict(self):
        return {**self._body(), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class ProtectedApplyReceipt:
    status: str
    request_fingerprint: str
    dataset_reference: Feature003DatasetReference
    state_ids: tuple[str, ...]
    method_scope: tuple[str, ...]
    authority: str
    evidence_ref: str

    def __post_init__(self):
        if self.status not in ("accepted", "rejected", "unavailable"):
            raise ValueError("protected_receipt")
        for name in ("request_fingerprint", "authority", "evidence_ref"):
            _identifier(getattr(self, name), "protected_receipt")
        if type(self.dataset_reference) is not Feature003DatasetReference:
            raise ValueError("protected_receipt")
        object.__setattr__(self, "state_ids", tuple(_identifier(v, "protected_receipt") for v in self.state_ids))
        object.__setattr__(self, "method_scope", tuple(_identifier(v, "protected_receipt") for v in self.method_scope))

    def to_dict(self):
        return {"status": self.status, "request_fingerprint": self.request_fingerprint,
                "dataset_reference": {"dataset_id": self.dataset_reference.dataset_id,
                    "protocol_id": self.dataset_reference.protocol_id,
                    "protocol_version": self.dataset_reference.protocol_version,
                    "manifest_reference": self.dataset_reference.manifest_reference,
                    "builder_version": self.dataset_reference.builder_version,
                    "manifest_digest": self.dataset_reference.manifest_digest},
                "state_ids": list(self.state_ids), "method_scope": list(self.method_scope),
                "authority": self.authority, "evidence_ref": self.evidence_ref}


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
    primary_output: Mapping[str, object] = field(default_factory=dict)

    _SAFE_REASONS: ClassVar[frozenset[str]] = frozenset({
        "evidence_missing", "evidence_unsupported", "evidence_unavailable", "evidence_invalid",
        "primary_output_not_probability", "primary_probability_invalid",
        "fewer_than_two_modalities", "comparison_semantics_incomplete",
        "comparison_semantics_invalid", "modality_semantics_mismatch",
        "modality_semantics_incomparable", "modality_probability_invalid",
        "repeat_provenance_incomplete", "repeat_probability_invalid",
    "repeat_identity_invalid", "fewer_than_two_repeats", "reference_not_ready",
    "reference_support_insufficient", "representation_missing", "representation_invalid",
    "reference_state_invalid", "reference_schema_mismatch", "domain_reference_insufficient",
    "domain_reference_invalid", "domain_evidence_missing", "domain_category_invalid",
    "reference_scope_mismatch", "reference_method_mismatch", "query_provenance_not_ready",
    "reference_insufficient_evidence", "reference_unavailable", "reference_missing", "reference_invalid",
    "explanation_metadata_invalid",
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
            object.__setattr__(self, "primary_output", _freeze(self.primary_output, "primary_output"))
        except Exception:
            raise ValueError("signal_contract") from None

    def to_dict(self):
        return {"source_key": self.source_key.to_dict(), "dimension": self.dimension.value,
                "method_id": self.method_id, "method_version": self.method_version,
                "method_parameters": _plain(self.method_parameters), "state": self.state.value,
                "value": _plain(self.value), "meaning": self.meaning,
                "evidence_sources": list(self.evidence_sources), "provenance": _plain(self.provenance),
                "reason_code": self.reason_code, "primary_output": _plain(self.primary_output)}
