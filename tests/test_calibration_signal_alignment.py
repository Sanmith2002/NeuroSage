from dataclasses import replace
from hashlib import sha256

import pytest

from safira.calibration.verification import verify_signal_alignment
from safira.signals.validation import prediction_fingerprint
from training_fixtures import build_inputs


def test_calibration_signals_align_one_to_one_with_exact_dataset_rows(registered_collection):
    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    aligned = verify_signal_alignment(dataset, signals, reference)
    assert len(aligned) == len(dataset.development.calibration)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_source"])
def test_misaligned_calibration_feature_rows_are_rejected(registered_collection, mutation):
    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    calibration = signals.calibration
    if mutation == "missing":
        calibration = ()
    elif mutation == "extra":
        from safira.signals.records import SignalRowKey
        calibration = calibration + (replace(signals.calibration[0], row_key=SignalRowKey("extra-row")),)
    else:
        row = calibration[0]
        from safira.signals.records import SignalSourceKey
        source = SignalSourceKey("other", "v1", "label-a")
        calibration = (replace(row, source_key=source,
                               predictors=tuple(replace(item, source_key=source)
                                                for item in row.predictors)),)
    changed = replace(signals, calibration=calibration)
    with pytest.raises(Exception):
        verify_signal_alignment(dataset, changed, reference)


def test_signal_method_parameters_and_dataset_reference_must_match(registered_collection):
    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    row = signals.calibration[0]
    changed_result = replace(row.predictors[0], method_parameters={"different": True})
    changed_row = replace(row, predictors=(changed_result,))
    changed = replace(signals, calibration=(changed_row,))
    with pytest.raises(Exception):
        verify_signal_alignment(dataset, changed, reference)
    with pytest.raises(Exception):
        verify_signal_alignment(dataset, signals,
                                replace(reference, manifest_reference="stale-manifest"))
