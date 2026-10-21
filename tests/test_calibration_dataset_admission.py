from dataclasses import replace

import pytest

from safira.calibration.verification import verify_dataset_inputs
from safira.signals.records import SignalDatasetCheck
from safira.signals.validation import dataset_fingerprint
from signals_fixtures import SyntheticSignalVerifier
from training_fixtures import build_inputs


class DatasetLedger:
    def __init__(self, prediction_ledger):
        self.prediction_ledger = prediction_ledger
        self.entries = set()

    def admit(self, dataset):
        self.entries.add(dataset_fingerprint(dataset))
        for role in ("train", "validation", "calibration"):
            for example in getattr(dataset.development, role):
                self.prediction_ledger.admit(example.prediction)

    def verify_dataset(self, dataset, reference):
        from safira.signals.validation import _dataset_rows
        if dataset_fingerprint(dataset) not in self.entries:
            raise ValueError("unadmitted dataset")
        return SignalDatasetCheck(
            dataset_fingerprint(dataset), reference.dataset_id, reference.protocol_id,
            reference.protocol_version, reference.manifest_reference, reference.builder_version,
            "ready", "synthetic-ledger", "exact lookup", "dataset-entry",
            _dataset_rows(dataset), reference.manifest_digest,
            ("train", "validation", "calibration"),
        )

    def verify_prediction(self, record):
        return self.prediction_ledger.verify_prediction(record)


def setup(registry, register):
    _, dataset, signals, reference = build_inputs(registry, register)
    predictions = SyntheticSignalVerifier()
    verifier = DatasetLedger(predictions)
    verifier.admit(dataset)
    protocol = None
    from safira.signals.records import SignalProtocol
    protocol = SignalProtocol("calibration", "v1", signals.manifest.source_keys,
                              {item.method_id: item for item in signals.manifest.method_configs}, {})
    return dataset, reference, verifier, protocol


def test_complete_manifest_bound_calibration_inventory_is_admitted(registered_collection):
    registry, register = registered_collection
    dataset, reference, verifier, protocol = setup(registry, register)
    check = verify_dataset_inputs(registry, protocol, verifier, dataset, reference)
    assert check.manifest_digest == reference.manifest_digest
    assert check.authorized_partitions == ("train", "validation", "calibration")


def test_missing_or_changed_dataset_inventory_fails_closed(registered_collection):
    registry, register = registered_collection
    dataset, reference, verifier, protocol = setup(registry, register)
    changed = replace(dataset, development=replace(dataset.development, calibration=()))
    with pytest.raises(Exception):
        verify_dataset_inputs(registry, protocol, verifier, changed, reference)


def test_unverified_embedded_prediction_fails_even_with_dataset_entry(registered_collection):
    registry, register = registered_collection
    dataset, reference, verifier, protocol = setup(registry, register)
    verifier.prediction_ledger = SyntheticSignalVerifier()
    with pytest.raises(Exception):
        verify_dataset_inputs(registry, protocol, verifier, dataset, reference)


def test_cross_partition_patient_group_is_rejected_even_when_dataset_is_ledgered(registered_collection):
    registry, register = registered_collection
    dataset, reference, verifier, protocol = setup(registry, register)
    train = list(dataset.development.train)
    train[0] = replace(train[0], patient_group_ref=dataset.development.validation[0].patient_group_ref)
    changed = replace(dataset, development=replace(dataset.development, train=tuple(train)))
    verifier.admit(changed)
    with pytest.raises(Exception):
        verify_dataset_inputs(registry, protocol, verifier, changed, reference)


def test_forged_correctness_target_is_rejected_without_matching_manifest_admission(registered_collection):
    registry, register = registered_collection
    dataset, reference, verifier, protocol = setup(registry, register)
    train = list(dataset.development.train)
    train[0] = replace(train[0], correctness_target=1 - train[0].correctness_target)
    changed = replace(dataset, development=replace(dataset.development, train=tuple(train)))
    with pytest.raises(Exception):
        verify_dataset_inputs(registry, protocol, verifier, changed, reference)
