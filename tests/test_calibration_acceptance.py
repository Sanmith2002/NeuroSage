from safira.calibration.verification import verify_prediction_admission
from safira.registry import ModelRegistry
from safira.signals.records import SignalSourceKey
from signals_fixtures import SyntheticSignalVerifier, make_live_record, signal_protocol


def test_exact_scope_admission_preserves_all_supported_classifier_configurations(registered_collection):
    registry, register = registered_collection
    records = []
    records.append(make_live_record(registry, register, model_id="single", labels=("binary",))[2])
    records.extend(make_live_record(registry, register, model_id="multi",
                                    labels=("label-a", "label-b"), scores=(.3, .8))[2:3])
    records.append(make_live_record(registry, register, model_id="source-a", labels=("shared",))[2])
    records.append(make_live_record(registry, register, model_id="source-b", labels=("shared",), scores=(.9,))[2])
    records.append(make_live_record(registry, register, model_id="versioned", version="v1",
                                    labels=("same-label",))[2])
    records.append(make_live_record(registry, register, model_id="versioned", version="v2",
                                    labels=("same-label",), scores=(.6,))[2])

    accepted = []
    for record in records:
        verifier = SyntheticSignalVerifier()
        verifier.admit(record)
        protocol = signal_protocol(record.source_key, {"evidence_coverage": {"required_evidence": []}})
        check = verify_prediction_admission(registry, protocol, verifier, record)
        assert check.source_key == record.source_key
        accepted.append(SignalSourceKey(*record.source_key))
    assert accepted[0] != accepted[1]
    assert accepted[2].label_id == accepted[3].label_id == "shared"
    assert accepted[2] != accepted[3]
    assert accepted[4].model_id == accepted[5].model_id == "versioned"
    assert accepted[4].model_version != accepted[5].model_version


def test_package_does_not_export_calibration_or_per_patient_application_api():
    import safira.calibration as calibration
    assert "calibrate" not in calibration.__all__
    assert "predict" not in calibration.__all__
    assert not hasattr(calibration, "SafetyAssessment")


def test_signal_run_ledger_requires_exact_previously_admitted_content(registered_collection):
    from dataclasses import replace
    import pytest
    from calibration_ledgers import SignalRunLedger
    from training_fixtures import build_inputs

    registry, register = registered_collection
    _, _, signals, _ = build_inputs(registry, register)
    ledger = SignalRunLedger()
    with pytest.raises(ValueError):
        ledger.verify(signals)
    ledger.admit(signals)
    ledger.verify(signals)
    changed = replace(signals, cohort_support={"synthetic": "changed"})
    with pytest.raises(ValueError):
        ledger.verify(changed)
