"""Exact Feature 001/002 admission checks used by stateless signal methods."""

from __future__ import annotations

import hashlib
import json
import re

from safira.collection.records import PredictionRecord
from safira.collection.validation import validate_evidence_item, validate_primary_output
from safira.signals.base import SignalInputVerifier
from safira.signals.exceptions import SignalInputError, SignalVerificationError
from safira.signals.records import SignalInputCheck, SignalProtocol, SignalSourceKey


_ASSOCIATION_FIELDS = ("patient_ref", "assessment_ref", "occurrence_ref")
_CAPABILITY_BY_CATEGORY = {
    "feature_representation": "feature_representation",
    "repeated_outputs": "repeated_outputs",
    "modality_outputs": "modality_outputs",
    "domain_metadata": "domain_metadata",
    "explanation": "explanation",
    "input_metadata": "input_metadata",
    "available_modalities": "available_modalities",
}
_EVIDENCE_CATEGORIES = frozenset(_CAPABILITY_BY_CATEGORY)


def prediction_fingerprint(record: PredictionRecord) -> str:
    try:
        body = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()
    except Exception:
        raise SignalInputError("record_not_canonical") from None


def _association_tuple(record):
    return tuple(getattr(record.association, field) for field in _ASSOCIATION_FIELDS)


def verify_record_admission(verifier, record):
    if type(record) is not PredictionRecord:
        raise SignalInputError("record_type_invalid")
    if verifier is None or not callable(getattr(verifier, "verify_prediction", None)):
        raise SignalVerificationError("trusted_verifier_required")
    try:
        check = verifier.verify_prediction(record)
    except Exception:
        raise SignalVerificationError("prediction_check_failed") from None
    if type(check) is not SignalInputCheck:
        raise SignalVerificationError("prediction_check_invalid")
    expected = (
        prediction_fingerprint(record), record.source_key, _association_tuple(record),
        record.provenance.mode,
    )
    actual = (check.record_fingerprint, check.source_key, check.association, check.provenance_mode)
    references = (check.authority, check.method, check.evidence_ref, check.input_scope)
    if (actual != expected or check.state != "verified"
            or not all(type(value) is str and value.strip() for value in references)):
        raise SignalVerificationError("prediction_scope_unverified")
    if re.fullmatch(r"[0-9a-f]{64}", check.record_fingerprint) is None:
        raise SignalVerificationError("prediction_fingerprint_invalid")
    return check


def validate_registered_record(registry, protocol: SignalProtocol, record: PredictionRecord):
    key = SignalSourceKey(*record.source_key)
    if key not in protocol.source_keys:
        raise SignalInputError("source_outside_protocol")
    try:
        metadata = registry.get_metadata(record.model_id, record.model_version)
    except Exception:
        raise SignalInputError("registration_not_found") from None
    label = next((item for item in metadata.labels if item.label_id == record.label_id), None)
    if label is None:
        raise SignalInputError("label_not_registered")
    primary = record.primary
    try:
        if (primary.value_kind != label.value_kind
                or dict(primary.scale) != dict(label.value_scale)
                or primary.meaning != label.value_scale["meaning"]
                or primary.positive_direction != label.value_scale["positive_direction"]
                or dict(primary.class_mapping) != dict(label.class_mapping)):
            raise ValueError
        expected_primary = validate_primary_output(primary.value, label)
        if primary.predicted_class != expected_primary.predicted_class:
            raise ValueError
    except Exception:
        raise SignalInputError("primary_semantics_mismatch") from None

    expected_assurance = {
        ("live", "validated"): "verified_live_binding",
        ("precomputed", "unavailable"): "trusted_source_checked",
    }.get((record.provenance.mode, record.input_verification))
    if expected_assurance is None or record.provenance.assurance != expected_assurance:
        raise SignalInputError("source_assurance_invalid")

    details = record.provenance.details
    if record.provenance.mode == "live":
        expected_details = {
            "classifier_sha256": metadata.classifier_artifact["sha256"],
            "adapter_id": metadata.adapter.adapter_id,
            "adapter_version": metadata.adapter.adapter_version,
            "adapter_fingerprint": metadata.adapter.implementation_fingerprint,
            "output_selector": label.output_selector,
            "value_source": label.value_source,
        }
        if any(details.get(name) != value for name, value in expected_details.items()):
            raise SignalInputError("live_source_identity_mismatch")
        if not isinstance(details.get("identity_scope"), str) or not details["identity_scope"].strip():
            raise SignalInputError("live_source_identity_incomplete")
    else:
        expected_details = ("source_contract_id", "source_contract_version", "integration_id",
                            "check_method", "independent_evidence_ref", "event_id",
                            "content_binding_method", "external_selector")
        if any(type(details.get(name)) is not str or not details[name].strip()
               for name in expected_details):
            raise SignalInputError("precomputed_provenance_incomplete")
        if (details.get("content_bound") is not True or details.get("association_bound") is not True
                or details.get("fresh") is not True or details.get("not_revoked") is not True
                or details.get("unused") is not True
                or details.get("registered_output_selector") != label.output_selector):
            raise SignalInputError("precomputed_provenance_invalid")

    seen = set()
    capabilities = metadata.adapter.capabilities.to_dict()
    for evidence in record.evidence:
        if evidence.category in seen:
            raise SignalInputError("duplicate_evidence_category")
        seen.add(evidence.category)
        if evidence.category not in _EVIDENCE_CATEGORIES:
            raise SignalInputError("evidence_category_invalid")
        if evidence.association != record.association or evidence.source_key != record.source_key:
            raise SignalInputError("evidence_source_mismatch")
        capability = _CAPABILITY_BY_CATEGORY.get(evidence.category)
        if (record.provenance.mode == "live" and capability is not None
                and evidence.state == "available" and not capabilities.get(capability, False)):
            raise SignalInputError("evidence_capability_mismatch")
        if evidence.state == "available":
            try:
                checked = validate_evidence_item(
                    record.association, record.source_key, evidence.category,
                    evidence.value, evidence.interpretation,
                )
            except Exception:
                raise SignalInputError("evidence_validation_failed") from None
            if checked.state != "available":
                raise SignalInputError("evidence_validation_failed")
    return metadata, label


def verify_and_validate_record(registry, protocol, verifier, record):
    check = verify_record_admission(verifier, record)
    validate_registered_record(registry, protocol, record)
    return check
