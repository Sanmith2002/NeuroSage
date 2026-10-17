"""Live prediction collection through exact, validated Feature 001 bindings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from safira.collection.exceptions import (
    ContributorMismatch, InvalidCollectionRequest, InvalidPrimaryOutput,
)
from safira.collection.records import (
    CollectionAssociation, CollectionResult, EvidenceItem, PredictionRecord,
    SourceProvenance, _freeze,
)
from safira.collection.validation import (
    _matches_shape_and_type, validate_input_structure, validate_primary_output,
    validate_source_key,
)
from safira.registry import ModelRegistry


# Boolean capabilities remain those of the existing ModelAdapter contract.
_OPTIONAL_METHODS = {
    "feature_representation": ("extract_features", True),
    "repeated_outputs": ("get_repeated_outputs", True),
    "modality_outputs": ("get_modality_outputs", True),
    "domain_metadata": ("get_domain_metadata", False),
    "explanation": ("explain", True),
    "input_metadata": ("get_input_metadata", False),
    "available_modalities": ("get_available_modalities", False),
}


@dataclass(frozen=True)
class LiveRequest:
    """Exact contributor plus owner-supplied declarations for this live input.

    Modality names are explicit input declarations, not inferred from registry
    metadata or optional evidence. Interpretation describes adapter results;
    it does not add methods to the adapter. All containers are detached.
    """

    model_id: str
    model_version: str
    label_id: str
    available_modalities: tuple[str, ...] | None = None
    evidence_interpretation: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        for name in ("model_id", "model_version", "label_id"):
            value = getattr(self, name)
            if type(value) is not str or not value or value != value.strip():
                raise InvalidCollectionRequest(name)
        if self.available_modalities is not None:
            if not isinstance(self.available_modalities, (tuple, list)):
                raise InvalidCollectionRequest("input.modality")
            modalities = tuple(self.available_modalities)
            if any(type(value) is not str or not value.strip() for value in modalities):
                raise InvalidCollectionRequest("input.modality")
            if len(set(modalities)) != len(modalities):
                raise InvalidCollectionRequest("input.modality")
            object.__setattr__(self, "available_modalities", modalities)
        if not isinstance(self.evidence_interpretation, Mapping):
            raise InvalidCollectionRequest("evidence.interpretation")
        object.__setattr__(self, "evidence_interpretation",
                           _freeze(self.evidence_interpretation, "evidence.interpretation"))


def _initial_item(association, key, category, value, interpretation):
    """Conservative initial validation; US4 adds advanced interpretation rules."""
    if value is None:
        return EvidenceItem(association, key, category, "missing")
    if not isinstance(interpretation, Mapping):
        interpretation = {}
    if category in ("input_metadata", "domain_metadata"):
        valid = isinstance(value, Mapping) and bool(value)
        interpretation = interpretation or {"meaning": "adapter-reported descriptive metadata"}
    elif category == "available_modalities":
        valid = (
            isinstance(value, (list, tuple))
            and all(type(v) is str and v.strip() for v in value)
            and len(set(value)) == len(value)
        )
        interpretation = interpretation or {"meaning": "adapter-reported modality identifiers"}
    elif category == "feature_representation":
        shape = interpretation.get("shape")
        valid = (
            isinstance(shape, (list, tuple))
            and all(d is None or (type(d) is int and d >= 0) for d in shape)
            and _matches_shape_and_type(value, tuple(shape), "number")
        )
    else:
        # Repeated/modality outputs and explanations require the advanced
        # category-specific interpretation validation in T030/T031. Do not
        # present a merely copyable value as validated before that work.
        valid = False
    if not isinstance(interpretation.get("meaning"), str) or not interpretation["meaning"].strip():
        return EvidenceItem(association, key, category, "invalid", reason_code="missing_interpretation")
    if not valid:
        return EvidenceItem(association, key, category, "invalid", reason_code="validation_failed")
    return EvidenceItem(association, key, category, "available", value=value, interpretation=interpretation)


def collect_live(registry, association, requests, patient_data, *, component=None):
    """Collect exact requested labels and return one atomic in-memory result.

    Each request is a LiveRequest or a (model_id, model_version, label_id)
    tuple. Use LiveRequest for explicit input modality/evidence declarations.
    Registry failures retain their existing typed categories. Component-level
    mapping/completeness validation belongs to User Story 3.
    """
    if not isinstance(registry, ModelRegistry) or not isinstance(association, CollectionAssociation):
        raise InvalidCollectionRequest("request")
    if component is not None:
        raise InvalidCollectionRequest("component.identity")
    try:
        supplied = tuple(requests)
    except Exception:
        raise InvalidCollectionRequest("request") from None
    if not supplied:
        raise InvalidCollectionRequest("request")

    # Preflight the entire envelope before any patient-facing adapter method.
    prepared = []
    bindings = {}
    seen = set()
    for candidate in supplied:
        if isinstance(candidate, LiveRequest):
            request = candidate
        elif isinstance(candidate, (tuple, list)) and len(candidate) == 3:
            request = LiveRequest(*candidate)
        else:
            raise InvalidCollectionRequest("request")
        key = validate_source_key(association, request.model_id, request.model_version, request.label_id)
        if key in seen:
            raise InvalidCollectionRequest("record.source_key")
        seen.add(key)
        model_key = (request.model_id, request.model_version)
        if model_key not in bindings:
            bindings[model_key] = registry.resolve_usable(*model_key)
        usable = bindings[model_key]
        label = next((label for label in usable.metadata.labels if label.label_id == request.label_id), None)
        if label is None:
            raise ContributorMismatch("label_id")
        validate_input_structure(patient_data, usable.metadata.input,
                                 available_modalities=request.available_modalities)
        prepared.append((request, usable, label))

    primaries = []
    for request, usable, label in prepared:
        try:
            value = getattr(usable.adapter, label.value_source)(patient_data, label.label_id)
        except Exception:
            raise InvalidPrimaryOutput("primary.value") from None
        primaries.append(validate_primary_output(value, label))

    records = []
    for (request, usable, label), primary in zip(prepared, primaries):
        source_key = (request.model_id, request.model_version, request.label_id)
        evidence = []
        capabilities = usable.metadata.adapter.capabilities
        for category, (method, has_label) in _OPTIONAL_METHODS.items():
            if not capabilities.supports(category):
                item = EvidenceItem(association, source_key, category, "unsupported")
            else:
                try:
                    args = (patient_data, label.label_id) if has_label else (patient_data,)
                    value = getattr(usable.adapter, method)(*args)
                except Exception:
                    item = EvidenceItem(association, source_key, category, "unavailable",
                                        reason_code="extraction_failed")
                else:
                    try:
                        item = _initial_item(association, source_key, category, value,
                                             request.evidence_interpretation.get(category, {}))
                        if (category == "available_modalities" and item.state == "available"
                                and request.available_modalities is not None
                                and set(item.value) != set(request.available_modalities)):
                            item = EvidenceItem(association, source_key, category, "invalid",
                                                reason_code="source_mismatch")
                    except Exception:
                        # Optional validation hooks/containers are untrusted too.
                        item = EvidenceItem(association, source_key, category, "invalid",
                                            reason_code="validation_failed")
            evidence.append(item)
        metadata = usable.metadata
        provenance = SourceProvenance(
            mode="live", association=association, source_key=source_key,
            assurance="verified_live_binding", details={
                "classifier_sha256": metadata.classifier_artifact["sha256"],
                "adapter_id": metadata.adapter.adapter_id,
                "adapter_version": metadata.adapter.adapter_version,
                "adapter_fingerprint": metadata.adapter.implementation_fingerprint,
                "output_selector": label.output_selector,
                "value_source": label.value_source,
                "identity_scope": "pair verified at registration or attachment; resolved by registry",
                "limits": ["No fresh identity-provider check at collection; owner must keep the loaded pair fixed.",
                           "Binding compatibility does not establish clinical safety."],
            },
        )
        records.append(PredictionRecord(
            association=association, model_id=request.model_id, model_version=request.model_version,
            label_id=request.label_id, primary=primary, provenance=provenance,
            evidence=tuple(evidence), input_verification="validated",
        ))
    return CollectionResult(association, tuple(records))
