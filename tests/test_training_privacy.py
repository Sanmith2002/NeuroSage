import json
from pathlib import Path

from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope
from signals_fixtures import SyntheticSignalVerifier


def test_outcome_repr_export_and_errors_do_not_expose_restricted_markers(registered_collection):
    from safira.training.records import (TrainingOutcome, TrainingProtocol, TrainingStatus,
                                         TrainingSupportCriteria)
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.service import SafetyTrainingService

    registry, register = registered_collection
    _, dataset, signals, _ = build_inputs(registry, register)
    scope = training_scope(registry, "training-model", "v1", "label-a")
    protocol = TrainingProtocol("p", "v1", (scope,),
        {scope.source_key: TrainingSupportCriteria(2, {0: 1, 1: 1})},
        {scope.source_key: ()})
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, signals.dataset_reference)
    outcome = SafetyTrainingService(registry, protocol, ledger).prepare(dataset, signals)[0]
    surfaces = (repr(outcome), json.dumps(outcome.to_dict()), str(TrainingVerificationError("admission_rejected")),
                repr(TrainingVerificationError("admission_rejected")))
    forbidden = ("opaque-g1", "assessment-g1", "occ-g1", "synthetic-outcome-check",
                 "correctness_target", "protected_test", "synthetic-feature")
    assert all(marker not in " ".join(surfaces) for marker in forbidden)
    assert str(TrainingVerificationError("patient-id-should-not-leak")) == "training_error"
    assert all(hasattr(row, "predictors") for row in signals.training)

    fixture_source = Path(__file__).with_name("training_fixtures.py").read_text(encoding="utf-8").lower()
    assert all(marker not in fixture_source for marker in
               ("date_of_birth", "medical_record_number", "patient_name", "real clinical dataset"))
