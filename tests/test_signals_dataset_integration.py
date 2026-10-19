"""Synthetic adversarial tests for the Feature 003 admission boundary."""

from dataclasses import replace

import pytest

from safira.signals.exceptions import SignalVerificationError
from safira.signals.records import Feature003DatasetReference
from safira.signals.validation import verify_dataset_admission
from tests.signals_fixtures import make_synthetic_feature003_result, make_live_record


class DatasetLedger:
    """Independent test ledger binding the complete input and each row."""

    def __init__(self, record_verifier, reference):
        from safira.signals.validation import dataset_fingerprint
        from safira.signals.records import SignalDatasetCheck, SignalDatasetRowCheck
        self.record_verifier = record_verifier
        self.reference = reference
        self.dataset_fingerprint = dataset_fingerprint
        self.check_type = SignalDatasetCheck
        self.row_type = SignalDatasetRowCheck

    def verify_dataset(self, result, reference):
        rows = []
        for role in ("train", "validation", "calibration"):
            for example in getattr(result.development, role):
                record = example.prediction
                rows.append(self.row_type(
                    record_fingerprint=self.record_verifier.fingerprint(record),
                    source_key=record.source_key,
                    association=(record.association.patient_ref, record.association.assessment_ref,
                                 record.association.occurrence_ref),
                    partition=role,
                ))
        return self.check_type(
            dataset_fingerprint=self.dataset_fingerprint(result),
            dataset_id=self.reference.dataset_id, protocol_id=self.reference.protocol_id,
            protocol_version=self.reference.protocol_version,
            manifest_reference=self.reference.manifest_reference,
            builder_version=self.reference.builder_version, readiness="ready",
            authority="synthetic-independent-dataset-ledger", method="exact inventory comparison",
            evidence_ref="synthetic-dataset-evidence", rows=tuple(rows),
            manifest_digest=reference.manifest_digest,
            authorized_partitions=("train", "validation", "calibration"),
        )


def _reference(result):
    return Feature003DatasetReference("d1", "p1", "1", result.manifest_reference, "builder-v1")


def _example_record(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register, labels=("label-a",))
    return record


def test_dataset_gate_accepts_exact_row_complete_independent_verification(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier
    record_verifier = SyntheticSignalVerifier()
    record = _example_record(registered_collection)
    record_verifier.admit(record)
    result = make_synthetic_feature003_result({"train": ((record, "opaque-g1"),)})
    reference = _reference(result)
    verifier = DatasetLedger(record_verifier, reference)
    check = verify_dataset_admission(verifier, record_verifier, result, reference)
    assert check.dataset_id == "d1"
    assert check.verified_row_count == 1


def test_dataset_gate_rejects_forged_row_inserted_after_dataset_identity(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier
    record_verifier = SyntheticSignalVerifier()
    admitted = _example_record(registered_collection)
    record_verifier.admit(admitted)
    result = make_synthetic_feature003_result({"train": ((admitted, "opaque-g1"),)})
    reference = _reference(result)
    forged = replace(admitted, primary=replace(admitted.primary, value=0.9))
    forged_result = make_synthetic_feature003_result({"train": ((forged, "opaque-g1"),)})
    with pytest.raises(SignalVerificationError):
        verify_dataset_admission(DatasetLedger(record_verifier, reference), record_verifier,
                                 forged_result, reference)


def test_dataset_gate_rejects_missing_or_substituted_inventory_and_scope(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier
    record_verifier = SyntheticSignalVerifier()
    record = _example_record(registered_collection)
    record_verifier.admit(record)
    result = make_synthetic_feature003_result({"train": ((record, "opaque-g1"),)})
    reference = _reference(result)
    ledger = DatasetLedger(record_verifier, reference)

    class EmptyInventory:
        def verify_dataset(self, dataset, ref):
            check = ledger.verify_dataset(dataset, ref)
            return replace(check, rows=())

    with pytest.raises(SignalVerificationError):
        verify_dataset_admission(EmptyInventory(), record_verifier, result, reference)
    with pytest.raises(SignalVerificationError):
        verify_dataset_admission(ledger, record_verifier, result,
                                 replace(reference, protocol_version="stale"))


def test_dataset_gate_rejects_caller_constructed_check_without_executed_verifier(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier
    record_verifier = SyntheticSignalVerifier()
    record = _example_record(registered_collection)
    result = make_synthetic_feature003_result({"train": ((record, "opaque-g1"),)})
    reference = _reference(result)

    class AssertionOnly:
        def verify_dataset(self, *_):
            from safira.signals.records import SignalDatasetCheck
            return SignalDatasetCheck(
                dataset_fingerprint="caller-assertion", dataset_id=reference.dataset_id,
                protocol_id=reference.protocol_id, protocol_version=reference.protocol_version,
                manifest_reference=reference.manifest_reference, builder_version=reference.builder_version,
                readiness="ready", authority="caller", method="asserted", evidence_ref="claimed", rows=(),
            )

    with pytest.raises(SignalVerificationError):
        verify_dataset_admission(AssertionOnly(), record_verifier, result, reference)


def test_dataset_gate_rejects_same_patient_group_crossing_development_partitions(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier
    record_verifier = SyntheticSignalVerifier()
    record = _example_record(registered_collection)
    record_verifier.admit(record)
    result = make_synthetic_feature003_result({
        "train": ((record, "same-opaque-group"),),
        "validation": ((record, "same-opaque-group"),),
    })
    reference = _reference(result)
    with pytest.raises(SignalVerificationError):
        verify_dataset_admission(DatasetLedger(record_verifier, reference), record_verifier,
                                 result, reference)
