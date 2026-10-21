from dataclasses import replace

import pytest

from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope


def _make(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    prediction_ledger = SyntheticSignalVerifier()
    ledger = SyntheticTrainingLedger(prediction_ledger)
    ledger.admit(dataset, signals, reference)
    return registry, dataset, signals, reference, ledger


def test_independent_ledger_accepts_exact_inputs_and_executes_prediction_checks(registered_collection):
    from safira.training.verification import _verify_training_inputs as verify_training_inputs

    registry, dataset, signals, reference, ledger = _make(registered_collection)
    admitted = verify_training_inputs(registry, dataset, signals, reference, ledger,
                                      scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))
    assert admitted._input_check.dataset_fingerprint
    assert ledger.calls[0][0] == "inputs"
    assert len(ledger.prediction_ledger.calls) == 4


def test_absent_provider_and_unledgered_inputs_fail_closed(registered_collection):
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, None,
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, ledger,
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_changed_dataset_or_signal_content_requires_fresh_independent_admission(registered_collection):
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs

    registry, dataset, signals, reference, ledger = _make(registered_collection)
    changed_example = replace(dataset.development.train[0], correctness_target=0)
    changed_train = (changed_example,) + dataset.development.train[1:]
    changed_dataset = replace(dataset, development=replace(dataset.development, train=changed_train))
    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, changed_dataset, signals, reference, ledger,
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_caller_assertion_only_verifier_cannot_replace_missing_prediction_ledger(registered_collection):
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    empty_prediction_ledger = SyntheticSignalVerifier()
    independently_registered_inputs = SyntheticTrainingLedger(empty_prediction_ledger)
    independently_registered_inputs.admit(dataset, signals, reference, admit_predictions=False)

    class AssertionOnly:
        def verify_inputs(self, *_):
            return independently_registered_inputs.verify_inputs(dataset, signals)

        def verify_dataset(self, *_):
            return independently_registered_inputs.verify_dataset(dataset, reference)

        def verify_prediction(self, record):
            return empty_prediction_ledger.verify_prediction(record)

    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, AssertionOnly(),
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_boolean_only_verifier_response_is_not_admission(registered_collection):
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)

    class BooleanOnly:
        def verify_inputs(self, *_):
            return True

    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, BooleanOnly(),
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


@pytest.mark.parametrize("response", ["a" * 64, None])
def test_digest_or_missing_only_verifier_response_is_not_admission(registered_collection, response):
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)

    class DigestOnly:
        def verify_inputs(self, *_):
            return response

    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, DigestOnly(),
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_mismatched_manifest_digest_from_provider_fails_closed(registered_collection):
    from dataclasses import replace
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)

    class StaleLedger:
        verify_dataset = ledger.verify_dataset
        verify_prediction = ledger.verify_prediction

        def verify_inputs(self, *args):
            return replace(ledger.verify_inputs(*args), manifest_digest="0" * 64)

    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, StaleLedger(),
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_stale_feature_run_identity_and_wrong_dataset_protocol_scope_fail(registered_collection):
    from dataclasses import replace
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)

    class StaleRunLedger:
        verify_dataset = ledger.verify_dataset
        verify_prediction = ledger.verify_prediction

        def verify_inputs(self, *args):
            return replace(ledger.verify_inputs(*args), feature_run_version="stale-run")

    exact_scope = training_scope(registry, *signals.training[0].source_key.to_tuple())
    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, StaleRunLedger(), scopes=(exact_scope,))
    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals,
                               replace(reference, protocol_version="stale"), ledger, scopes=(exact_scope,))
