"""T004: exact input admission must use independently checked Feature 002 lineage."""

from dataclasses import replace

import pytest

from safira.collection import PrimaryOutput, SourceProvenance
from safira.signals.exceptions import SignalInputError, SignalProtocolError, SignalVerificationError
from safira.signals.service import SignalExtractor

from signals_fixtures import SyntheticSignalVerifier, make_live_record, signal_protocol


def _extractor(registry, source_key, verifier):
    protocol = signal_protocol(source_key, {"evidence_coverage": {"required_evidence": []}})
    return SignalExtractor(registry, protocol, verifier)


def test_exact_record_admission_succeeds_and_records_verifier_call(registered_collection):
    registry, register = registered_collection
    definition, adapter, record = make_live_record(registry, register)
    calls_before = tuple(adapter.calls)
    verifier = SyntheticSignalVerifier()
    verifier.admit(record)
    results = _extractor(registry, record.source_key, verifier).extract_record(record)
    assert results and verifier.calls
    assert all(item.source_key.to_tuple() == record.source_key for item in results)
    assert len(results[0].provenance["admission_check_sha256"]) == 64
    assert "opaque-synthetic-patient" not in str(results[0].to_dict())
    assert tuple(adapter.calls) == calls_before


def test_absent_verifier_fails_closed_without_exposing_patient_reference(registered_collection):
    registry, register = registered_collection
    definition, _, record = make_live_record(registry, register)
    with pytest.raises(SignalProtocolError) as error:
        _extractor(registry, record.source_key, None).extract_record(record)
    assert "opaque-synthetic-patient" not in str(error.value)


def test_unregistered_record_content_is_rejected_by_independent_ledger(registered_collection):
    registry, register = registered_collection
    definition, _, record = make_live_record(registry, register)
    verifier = SyntheticSignalVerifier()
    verifier.admit(record)
    altered = replace(record, primary=replace(record.primary, value=0.71))
    with pytest.raises(SignalVerificationError):
        _extractor(registry, record.source_key, verifier).extract_record(altered)


def test_caller_constructed_record_without_independent_ledger_entry_is_rejected(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    verifier = SyntheticSignalVerifier()
    with pytest.raises(SignalVerificationError):
        _extractor(registry, record.source_key, verifier).extract_record(record)


def test_stale_evidence_content_fails_exact_admission(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    verifier = SyntheticSignalVerifier()
    verifier.admit(record)
    evidence = replace(record.evidence[0], reason_code="invalid")
    altered = replace(record, evidence=(evidence, *record.evidence[1:]))
    with pytest.raises(SignalVerificationError):
        _extractor(registry, record.source_key, verifier).extract_record(altered)


@pytest.mark.parametrize("field,value", [("model_version", "v2"), ("label_id", "other")])
def test_wrong_registered_version_or_label_fails_safely(registered_collection, field, value):
    registry, register = registered_collection
    definition, _, record = make_live_record(registry, register)
    verifier = SyntheticSignalVerifier()
    source_key = (
        record.model_id,
        value if field == "model_version" else record.model_version,
        value if field == "label_id" else record.label_id,
    )
    changed = replace(record, **{field: value}, provenance=SourceProvenance(
        record.provenance.mode, record.association, source_key,
        record.provenance.assurance, record.provenance.details,
    ), evidence=tuple(replace(item, source_key=source_key) for item in record.evidence))
    verifier.admit(changed)
    with pytest.raises(SignalInputError):
        _extractor(registry, record.source_key, verifier).extract_record(changed)


def test_forged_live_assurance_is_rejected_even_when_record_is_ledgered(registered_collection):
    registry, register = registered_collection
    definition, _, record = make_live_record(registry, register)
    forged_provenance = SourceProvenance(
        "precomputed", record.association, record.source_key, "unverified_claim", {},
    )
    forged = replace(record, provenance=forged_provenance, input_verification="unavailable")
    verifier = SyntheticSignalVerifier()
    verifier.admit(forged)
    with pytest.raises(SignalInputError):
        _extractor(registry, record.source_key, verifier).extract_record(forged)


def test_precomputed_record_requires_and_preserves_independent_source_check(registered_collection):
    registry, register = registered_collection
    definition, _, record = make_live_record(registry, register)
    details = {
        "source_contract_id": "synthetic-contract", "source_contract_version": "v1",
        "integration_id": "synthetic-precomputed-ledger", "check_method": "exact content binding",
        "independent_evidence_ref": "event-ledger-ref", "event_id": "synthetic-event",
        "content_binding_method": "source-specific evidence", "external_selector": "output-1",
        "content_bound": True, "association_bound": True, "fresh": True,
        "not_revoked": True, "unused": True, "registered_output_selector": 0,
    }
    provenance = SourceProvenance(
        "precomputed", record.association, record.source_key, "trusted_source_checked", details,
    )
    precomputed = replace(record, provenance=provenance, input_verification="unavailable")
    verifier = SyntheticSignalVerifier()
    verifier.admit(precomputed)
    result = _extractor(registry, precomputed.source_key, verifier).extract_record(precomputed)
    assert result
    assert result[0].provenance["mode"] == "precomputed"
    assert result[0].provenance["assurance"] == "trusted_source_checked"


def test_extractor_never_calls_classifier_adapter_again(registered_collection):
    registry, register = registered_collection
    _, adapter, record = make_live_record(registry, register)
    before = tuple(adapter.calls)
    verifier = SyntheticSignalVerifier()
    verifier.admit(record)
    _extractor(registry, record.source_key, verifier).extract_record(record)
    assert tuple(adapter.calls) == before


def test_non_probability_registered_output_cannot_be_coerced(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(
        registry, register, model_id="margin-model", value_kinds=("continuous_score",), scores=(0.3,),
    )
    verifier = SyntheticSignalVerifier()
    verifier.admit(record)
    results = SignalExtractor(
        registry,
        signal_protocol(record.source_key, {"bernoulli_entropy": {"log_base": 2}}),
        verifier,
    ).extract_record(record)
    assert results[0].state.value == "invalid"
    assert results[0].value is None
