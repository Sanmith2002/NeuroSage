from dataclasses import replace

import pytest

from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope


def test_cross_partition_patient_group_is_rejected_before_eligibility(registered_collection):
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    cross_patient = replace(dataset.development.validation[0], patient_group_ref="g1")
    dataset = replace(dataset, development=replace(dataset.development,
        validation=(cross_patient,)))
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)

    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, ledger,
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_correctness_target_is_not_copied_to_predictor_record(registered_collection):
    registry, register = registered_collection
    _, dataset, signals, _ = build_inputs(registry, register)
    feature = signals.training[0]
    assert not hasattr(feature, "correctness_target")
    assert not hasattr(feature, "patient_group_ref")
    assert dataset.development.train[0].correctness_target in (0, 1)


def test_target_only_change_never_changes_feature_predictors(registered_collection):
    import json
    registry, register = registered_collection
    _, dataset, signals, _ = build_inputs(registry, register)
    predictor_before = json.dumps(signals.training[0].to_dict(), sort_keys=True)
    changed = replace(dataset.development.train[0], correctness_target=1 - dataset.development.train[0].correctness_target)
    changed_dataset = replace(dataset, development=replace(
        dataset.development, train=(changed,) + dataset.development.train[1:]))

    assert changed_dataset.development.train[0].correctness_target != dataset.development.train[0].correctness_target
    assert json.dumps(signals.training[0].to_dict(), sort_keys=True) == predictor_before
    assert "correctness_target" not in predictor_before


def test_outcome_group_role_and_verification_mutations_need_fresh_dataset_admission(registered_collection):
    from dataclasses import replace
    import pytest
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import SyntheticTrainingLedger, training_scope

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    scope = training_scope(registry, "training-model", "v1", "label-a")
    mutate = (
        replace(dataset.development.train[0], outcome=1 - dataset.development.train[0].outcome),
        replace(dataset.development.train[0], patient_group_ref="changed-group"),
        replace(dataset.development.train[0], partition_role="validation"),
        replace(dataset.development.train[0], verification_ref="changed-verification"),
    )
    for changed_example in mutate:
        changed_dataset = replace(dataset, development=replace(
            dataset.development, train=(changed_example,) + dataset.development.train[1:]))
        ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
        ledger.admit(dataset, signals, reference)
        with pytest.raises(TrainingVerificationError):
            _verify_training_inputs(registry, changed_dataset, signals, reference, ledger, scopes=(scope,))
