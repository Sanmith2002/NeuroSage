from tests.training_fixtures import SyntheticTrainingLedger, build_inputs

import pytest


def test_service_returns_per_scope_outcome_without_training(registered_collection):
    from hashlib import sha256
    from safira.training.records import TrainingProtocol, TrainingSupportCriteria
    from safira.training.service import SafetyTrainingService
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import training_scope

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    prediction_ledger = SyntheticSignalVerifier()
    ledger = SyntheticTrainingLedger(prediction_ledger)
    ledger.admit(dataset, signals, reference)
    scope = training_scope(registry, "training-model", "v1", "label-a")
    protocol = TrainingProtocol(
        "training-protocol", "v1", (scope,),
        {scope.source_key: TrainingSupportCriteria(2, {0: 1, 1: 1})},
        {scope.source_key: ()},
    )

    outcomes = SafetyTrainingService(registry, protocol, ledger).prepare(dataset, signals)

    example = dataset.development.train[0]
    predictor = signals.training[0]
    fingerprint = __import__("safira.signals.validation", fromlist=["prediction_fingerprint"]).prediction_fingerprint(
        example.prediction)
    expected_row_key = sha256(
        f"{signals.dataset_reference.dataset_id}\0{signals.dataset_reference.manifest_reference}\0{fingerprint}".encode()
    ).hexdigest()
    assert example.prediction.source_key == scope.source_key
    assert predictor.source_key.to_tuple() == scope.source_key
    assert predictor.row_key.value == expected_row_key
    assert len(ledger.prediction_ledger.calls) == 4
    assert len(outcomes) == 1
    assert outcomes[0].scope == scope
    assert outcomes[0].status.value == "ELIGIBLE_FOR_CANDIDATE_FITTING"
    assert outcomes[0].artifact is None


def test_missing_criteria_is_not_ready_and_low_group_support_is_insufficient(registered_collection):
    from safira.training.records import TrainingProtocol, TrainingStatus, TrainingSupportCriteria
    from safira.training.service import SafetyTrainingService
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import training_scope

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)
    ledger.verify_dataset(dataset, reference)
    scope = training_scope(registry, "training-model", "v1", "label-a")
    no_criteria = TrainingProtocol("p", "v1", (scope,), {}, {scope.source_key: ()})
    assert SafetyTrainingService(registry, no_criteria, ledger).prepare(dataset, signals)[0].status is TrainingStatus.NOT_READY

    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    small_dataset = dataset
    small_dataset = type(dataset)(
        type(dataset.development)((dataset.development.train[0],), dataset.development.validation,
                                  dataset.development.calibration),
        dataset.readiness, dataset.exclusions, dataset.manifest_reference,
    )
    small_signals = type(signals)(signals.dataset_reference, signals.training[:1], signals.validation,
                                  signals.calibration, signals.manifest, signals.cohort_support)
    ledger.admit(small_dataset, small_signals, reference)
    strict = TrainingProtocol("p", "v1", (scope,),
                              {scope.source_key: TrainingSupportCriteria(3, {})},
                              {scope.source_key: ()})
    assert SafetyTrainingService(registry, strict, ledger).prepare(small_dataset, small_signals)[0].status is TrainingStatus.INSUFFICIENT_EVIDENCE


def test_repeated_visits_count_one_patient_and_conflicting_target_group_counts_in_neither_class(registered_collection):
    from safira.training.records import TrainingProtocol, TrainingStatus, TrainingSupportCriteria
    from safira.training.service import SafetyTrainingService
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import training_scope

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(
        registry, register,
        partitions={"train": (("same-group", 1), ("same-group", 0)),
                    "validation": (("val-group", 1),), "calibration": ()},
    )
    scope = training_scope(registry, "training-model", "v1", "label-a")
    protocol = TrainingProtocol("p", "v1", (scope,),
        {scope.source_key: TrainingSupportCriteria(2, {0: 1, 1: 1})},
        {scope.source_key: ()})
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)

    outcome = SafetyTrainingService(registry, protocol, ledger).prepare(dataset, signals)[0]
    assert outcome.status is TrainingStatus.INSUFFICIENT_EVIDENCE
    assert outcome.reason_code == "patient_group_support_insufficient"


def test_same_label_from_two_models_is_never_pooled_for_adequacy(registered_collection):
    from dataclasses import replace
    from safira.dataset import DatasetBuildResult, DatasetReadiness, PartitionedDataset
    from safira.signals.records import SignalFeatureSet
    from safira.training.records import TrainingProtocol, TrainingStatus, TrainingSupportCriteria
    from safira.training.service import SafetyTrainingService
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import SyntheticTrainingLedger, build_inputs

    registry, register = registered_collection
    _, dataset_a, features_a, reference = build_inputs(registry, register, model_id="model-a")
    _, dataset_b, features_b, _ = build_inputs(
        registry, register, model_id="model-b",
        partitions={"train": (("g5", 1),), "validation": (), "calibration": ()},
    )
    dataset = DatasetBuildResult(
        PartitionedDataset(dataset_a.development.train + dataset_b.development.train,
                           dataset_a.development.validation + dataset_b.development.validation,
                           dataset_a.development.calibration + dataset_b.development.calibration),
        DatasetReadiness("ready", scope="synthetic"), (), dataset_a.manifest_reference,
    )
    manifest = replace(features_a.manifest,
                       source_keys=features_a.manifest.source_keys + features_b.manifest.source_keys)
    signals = SignalFeatureSet(reference, features_a.training + features_b.training,
                               features_a.validation + features_b.validation,
                               features_a.calibration + features_b.calibration, manifest, {})
    from tests.training_fixtures import training_scope
    scope_a = training_scope(registry, "model-a", "v1", "label-a")
    scope_b = training_scope(registry, "model-b", "v1", "label-a")
    protocol = TrainingProtocol("p", "v1", (scope_a, scope_b),
        {scope_a.source_key: TrainingSupportCriteria(2, {0: 1, 1: 1}),
         scope_b.source_key: TrainingSupportCriteria(2, {1: 1})},
        {scope_a.source_key: (), scope_b.source_key: ()})
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)
    outcomes = SafetyTrainingService(registry, protocol, ledger).prepare(dataset, signals)
    by_scope = {item.scope.source_key: item for item in outcomes}
    assert by_scope[scope_a.source_key].status is TrainingStatus.ELIGIBLE_FOR_CANDIDATE_FITTING
    assert by_scope[scope_b.source_key].status is TrainingStatus.INSUFFICIENT_EVIDENCE


def test_required_signal_state_controls_explicit_scope_outcome(registered_collection):
    from dataclasses import replace
    from safira.signals import SignalState
    from safira.training.records import TrainingProtocol, TrainingStatus, TrainingSupportCriteria
    from safira.training.service import SafetyTrainingService
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    scope = training_scope(registry, "training-model", "v1", "label-a")
    protocol = TrainingProtocol("p", "v1", (scope,),
        {scope.source_key: TrainingSupportCriteria(2, {0: 1, 1: 1})},
        {scope.source_key: ("evidence_coverage",)})
    result = signals.training[0].predictors[0]
    cases = (
        (replace(result, state=SignalState.INVALID, value=None, reason_code="evidence_invalid"), TrainingStatus.INVALID_INPUT),
        (replace(result, state=SignalState.NOT_READY, value=None, reason_code="reference_not_ready"), TrainingStatus.NOT_READY),
        (replace(result, state=SignalState.UNAVAILABLE, value=None, reason_code="evidence_unavailable"), TrainingStatus.UNAVAILABLE_REQUIRED_EVIDENCE),
    )
    for changed_result, expected in cases:
        changed_row = replace(signals.training[0], predictors=(changed_result,))
        changed_signals = replace(signals, training=(changed_row,) + signals.training[1:])
        ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
        ledger.admit(dataset, changed_signals, reference)
        outcome = SafetyTrainingService(registry, protocol, ledger).prepare(dataset, changed_signals)[0]
        assert outcome.status is expected


@pytest.mark.parametrize("missing_policy", ("feature_policies", "preprocessing_policies"))
def test_missing_mandatory_training_policy_is_not_ready_before_candidate_work(
        registered_collection, missing_policy, monkeypatch):
    from dataclasses import replace
    from safira.training.records import TrainingStatus
    from safira.training.service import SafetyTrainingService
    from test_training_acceptance import _make_service

    registry, dataset, signals, protocol, ledger, _ = _make_service(registered_collection)
    incomplete = replace(protocol, **{missing_policy: {}})
    service = SafetyTrainingService(registry, incomplete, ledger)

    def forbidden(*_args, **_kwargs):
        pytest.fail("non-ready protocol reached matrix construction or candidate work")

    import safira.training.service as service_module
    for name in ("build_feature_schema", "fit_preprocessing", "transform_rows",
                 "fit_prevalence_baseline", "fit_logistic_candidate", "compare_candidates"):
        monkeypatch.setattr(service_module, name, forbidden)

    prepared = service.prepare(dataset, signals)[0]
    trained = service.train(dataset, signals)[0]
    # `prepare` remains eligibility-only; candidate-specific policy approval is
    # enforced by `train` after the same independent source admission.
    assert prepared.status is TrainingStatus.ELIGIBLE_FOR_CANDIDATE_FITTING
    assert trained.status is TrainingStatus.NOT_READY
    assert trained.artifact is None


def test_missing_policy_isolated_to_its_exact_scope(registered_collection):
    from dataclasses import replace
    from safira.training.records import TrainingStatus
    from safira.training.service import SafetyTrainingService
    from test_training_acceptance import _make_service

    labels = ("eligible-label", "unapproved-label")
    partitions = {
        "train": (("a0", 0), ("b0", 0), ("a1", 0), ("b1", 0),
                  ("a2", 1), ("b2", 1), ("a3", 1), ("b3", 1)),
        "validation": (("av0", 0), ("bv0", 0), ("av1", 0), ("bv1", 0),
                       ("av2", 1), ("bv2", 1), ("av3", 1), ("bv3", 1)),
        "calibration": (("ca", 0), ("cb", 1)),
    }
    registry, dataset, signals, protocol, ledger, _ = _make_service(
        registered_collection, labels=labels, partitions=partitions)
    scope_by_label = {scope.label_id: scope.source_key for scope in protocol.scopes}
    ready_key = scope_by_label["eligible-label"]
    unready_key = scope_by_label["unapproved-label"]
    policies = dict(protocol.feature_policies)
    del policies[unready_key]
    protocol = replace(protocol, feature_policies=policies)

    outcomes = SafetyTrainingService(registry, protocol, ledger).train(dataset, signals)
    by_scope = {outcome.scope.source_key: outcome for outcome in outcomes}
    assert by_scope[ready_key].status in (TrainingStatus.SELECTED_BASELINE, TrainingStatus.SELECTED_LOGISTIC)
    assert by_scope[ready_key].artifact is not None
    assert by_scope[unready_key].status is TrainingStatus.NOT_READY
    assert by_scope[unready_key].artifact is None


def test_missing_training_policy_does_not_mask_unauthorized_input_mutation(registered_collection):
    from dataclasses import replace
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.records import TrainingStatus
    from safira.training.service import SafetyTrainingService
    from test_training_acceptance import _make_service

    registry, dataset, signals, protocol, ledger, _ = _make_service(registered_collection)
    incomplete = replace(protocol, feature_policies={})
    service = SafetyTrainingService(registry, incomplete, ledger)
    changed_example = replace(dataset.development.train[0],
                              correctness_target=1 - dataset.development.train[0].correctness_target)
    changed_dataset = replace(dataset, development=replace(
        dataset.development, train=(changed_example,) + dataset.development.train[1:]))

    with pytest.raises(TrainingVerificationError):
        service.train(changed_dataset, signals)

    # The original independently admitted inputs still reach the ordinary protocol result.
    assert service.train(dataset, signals)[0].status is TrainingStatus.NOT_READY


def test_malformed_supplied_preprocessing_policy_remains_invalid_input(registered_collection):
    from dataclasses import replace
    from safira.training.records import PreprocessingPolicy, TrainingStatus
    from safira.training.service import SafetyTrainingService
    from test_training_acceptance import _make_service

    registry, dataset, signals, protocol, ledger, _ = _make_service(registered_collection)
    key = protocol.scopes[0].source_key
    malformed = PreprocessingPolicy(
        constant_features="keep", category_encoding="one_hot_seen_unseen",
        numeric_imputation={}, numeric_scaling={},
    )
    protocol = replace(protocol, preprocessing_policies={key: malformed})

    outcome = SafetyTrainingService(registry, protocol, ledger).train(dataset, signals)[0]
    assert outcome.status is TrainingStatus.INVALID_INPUT
    assert outcome.artifact is None
