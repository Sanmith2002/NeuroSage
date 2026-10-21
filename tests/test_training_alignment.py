from dataclasses import replace

import pytest

from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope


def test_wrong_feature_row_key_is_rejected_even_after_fixture_admission(registered_collection):
    from safira.signals.records import SignalRowKey
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    broken = replace(signals.training[0], row_key=SignalRowKey("wrong-row-key"))
    signals = replace(signals, training=(broken,) + signals.training[1:])
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)

    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, ledger,
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_extra_feature_row_is_rejected_after_independent_admission(registered_collection):
    from safira.signals.records import SignalFeatureRecord, SignalRowKey
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    extra = SignalFeatureRecord(SignalRowKey("extra-row"), signals.training[0].source_key,
                                signals.training[0].predictors)
    signals = replace(signals, training=signals.training + (extra,))
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)

    with pytest.raises(TrainingVerificationError):
        verify_training_inputs(registry, dataset, signals, reference, ledger,
                               scopes=(training_scope(registry, *signals.training[0].source_key.to_tuple()),))


def test_cross_role_feature_row_and_duplicate_feature_key_are_rejected(registered_collection):
    from dataclasses import replace
    from safira.signals.records import SignalFeatureSet

    registry, register = registered_collection
    _, dataset, signals, _ = build_inputs(registry, register)
    with pytest.raises(ValueError):
        SignalFeatureSet(signals.dataset_reference, signals.training + (signals.training[0],),
                         signals.validation, signals.calibration, signals.manifest, {})
    cross_role = replace(signals, training=signals.training[1:],
                         validation=(signals.training[0],) + signals.validation)
    assert len(cross_role.training) + len(cross_role.validation) == len(signals.training) + len(signals.validation)


@pytest.mark.parametrize("mutation", ["unknown_model", "wrong_version", "unknown_label",
                                      "adapter", "preprocessing", "prediction_semantics"])
def test_registry_and_prediction_identity_mismatches_fail_closed(registered_collection, mutation):
    from safira.collection.records import PredictionRecord, SourceProvenance
    from safira.dataset.records import CorrectnessExample
    from safira.signals.records import SignalFeatureRecord, SignalRowKey, SignalSourceKey
    from safira.signals.validation import prediction_fingerprint
    from safira.training.exceptions import (TrainingCompatibilityError, TrainingInputError,
                                            TrainingVerificationError)
    from safira.training.verification import _verify_training_inputs as verify_training_inputs
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    original = dataset.development.train[0].prediction
    new_scope = original.source_key
    provenance = original.provenance
    primary = original.primary
    state_reference = None
    if mutation == "unknown_model":
        new_scope = ("unknown-model",) + new_scope[1:]
    elif mutation == "wrong_version":
        new_scope = (new_scope[0], "unknown-version", new_scope[2])
    elif mutation == "unknown_label":
        new_scope = new_scope[:2] + ("unknown-label",)
    elif mutation == "adapter":
        details = dict(provenance.details); details["adapter_id"] = "wrong-adapter"
        provenance = replace(provenance, details=details)
    elif mutation == "preprocessing":
        from safira.signals.records import FittedStateReference
        state_reference = FittedStateReference(
            "state-1", SignalSourceKey(*new_scope), "knn_distance", "v1", reference.dataset_id,
            reference.protocol_id, reference.protocol_version, reference.manifest_reference,
            "wrong-preprocessing", {"digest": "synthetic"},
        )
        manifest = replace(signals.manifest, fitted_state_references=(state_reference,))
        signals = replace(signals, manifest=manifest)
    elif mutation == "prediction_semantics":
        primary = replace(primary, meaning="different declared meaning")
    provenance = replace(provenance, source_key=new_scope)
    evidence = tuple(replace(item, source_key=new_scope) for item in original.evidence)
    forged = replace(original, model_id=new_scope[0], model_version=new_scope[1], label_id=new_scope[2],
                     provenance=provenance, primary=primary, evidence=evidence)
    old = dataset.development.train[0]
    updated = CorrectnessExample(forged, old.target_id, old.target_version, old.outcome,
                                 old.correctness_target, old.patient_group_ref, old.partition_role,
                                 old.verification_ref, old.independence_ref)
    dataset = replace(dataset, development=replace(
        dataset.development, train=(updated,) + dataset.development.train[1:]))
    digest = prediction_fingerprint(forged)
    expected_row = __import__("hashlib").sha256(
        f"{reference.dataset_id}\0{reference.manifest_reference}\0{digest}".encode()).hexdigest()
    old_feature = signals.training[0]
    source = SignalSourceKey(*new_scope)
    predictors = tuple(replace(item, source_key=source) for item in old_feature.predictors)
    updated_feature = replace(old_feature, source_key=source, predictors=predictors,
                              row_key=SignalRowKey(expected_row))
    signals = replace(signals, training=(updated_feature,) + signals.training[1:])
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)

    exact_scope = training_scope(registry, original.model_id, original.model_version, original.label_id)
    if mutation in ("unknown_model", "wrong_version", "unknown_label"):
        from safira.training.records import TrainingScope
        exact_scope = TrainingScope(*new_scope, exact_scope.classifier_artifact_sha256,
                                    exact_scope.adapter_id, exact_scope.adapter_version,
                                    exact_scope.adapter_fingerprint, exact_scope.preprocessing_identity)
    with pytest.raises((TrainingCompatibilityError, TrainingInputError, TrainingVerificationError)):
        verify_training_inputs(registry, dataset, signals, reference, ledger, scopes=(exact_scope,))
