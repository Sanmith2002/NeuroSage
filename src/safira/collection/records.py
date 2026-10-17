"""Source-qualified collection values detached from caller-owned containers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any
import unicodedata
from copy import deepcopy

from safira.collection.exceptions import InvalidCollectionRequest, InvalidPrimaryOutput


EVIDENCE_STATES = frozenset(
    {"available", "unsupported", "missing", "unavailable", "invalid"}
)
_SAFE_REASONS = frozenset(
    {
        "unsupported", "missing", "unavailable", "invalid",
        "non_detachable", "extraction_failed", "missing_interpretation",
        "validation_failed", "source_mismatch", "shape_mismatch",
    }
)


def _text(value: object, field_name: str, *, exact: bool = True) -> str:
    if (
        type(value) is not str
        or not value.strip()
        or (exact and value != value.strip())
        or any(unicodedata.category(char) == "Cc" for char in value)
    ):
        raise InvalidCollectionRequest(field_name)
    return value


def _source_key(value: object, field_name: str) -> tuple[str, str, str]:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise InvalidCollectionRequest(field_name)
    return tuple(_text(part, field_name) for part in value)  # type: ignore[return-value]


def _freeze(value: object, field_name: str, ancestors: frozenset[int] = frozenset()) -> object:
    """Copy supported JSON-like values into recursively immutable containers."""

    try:
        return _freeze_value(value, field_name, ancestors)
    except InvalidCollectionRequest:
        raise
    except Exception:
        # Container hooks can raise arbitrary exceptions with sensitive text.
        raise InvalidCollectionRequest(field_name) from None


def _freeze_value(value: object, field_name: str, ancestors: frozenset[int]) -> object:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise InvalidCollectionRequest(field_name)
        return value
    if isinstance(value, (Mapping, tuple, list)):
        if id(value) in ancestors:
            raise InvalidCollectionRequest(field_name)
        ancestors = ancestors | {id(value)}
        if isinstance(value, Mapping):
            copied: dict[str, object] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise InvalidCollectionRequest(field_name)
                copied[key] = _freeze(item, field_name, ancestors)
            return MappingProxyType(copied)
        return tuple(_freeze(item, field_name, ancestors) for item in value)
    raise InvalidCollectionRequest(field_name)


def _thaw(value: object) -> Any:
    """Return a detached mutable representation for outward serialization."""

    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class CollectionAssociation:
    patient_ref: str
    assessment_ref: str
    occurrence_ref: str

    def __post_init__(self) -> None:
        for name in ("patient_ref", "assessment_ref", "occurrence_ref"):
            _text(getattr(self, name), f"association.{name}")

    def to_dict(self) -> dict[str, str]:
        return {
            "patient_ref": self.patient_ref,
            "assessment_ref": self.assessment_ref,
            "occurrence_ref": self.occurrence_ref,
        }


@dataclass(frozen=True)
class ComponentIdentity:
    component_id: str
    component_version: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.component_id, "component.identity")
        _text(self.component_version, "component.identity")
        if not isinstance(self.metadata, Mapping):
            raise InvalidCollectionRequest("component.metadata")
        object.__setattr__(self, "metadata", _freeze(self.metadata, "component.metadata"))

    def to_dict(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True)
class ComponentContribution:
    source_contract_id: str
    source_contract_version: str
    external_selector: str
    model_id: str
    model_version: str
    label_id: str
    registered_output_selector: str | int

    def __post_init__(self) -> None:
        for name in (
            "source_contract_id", "source_contract_version", "external_selector",
            "model_id", "model_version", "label_id",
        ):
            _text(getattr(self, name), "component.contribution")
        selector = self.registered_output_selector
        if type(selector) is not int and (type(selector) is not str or not selector):
            raise InvalidCollectionRequest("component.contribution")

    @property
    def source_key(self) -> tuple[str, str, str]:
        return self.model_id, self.model_version, self.label_id

    def to_dict(self) -> dict[str, object]:
        return {
            "source_contract_id": self.source_contract_id,
            "source_contract_version": self.source_contract_version,
            "external_selector": self.external_selector,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "label_id": self.label_id,
            "registered_output_selector": self.registered_output_selector,
        }


@dataclass(frozen=True)
class PrimaryOutput:
    value: float | int
    value_kind: str
    scale: Mapping[str, object]
    meaning: str
    positive_direction: str
    class_mapping: Mapping[str, object]
    predicted_class: str
    calibration: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if type(self.value) not in (int, float) or (
            type(self.value) is float and not isfinite(self.value)
        ):
            raise InvalidPrimaryOutput("primary.value")
        if self.value_kind not in ("probability", "continuous_score"):
            raise InvalidPrimaryOutput("primary.value_kind")
        if self.value_kind == "probability" and not 0 <= self.value <= 1:
            raise InvalidPrimaryOutput("primary.value")
        _text(self.meaning, "primary.meaning", exact=False)
        if self.positive_direction not in ("increasing", "decreasing"):
            raise InvalidPrimaryOutput("primary.direction")
        _text(self.predicted_class, "primary.predicted_class", exact=False)
        for name in ("scale", "class_mapping"):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise InvalidCollectionRequest(f"primary.{name}")
            object.__setattr__(self, name, _freeze(value, f"primary.{name}"))
        if self.calibration is not None:
            if not isinstance(self.calibration, Mapping):
                raise InvalidCollectionRequest("primary.calibration")
            object.__setattr__(self, "calibration", _freeze(self.calibration, "primary.calibration"))

    def to_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "value_kind": self.value_kind,
            "scale": _thaw(self.scale),
            "meaning": self.meaning,
            "positive_direction": self.positive_direction,
            "class_mapping": _thaw(self.class_mapping),
            "predicted_class": self.predicted_class,
            "calibration": _thaw(self.calibration),
        }


@dataclass(frozen=True)
class SourceProvenance:
    mode: str
    association: CollectionAssociation
    source_key: tuple[str, str, str]
    assurance: str
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in ("live", "precomputed"):
            raise InvalidCollectionRequest("provenance.mode")
        if not isinstance(self.association, CollectionAssociation):
            raise InvalidCollectionRequest("provenance.association")
        object.__setattr__(self, "source_key", _source_key(self.source_key, "provenance.source_key"))
        _text(self.assurance, "provenance.assurance")
        if not isinstance(self.details, Mapping):
            raise InvalidCollectionRequest("provenance.details")
        object.__setattr__(self, "details", _freeze(self.details, "provenance.details"))

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "association": self.association.to_dict(),
            "source_key": list(self.source_key),
            "assurance": self.assurance,
            "details": _thaw(self.details),
        }


@dataclass(frozen=True)
class EvidenceItem:
    association: CollectionAssociation
    source_key: tuple[str, str, str]
    category: str
    state: str
    value: object = None
    reason_code: str | None = None
    interpretation: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.association, CollectionAssociation):
            raise InvalidCollectionRequest("evidence.association")
        object.__setattr__(self, "source_key", _source_key(self.source_key, "evidence.source_key"))
        _text(self.category, "evidence.category")
        if self.state not in EVIDENCE_STATES:
            raise InvalidCollectionRequest("evidence.state")
        if not isinstance(self.interpretation, Mapping):
            raise InvalidCollectionRequest("evidence.interpretation")
        if self.state == "available":
            if self.value is None:
                object.__setattr__(self, "state", "invalid")
                object.__setattr__(self, "reason_code", "invalid")
                object.__setattr__(self, "interpretation", MappingProxyType({}))
                return
            try:
                frozen_value = _freeze(self.value, "evidence.value")
                frozen_interpretation = _freeze(self.interpretation, "evidence.interpretation")
            except InvalidCollectionRequest:
                object.__setattr__(self, "state", "invalid")
                object.__setattr__(self, "value", None)
                object.__setattr__(self, "reason_code", "non_detachable")
                object.__setattr__(self, "interpretation", MappingProxyType({}))
                return
            object.__setattr__(self, "value", frozen_value)
            object.__setattr__(self, "interpretation", frozen_interpretation)
            object.__setattr__(self, "reason_code", None)
            return
        if self.value is not None:
            object.__setattr__(self, "state", "invalid")
        object.__setattr__(self, "value", None)
        reason = self.reason_code
        if reason not in _SAFE_REASONS:
            reason = self.state
        object.__setattr__(self, "reason_code", reason)
        try:
            frozen_interpretation = _freeze(self.interpretation, "evidence.interpretation")
        except InvalidCollectionRequest:
            object.__setattr__(self, "state", "invalid")
            object.__setattr__(self, "reason_code", "non_detachable")
            frozen_interpretation = MappingProxyType({})
        object.__setattr__(self, "interpretation", frozen_interpretation)

    def to_dict(self) -> dict[str, object]:
        return {
            "association": self.association.to_dict(),
            "source_key": list(self.source_key),
            "category": self.category,
            "state": self.state,
            "value": _thaw(self.value),
            "reason_code": self.reason_code,
            "interpretation": _thaw(self.interpretation),
        }


@dataclass(frozen=True)
class PredictionRecord:
    association: CollectionAssociation
    model_id: str
    model_version: str
    label_id: str
    primary: PrimaryOutput
    provenance: SourceProvenance
    evidence: tuple[EvidenceItem, ...] = ()
    component: ComponentIdentity | None = None
    input_verification: str = "unavailable"

    def __post_init__(self) -> None:
        if not isinstance(self.association, CollectionAssociation):
            raise InvalidCollectionRequest("record.association")
        for name in ("model_id", "model_version", "label_id"):
            _text(getattr(self, name), "record.source_key")
        if not isinstance(self.primary, PrimaryOutput):
            raise InvalidCollectionRequest("record.primary")
        if (
            not isinstance(self.provenance, SourceProvenance)
            or self.provenance.association != self.association
            or self.provenance.source_key != self.source_key
        ):
            raise InvalidCollectionRequest("record.source_key")
        if self.component is not None and not isinstance(self.component, ComponentIdentity):
            raise InvalidCollectionRequest("component.identity")
        if self.input_verification not in ("validated", "unavailable"):
            raise InvalidCollectionRequest("record.input_verification")
        if not isinstance(self.evidence, (tuple, list)):
            raise InvalidCollectionRequest("record.evidence")
        for item in self.evidence:
            if (
                not isinstance(item, EvidenceItem)
                or item.association != self.association
                or item.source_key != self.source_key
            ):
                raise InvalidCollectionRequest("record.evidence")
        object.__setattr__(self, "evidence", tuple(self.evidence))

    @property
    def source_key(self) -> tuple[str, str, str]:
        return self.model_id, self.model_version, self.label_id

    def to_dict(self) -> dict[str, object]:
        return {
            "association": self.association.to_dict(),
            "model_id": self.model_id,
            "model_version": self.model_version,
            "label_id": self.label_id,
            "primary": self.primary.to_dict(),
            "provenance": self.provenance.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "component": self.component.to_dict() if self.component else None,
            "input_verification": self.input_verification,
        }


@dataclass(frozen=True)
class CollectionResult:
    association: CollectionAssociation
    records: tuple[PredictionRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.association, CollectionAssociation):
            raise InvalidCollectionRequest("result.association")
        if not isinstance(self.records, (tuple, list)) or not self.records:
            raise InvalidCollectionRequest("result.records")
        seen: set[tuple[str, str, str]] = set()
        for record in self.records:
            if not isinstance(record, PredictionRecord) or record.association != self.association:
                raise InvalidCollectionRequest("result.records")
            if record.source_key in seen:
                raise InvalidCollectionRequest("record.source_key")
            seen.add(record.source_key)
        object.__setattr__(self, "records", tuple(self.records))

    def to_dict(self) -> dict[str, object]:
        return {
            "association": self.association.to_dict(),
            "records": [record.to_dict() for record in self.records],
        }


def to_safety_context(record: PredictionRecord, *, patient_data: object = None):
    """Return a detached legacy SafetyContext projection of one accepted record.

    The record remains authoritative for source identity, provenance and the
    five evidence states. This helper only populates values the legacy context
    can represent and never creates a SafetyAssessment.
    """
    if not isinstance(record, PredictionRecord):
        raise InvalidCollectionRequest("record.primary")
    from safira.context import SafetyContext

    try:
        detached_input = deepcopy(patient_data)
        available = {item.category: item.to_dict()["value"]
                     for item in record.evidence if item.state == "available"}
        primary_metadata = {
            "source_key": list(record.source_key),
            "association": record.association.to_dict(),
            "provenance": record.provenance.to_dict(),
            "evidence_states": {item.category: item.state for item in record.evidence},
            "primary": record.primary.to_dict(),
        }
        metadata = {"safira_collection": primary_metadata}
        if record.primary.value_kind != "probability":
            metadata["safira_collection"]["continuous_score"] = {
                "value": record.primary.value,
                "meaning": record.primary.meaning,
                "scale": record.primary.to_dict()["scale"],
            }
        return SafetyContext(
            patient_id=record.association.patient_ref,
            label=record.label_id,
            patient_data=detached_input,
            prediction=record.primary.predicted_class,
            prediction_probability=(record.primary.value
                                   if record.primary.value_kind == "probability" else None),
            input_metadata=available.get("input_metadata", {}),
            available_modalities=available.get("available_modalities", []),
            feature_representation=available.get("feature_representation"),
            repeated_outputs=available.get("repeated_outputs", []),
            modality_outputs=available.get("modality_outputs", {}),
            domain_metadata=available.get("domain_metadata", {}),
            explanation=available.get("explanation"),
            model_metadata=metadata,
        )
    except Exception:
        raise InvalidCollectionRequest("record.primary") from None
