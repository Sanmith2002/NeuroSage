"""Versioned external prediction ingestion through injected trust boundaries.

This module accepts only source contracts and provenance verifiers explicitly
provided to a collector instance. It never treats external identity fields as
proof that a registered classifier produced a value.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
import json
from math import isfinite
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from safira.adapters import AdapterCapabilities
from safira.adapters.base import ModelAdapter
from safira.collection.exceptions import (
    ContributorMismatch,
    EvidenceUnavailable,
    InvalidCollectionRequest,
    InvalidPrimaryOutput,
    ProvenanceCheckFailed,
    UnknownSourceContract,
)
from safira.collection.records import (
    CollectionAssociation,
    CollectionResult,
    ComponentContribution,
    ComponentIdentity,
    EvidenceItem,
    PredictionRecord,
    SourceProvenance,
)
from safira.collection.validation import (
    validate_component_contributor_mapping, validate_primary_output,
)


_EVIDENCE_CATEGORIES = (
    "feature_representation", "repeated_outputs", "modality_outputs",
    "domain_metadata", "explanation", "input_metadata", "available_modalities",
)


@dataclass(frozen=True)
class OutputCandidate:
    """One source-contract-normalized output; values remain source-defined."""

    external_selector: str
    value: object
    value_kind: str
    meaning: str
    positive_direction: str
    supplied_class: str | None = None
    calibration: Mapping[str, object] | None = None
    evidence: Mapping[str, object] = field(default_factory=dict)
    event_id: str | None = None


@dataclass(frozen=True)
class NormalizedEnvelope:
    """A contract parser's candidates and optional source-declared association."""

    outputs: tuple[OutputCandidate, ...]
    association: tuple[str, str, str] | None = None


@dataclass(frozen=True)
class ProvenanceCheck:
    """Structured result of one executed source-specific provenance check."""

    integration_id: str
    check_method: str
    independent_evidence_ref: str
    event_id: str
    content_binding_method: str
    content_bound: bool
    covered_selector: str
    contributor: tuple[str, str, str]
    association: tuple[str, str, str]
    association_bound: bool
    fresh: bool
    not_revoked: bool
    unused: bool


@dataclass(frozen=True)
class SourceDeclarations:
    """Owner-supplied external-selector mapping and optional side declarations."""

    contributions: tuple[ComponentContribution, ...]
    expected_contributors: tuple[tuple[str, str, str], ...] = ()
    association: CollectionAssociation | None = None
    meanings: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.contributions, (tuple, list)):
            raise InvalidCollectionRequest("component.contribution")
        if any(not isinstance(item, ComponentContribution) for item in self.contributions):
            raise InvalidCollectionRequest("component.contribution")
        object.__setattr__(self, "contributions", tuple(self.contributions))
        try:
            expected = tuple(tuple(item) for item in self.expected_contributors)
            if any(len(item) != 3 or any(type(part) is not str or not part.strip() for part in item)
                   for item in expected) or len(set(expected)) != len(expected):
                raise ValueError
            object.__setattr__(self, "expected_contributors", expected)
        except Exception:
            raise InvalidCollectionRequest("component.contribution") from None
        if self.association is not None and not isinstance(self.association, CollectionAssociation):
            raise InvalidCollectionRequest("association.occurrence_ref")
        try:
            object.__setattr__(self, "meanings", MappingProxyType(_detach_mapping(self.meanings)))
        except Exception:
            raise InvalidCollectionRequest("source_contract") from None


@runtime_checkable
class SourceContract(Protocol):
    contract_id: str
    version: str

    def parse(self, raw_json: str | bytes) -> NormalizedEnvelope: ...

    def validate_declarations(
        self, envelope: NormalizedEnvelope, declarations: SourceDeclarations
    ) -> NormalizedEnvelope: ...


@runtime_checkable
class TrustedProvenanceVerifier(Protocol):
    integration_id: str

    def check_output_link(
        self,
        raw_json: str | bytes,
        candidate: OutputCandidate,
        contributor: object,
        label: object,
        association: CollectionAssociation,
    ) -> object: ...


@dataclass(frozen=True)
class TrustedSourceIntegration:
    """Explicitly injected contract/verifier pair for one source boundary."""

    contract: SourceContract
    verifier: TrustedProvenanceVerifier

    def __post_init__(self) -> None:
        for value in (getattr(self.contract, "contract_id", None), getattr(self.contract, "version", None),
                      getattr(self.verifier, "integration_id", None)):
            if type(value) is not str or not value or value != value.strip():
                raise InvalidCollectionRequest("source_contract")
        if not callable(getattr(self.contract, "parse", None)) or not callable(
            getattr(self.contract, "validate_declarations", None)
        ) or not callable(
            getattr(self.verifier, "check_output_link", None)
        ):
            raise InvalidCollectionRequest("source_contract")


def _detach(value: object, ancestors: frozenset[int] = frozenset()) -> object:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("nonfinite")
        return value
    if isinstance(value, Mapping):
        if id(value) in ancestors:
            raise ValueError("cycle")
        ancestors = ancestors | {id(value)}
        result = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("key")
            result[key] = _detach(item, ancestors)
        return MappingProxyType(result)
    if isinstance(value, (tuple, list)):
        if id(value) in ancestors:
            raise ValueError("cycle")
        ancestors = ancestors | {id(value)}
        return tuple(_detach(item, ancestors) for item in value)
    raise ValueError("unsupported")


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _detach_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("mapping")
    copied = _detach(value)
    return copied  # type: ignore[return-value]


def _reject_constant(_: str) -> None:
    raise ValueError("nonfinite JSON constant")


def _unique_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _strict_json(raw_json: str | bytes) -> object:
    if type(raw_json) not in (str, bytes):
        raise UnknownSourceContract("source_contract")
    try:
        return json.loads(raw_json, object_pairs_hook=_unique_members, parse_constant=_reject_constant)
    except Exception:
        raise UnknownSourceContract("source_contract") from None


def _association_key(association: CollectionAssociation) -> tuple[str, str, str]:
    return association.patient_ref, association.assessment_ref, association.occurrence_ref


def _candidate(value: object) -> OutputCandidate:
    if not isinstance(value, OutputCandidate):
        raise UnknownSourceContract("source_contract")
    try:
        if type(value.external_selector) is not str or not value.external_selector.strip():
            raise ValueError
        if type(value.value_kind) is not str or type(value.meaning) is not str or type(value.positive_direction) is not str:
            raise ValueError
        if value.supplied_class is not None and type(value.supplied_class) is not str:
            raise ValueError
        detached_value = _detach(value.value)
        calibration = None if value.calibration is None else MappingProxyType(_detach_mapping(value.calibration))
        evidence = MappingProxyType(_detach_mapping(value.evidence))
        if value.event_id is not None and (type(value.event_id) is not str or not value.event_id.strip()):
            raise ValueError
        return OutputCandidate(value.external_selector, detached_value, value.value_kind, value.meaning,
                               value.positive_direction, value.supplied_class, calibration, evidence, value.event_id)
    except Exception:
        raise UnknownSourceContract("source_contract") from None


def _check_field(check: object, name: str) -> object:
    if isinstance(check, Mapping):
        return check.get(name)
    return getattr(check, name, None)


class PrecomputedCollector:
    """Admit precomputed candidates only after exact registry and source checks."""

    def __init__(self, registry: object, integrations: Iterable[TrustedSourceIntegration]) -> None:
        if not callable(getattr(registry, "get_metadata", None)):
            raise InvalidCollectionRequest("request")
        try:
            pairs = tuple(integrations)
        except Exception:
            raise InvalidCollectionRequest("source_contract") from None
        mapping: dict[tuple[str, str], TrustedSourceIntegration] = {}
        for pair in pairs:
            if not isinstance(pair, TrustedSourceIntegration):
                raise InvalidCollectionRequest("source_contract")
            key = (pair.contract.contract_id, pair.contract.version)
            if key in mapping:
                raise InvalidCollectionRequest("source_contract")
            mapping[key] = pair
        self._registry = registry
        self._integrations = MappingProxyType(mapping)

    @property
    def contract_keys(self) -> frozenset[tuple[str, str]]:
        return frozenset(self._integrations)

    def ingest(
        self,
        association: CollectionAssociation,
        contract_key: tuple[str, str],
        raw_json: str | bytes,
        declarations: SourceDeclarations | Iterable[ComponentContribution],
        *,
        component: ComponentIdentity | None = None,
    ) -> CollectionResult:
        if not isinstance(association, CollectionAssociation):
            raise InvalidCollectionRequest("association.occurrence_ref")
        if component is not None and not isinstance(component, ComponentIdentity):
            raise InvalidCollectionRequest("component.identity")
        if not isinstance(contract_key, (tuple, list)) or len(contract_key) != 2 or any(type(v) is not str for v in contract_key):
            raise UnknownSourceContract("source_contract")
        integration = self._integrations.get(tuple(contract_key))
        if integration is None:
            raise UnknownSourceContract("source_contract")
        if isinstance(declarations, SourceDeclarations):
            supplied = declarations
        else:
            try:
                supplied = SourceDeclarations(tuple(declarations))
            except Exception:
                raise InvalidCollectionRequest("component.contribution") from None
        if supplied.association is not None and supplied.association != association:
            raise InvalidCollectionRequest("association.occurrence_ref")

        _strict_json(raw_json)
        try:
            envelope = integration.contract.parse(raw_json)
            envelope = integration.contract.validate_declarations(envelope, supplied)
            if not isinstance(envelope, NormalizedEnvelope) or not isinstance(envelope.outputs, (tuple, list)) or not envelope.outputs:
                raise ValueError
            candidates = tuple(_candidate(candidate) for candidate in envelope.outputs)
            if envelope.association is not None and tuple(envelope.association) != _association_key(association):
                raise ValueError
        except Exception:
            raise UnknownSourceContract("source_contract") from None

        candidate_selectors = [candidate.external_selector for candidate in candidates]
        if set(supplied.meanings) - set(candidate_selectors):
            raise ContributorMismatch("component.contribution")
        by_selector = validate_component_contributor_mapping(
            self._registry, supplied.contributions, candidate_selectors,
            contract_key=tuple(contract_key), expected_contributors=supplied.expected_contributors,
        )
        if component is not None and not supplied.expected_contributors:
            raise ContributorMismatch("component.contribution")

        # Validate the full candidate set and every check before publishing any record.
        pending: list[PredictionRecord] = []
        event_ids: set[str] = set()
        for candidate in candidates:
            contribution, definition, label = by_selector[candidate.external_selector]
            declared_meaning = supplied.meanings.get(candidate.external_selector)
            if declared_meaning is not None:
                if not isinstance(declared_meaning, Mapping) or set(declared_meaning) - {
                    "value_kind", "meaning", "positive_direction"
                }:
                    raise ContributorMismatch("component.contribution")
                for name in ("value_kind", "meaning", "positive_direction"):
                    declared_value = declared_meaning.get(name)
                    candidate_value = getattr(candidate, name)
                    if declared_value is not None and type(declared_value) is not str:
                        raise ContributorMismatch("component.contribution")
                    if candidate_value and declared_value is not None and candidate_value != declared_value:
                        raise ContributorMismatch("component.contribution")
            else:
                declared_meaning = {}
            candidate = replace(
                candidate,
                value_kind=candidate.value_kind or declared_meaning.get("value_kind", ""),
                meaning=candidate.meaning or declared_meaning.get("meaning", ""),
                positive_direction=candidate.positive_direction or declared_meaning.get("positive_direction", ""),
            )
            expected_meaning = label.value_scale.get("meaning")
            expected_direction = label.value_scale.get("positive_direction")
            if (candidate.value_kind != label.value_kind or candidate.meaning != expected_meaning
                    or candidate.positive_direction != expected_direction):
                raise ContributorMismatch("component.contribution")
            primary = validate_primary_output(candidate.value, label, supplied_class=candidate.supplied_class,
                                              calibration=candidate.calibration)
            try:
                check = integration.verifier.check_output_link(raw_json, candidate, definition, label, association)
            except Exception:
                raise ProvenanceCheckFailed("provenance.details") from None
            try:
                check_passes = self._check_passes(check, integration.verifier, candidate, contribution, association)
            except Exception:
                check_passes = False
            if not check_passes:
                raise ProvenanceCheckFailed("provenance.details")
            event_id = _check_field(check, "event_id")
            if event_id in event_ids:
                raise ProvenanceCheckFailed("provenance.details")
            event_ids.add(event_id)
            evidence_items = self._evidence_items(candidate, association, contribution.source_key)
            details = {
                "source_contract_id": contract_key[0], "source_contract_version": contract_key[1],
                "integration_id": _check_field(check, "integration_id"),
                "check_method": _check_field(check, "check_method"),
                "independent_evidence_ref": _check_field(check, "independent_evidence_ref"),
                "event_id": event_id,
                "content_binding_method": _check_field(check, "content_binding_method"),
                "content_bound": True,
                "external_selector": candidate.external_selector,
                "registered_output_selector": label.output_selector,
                "association_bound": True, "fresh": True, "not_revoked": True, "unused": True,
                "assurance_limits": "trusted source check; not live classifier identity verification",
            }
            provenance = SourceProvenance("precomputed", association, contribution.source_key,
                                          "trusted_source_checked", details)
            pending.append(PredictionRecord(association, contribution.model_id, contribution.model_version,
                                            contribution.label_id, primary, provenance, evidence_items,
                                            component=component, input_verification="unavailable"))
        return CollectionResult(association, tuple(pending))

    @staticmethod
    def _check_passes(check: object, verifier: object, candidate: OutputCandidate,
                      contribution: ComponentContribution, association: CollectionAssociation) -> bool:
        # A callback is trusted only because its immutable pair was injected at construction.
        # The returned report must still contain every executed scope result.
        names = ("integration_id", "check_method", "independent_evidence_ref", "event_id",
                 "content_binding_method", "content_bound", "covered_selector", "contributor",
                 "association", "association_bound", "fresh", "not_revoked", "unused")
        values = {name: _check_field(check, name) for name in names}
        required_text = ("integration_id", "check_method", "independent_evidence_ref", "event_id",
                         "content_binding_method", "covered_selector")
        if any(type(values[name]) is not str or not values[name] for name in required_text):
            return False
        if type(check) is not ProvenanceCheck:
            return False
        if any(type(values[name]) is not bool for name in ("content_bound", "association_bound", "fresh", "not_revoked", "unused")):
            return False
        if type(values["contributor"]) not in (tuple, list) or type(values["association"]) not in (tuple, list):
            return False
        if values["integration_id"] != getattr(verifier, "integration_id", None):
            return False
        if values["covered_selector"] != candidate.external_selector:
            return False
        if tuple(values["contributor"]) != contribution.source_key:
            return False
        if tuple(values["association"]) != _association_key(association):
            return False
        return (values["content_bound"] is True and values["association_bound"] is True
                and values["fresh"] is True and values["not_revoked"] is True and values["unused"] is True
                and type(values["event_id"]) is str and type(values["content_binding_method"]) is str
                and type(values["check_method"]) is str and type(values["independent_evidence_ref"]) is str)

    @staticmethod
    def _evidence_items(candidate: OutputCandidate, association: CollectionAssociation,
                        source_key: tuple[str, str, str]) -> tuple[EvidenceItem, ...]:
        items = []
        raw = candidate.evidence
        for category in _EVIDENCE_CATEGORIES:
            if category not in raw:
                items.append(EvidenceItem(association, source_key, category, "missing", reason_code="missing"))
                continue
            value = raw[category]
            if value is None:
                items.append(EvidenceItem(association, source_key, category, "missing", reason_code="missing"))
                continue
            # Category-specific validation belongs to US4. Until then, retain the
            # declared optional value as invalid rather than assert its meaning.
            items.append(EvidenceItem(association, source_key, category, "invalid", reason_code="missing_interpretation"))
        return tuple(items)


class PrecomputedAdapter(ModelAdapter):
    """A request-scoped adapter view returning one accepted record's saved values."""

    def __init__(self, record: PredictionRecord) -> None:
        if not isinstance(record, PredictionRecord) or record.provenance.mode != "precomputed":
            raise InvalidCollectionRequest("record.primary")
        available = {item.category for item in record.evidence if item.state == "available"}
        capabilities = AdapterCapabilities(
            prediction_probability=record.primary.value_kind == "probability",
            feature_representation="feature_representation" in available,
            repeated_outputs="repeated_outputs" in available,
            modality_outputs="modality_outputs" in available,
            domain_metadata="domain_metadata" in available,
            explanation="explanation" in available,
            input_metadata="input_metadata" in available,
            available_modalities="available_modalities" in available,
        )
        super().__init__(capabilities)
        self._record = record

    def _check(self, patient_data: object, label: str) -> None:
        association_matches = type(patient_data) is CollectionAssociation and patient_data == self._record.association
        label_matches = type(label) is str and label == self._record.label_id
        if not association_matches or not label_matches:
            raise InvalidCollectionRequest("record.association" if not association_matches else "label_id")

    def _evidence(self, patient_data: object, label: str, category: str) -> object:
        self._check(patient_data, label)
        item = next((item for item in self._record.evidence if item.category == category), None)
        if item is None or item.state != "available":
            raise EvidenceUnavailable("evidence.state")
        return _thaw(item.value)

    def predict(self, patient_data: Any, label: str) -> object:
        self._check(patient_data, label)
        if self._record.primary.value_kind == "probability":
            return self._record.primary.predicted_class
        return self._record.primary.value

    def predict_probability(self, patient_data: Any, label: str) -> float:
        self._check(patient_data, label)
        if self._record.primary.value_kind != "probability":
            raise EvidenceUnavailable("primary.value_kind")
        return self._record.primary.value  # type: ignore[return-value]

    def extract_features(self, patient_data: Any, label: str) -> object:
        return self._evidence(patient_data, label, "feature_representation")

    def get_repeated_outputs(self, patient_data: Any, label: str) -> object:
        return self._evidence(patient_data, label, "repeated_outputs")

    def get_modality_outputs(self, patient_data: Any, label: str) -> object:
        return self._evidence(patient_data, label, "modality_outputs")

    def get_domain_metadata(self, patient_data: Any) -> object:
        return self._evidence(patient_data, self._record.label_id, "domain_metadata")

    def explain(self, patient_data: Any, label: str) -> object:
        return self._evidence(patient_data, label, "explanation")

    def get_input_metadata(self, patient_data: Any) -> object:
        return self._evidence(patient_data, self._record.label_id, "input_metadata")

    def get_available_modalities(self, patient_data: Any) -> object:
        return self._evidence(patient_data, self._record.label_id, "available_modalities")


def precomputed_adapter(record: PredictionRecord) -> PrecomputedAdapter:
    return PrecomputedAdapter(record)
