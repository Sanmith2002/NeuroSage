from dataclasses import replace

import pytest


def _make_service(registered_collection, *, labels=("label-a",), validation=(("v1", 1), ("v2", 0), ("v3", 1), ("v4", 0)),
                 validation_values=None, train_values=None, model_id="training-model", partitions=None):
    from safira.signals import SignalFeatureSet, SignalResult
    from safira.training.records import (
        CandidateFailurePolicy, FeatureKind, FeaturePolicy, FeatureSpec, LogisticCandidateConfig, PreprocessingPolicy,
        TrainingProtocol, TrainingSupportCriteria, ValidationSupportCriteria,
    )
    from safira.training.service import SafetyTrainingService
    from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    if partitions is None:
        partitions = {"train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
                      "validation": validation, "calibration": (("c1", 0),)}
    _, dataset, signals, reference = build_inputs(registry, register, model_id=model_id,
                                                  labels=labels, partitions=partitions)
    def numeric(rows, examples, overrides=None):
        values = overrides if overrides is not None else tuple(float(row.correctness_target) for row in examples)
        return tuple(replace(row, predictors=(replace(row.predictors[0], value=values[index]),))
                     for index, row in enumerate(rows))
    signals = replace(signals,
        training=numeric(signals.training, dataset.development.train, train_values),
        validation=numeric(signals.validation, dataset.development.validation, validation_values),
        calibration=numeric(signals.calibration, dataset.development.calibration))
    scopes = tuple(training_scope(registry, model_id, "v1", label) for label in labels)
    adequacy = {scope.source_key: TrainingSupportCriteria(4, {0: 2, 1: 2}) for scope in scopes}
    validation_adequacy = {scope.source_key: ValidationSupportCriteria(4, {0: 1, 1: 1}) for scope in scopes}
    policies = {scope.source_key: FeaturePolicy((FeatureSpec(
        "evidence_coverage", "v1", "synthetic evidence profile", signals.training[0].predictors[0].dimension,
        FeatureKind.NUMERIC, {"required_evidence": []}, required=True, state_indicators=False),)) for scope in scopes}
    preprocess = {scope.source_key: PreprocessingPolicy("keep", "one_hot_seen_unseen",
        {"evidence_coverage": "none"}, {"evidence_coverage": "none"}) for scope in scopes}
    configs = {scope.source_key: LogisticCandidateConfig(True, 1.0, 1e-4, 200) for scope in scopes}
    failure = {scope.source_key: CandidateFailurePolicy.ALLOW_REMAINING for scope in scopes}
    protocol = TrainingProtocol("training-protocol", "v1", scopes, adequacy,
        {scope.source_key: ("evidence_coverage",) for scope in scopes}, policies, preprocess, configs,
        validation_adequacy, failure)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)
    return registry, dataset, signals, protocol, ledger, SafetyTrainingService(registry, protocol, ledger)


def _make_multi_model_service(registered_collection):
    from dataclasses import replace
    from safira.dataset import DatasetBuildResult, PartitionedDataset
    from safira.signals import SignalFeatureSet
    from safira.training.records import (
        CandidateFailurePolicy, FeatureKind, FeaturePolicy, FeatureSpec, LogisticCandidateConfig,
        PreprocessingPolicy, TrainingProtocol, TrainingSupportCriteria, ValidationSupportCriteria,
    )
    from safira.training.service import SafetyTrainingService
    from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    all_data, all_sets, scopes = [], [], []
    for model_id in ("independent-a", "independent-b"):
        _, dataset, signals, _ = build_inputs(
            registry, register, model_id=model_id, labels=("shared-label",),
            partitions={"train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
                        "validation": (("v1", 1), ("v2", 0), ("v3", 1), ("v4", 0)),
                        "calibration": (("c1", 0),)},
        )
        def numeric(role_rows, examples):
            return tuple(replace(row, predictors=(replace(row.predictors[0],
                value=float(examples[index].correctness_target)),)) for index, row in enumerate(role_rows))
        signals = replace(signals, training=numeric(signals.training, dataset.development.train),
                          validation=numeric(signals.validation, dataset.development.validation),
                          calibration=numeric(signals.calibration, dataset.development.calibration))
        all_data.append(dataset)
        all_sets.append(signals)
        scopes.append(training_scope(registry, model_id, "v1", "shared-label"))
    first, second = all_data
    dataset = DatasetBuildResult(
        PartitionedDataset(first.development.train + second.development.train,
                           first.development.validation + second.development.validation,
                           first.development.calibration + second.development.calibration),
        first.readiness, first.exclusions, first.manifest_reference,
    )
    s1, s2 = all_sets
    manifest = replace(s1.manifest, source_keys=s1.manifest.source_keys + s2.manifest.source_keys)
    signals = SignalFeatureSet(s1.dataset_reference, s1.training + s2.training,
        s1.validation + s2.validation, s1.calibration + s2.calibration, manifest, {})
    adequacy = {scope.source_key: TrainingSupportCriteria(4, {0: 2, 1: 2}) for scope in scopes}
    val = {scope.source_key: ValidationSupportCriteria(4, {0: 1, 1: 1}) for scope in scopes}
    feature = {scope.source_key: FeaturePolicy((FeatureSpec(
        "evidence_coverage", "v1", "synthetic evidence profile", signals.training[0].predictors[0].dimension,
        FeatureKind.NUMERIC, {"required_evidence": []}, required=True, state_indicators=False),)) for scope in scopes}
    prep = {scope.source_key: PreprocessingPolicy("keep", "one_hot_seen_unseen",
        {"evidence_coverage": "none"}, {"evidence_coverage": "none"}) for scope in scopes}
    configs = {scope.source_key: LogisticCandidateConfig(True, 1.0, 1e-4, 200) for scope in scopes}
    failures = {scope.source_key: CandidateFailurePolicy.ALLOW_REMAINING for scope in scopes}
    protocol = TrainingProtocol("multi-source-protocol", "v1", tuple(scopes), adequacy,
        {scope.source_key: ("evidence_coverage",) for scope in scopes}, feature, prep, configs, val, failures)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, s1.dataset_reference)
    return dataset, signals, protocol, SafetyTrainingService(registry, protocol, ledger)


def test_public_training_service_trains_per_scope_and_emits_private_uncalibrated_artifact(registered_collection):
    from safira.training.records import TrainingStatus
    _, dataset, signals, _, _, service = _make_service(registered_collection)
    outcomes = service.train(dataset, signals)
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status in (TrainingStatus.SELECTED_BASELINE, TrainingStatus.SELECTED_LOGISTIC)
    assert outcome.artifact is not None
    assert outcome.artifact.lifecycle == "uncalibrated_non_deployable"
    payload = outcome.to_dict()
    assert "artifact" in payload and "patient_group_ref" not in str(payload)
    assert outcome.artifact.selection_metrics["role"] == "selection_evidence"


def test_public_training_rejects_forged_input_before_candidate_fitting(registered_collection):
    from dataclasses import replace
    from safira.training.exceptions import TrainingVerificationError
    _, dataset, signals, _, _, service = _make_service(registered_collection)
    changed = replace(dataset, readiness=replace(dataset.readiness, scope="altered"))
    with pytest.raises(TrainingVerificationError):
        service.train(changed, signals)


@pytest.mark.parametrize("values", [(0.0, 1.0, 0.0, 1.0), (.5, .5, .5, .5)])
def test_validation_can_select_baseline_and_exact_tie_prefers_baseline(registered_collection, values):
    from safira.training.records import TrainingStatus
    _, dataset, signals, _, _, service = _make_service(
        registered_collection, validation_values=values)
    outcome = service.train(dataset, signals)[0]
    assert outcome.status is TrainingStatus.SELECTED_BASELINE
    assert outcome.artifact.family == "prevalence_baseline"


def test_baseline_artifact_is_training_prevalence_constant_not_runtime_inference(registered_collection):
    _, dataset, signals, _, _, service = _make_service(
        registered_collection, validation_values=(0.0, 1.0, 0.0, 1.0))
    outcome = service.train(dataset, signals)[0]
    assert outcome.artifact.family == "prevalence_baseline"
    assert outcome.artifact.estimator_state["probability"] == .5
    assert not hasattr(outcome.artifact, "predict")
    assert outcome.artifact.calibrated is False and outcome.artifact.deployable is False


def test_aggregate_selection_support_is_serialized_only_when_protocol_allows_disclosure(registered_collection):
    from dataclasses import replace
    from safira.training.records import ValidationSupportCriteria
    from safira.training.service import SafetyTrainingService
    _, dataset, signals, protocol, ledger, _ = _make_service(registered_collection)
    key = protocol.scopes[0].source_key
    protocol = replace(protocol, validation_adequacy={key: ValidationSupportCriteria(4, {0: 1, 1: 1}, True)})
    outcome = SafetyTrainingService(registered_collection[0], protocol, ledger).train(dataset, signals)[0]
    support = outcome.artifact.selection_metrics["disclosed_support"]
    assert support == {"patient_group_count": 4, "correctness_class_support": {"0": 2, "1": 2}}
    serialized = str(outcome.to_dict())
    assert all(f"'{group}'" not in serialized for group in ("t1", "t2", "t3", "t4"))


def test_multilabel_scopes_train_independently_and_insufficient_label_does_not_block_other(registered_collection):
    from safira.training.records import TrainingStatus
    labels = ("label-a", "label-b")
    partitions = {
        "train": (("a0", 0), ("b0", 0), ("a1", 0), ("b1", 0),
                  ("a2", 1), ("b2", 0), ("a3", 1), ("b3", 0)),
        "validation": (("av0", 1), ("bv0", 0), ("av1", 0), ("bv1", 0),
                       ("av2", 1), ("bv2", 0), ("av3", 0), ("bv3", 0)),
        "calibration": (("ca", 0), ("cb", 0)),
    }
    _, dataset, signals, _, _, service = _make_service(
        registered_collection, labels=labels, partitions=partitions)
    outcomes = {item.scope.label_id: item for item in service.train(dataset, signals)}
    assert outcomes["label-a"].status in (TrainingStatus.SELECTED_BASELINE, TrainingStatus.SELECTED_LOGISTIC)
    assert outcomes["label-b"].status is TrainingStatus.INSUFFICIENT_EVIDENCE
    assert outcomes["label-b"].artifact is None


def test_independent_contributors_with_overlapping_label_names_remain_separate(registered_collection):
    from safira.training.records import TrainingStatus
    dataset, signals, protocol, service = _make_multi_model_service(registered_collection)
    outcomes = service.train(dataset, signals)
    assert len(outcomes) == 2
    assert len({item.scope.source_key for item in outcomes}) == 2
    assert {item.scope.label_id for item in outcomes} == {"shared-label"}
    assert all(item.status in (TrainingStatus.SELECTED_BASELINE, TrainingStatus.SELECTED_LOGISTIC)
               for item in outcomes)
    assert all(item.artifact.scope.model_id == item.scope.model_id for item in outcomes)


def test_single_class_training_is_descriptive_only_and_never_yields_artifact(registered_collection):
    from dataclasses import replace
    from safira.training.records import TrainingStatus, TrainingSupportCriteria
    _, dataset, signals, protocol, ledger, _ = _make_service(
        registered_collection,
        partitions={"train": (("t1", 0), ("t2", 0), ("t3", 0), ("t4", 0)),
                    "validation": (("v1", 1), ("v2", 0), ("v3", 1), ("v4", 0)),
                    "calibration": (("c1", 0),)},
    )
    scope = protocol.scopes[0]
    protocol = replace(protocol, adequacy={scope.source_key: TrainingSupportCriteria(4, {0: 2})})
    from safira.training.service import SafetyTrainingService
    result = SafetyTrainingService(registered_collection[0], protocol, ledger).train(dataset, signals)[0]
    assert result.status is TrainingStatus.INSUFFICIENT_EVIDENCE
    assert result.artifact is None


def test_identical_authorized_inputs_repeat_identical_artifact_digest(registered_collection):
    _, dataset, signals, _, _, service = _make_service(registered_collection)
    first = service.train(dataset, signals)[0]
    second = service.train(dataset, signals)[0]
    assert first.artifact.digest == second.artifact.digest
    assert first.artifact.to_dict() == second.artifact.to_dict()


def test_validation_changes_do_not_refit_training_estimator_or_preprocessing(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import SyntheticTrainingLedger
    from safira.training.service import SafetyTrainingService

    registry, dataset, signals, protocol, _, service = _make_service(registered_collection)
    first = service.train(dataset, signals)[0].artifact
    changed_rows = tuple(replace(row, predictors=(replace(row.predictors[0],
        value=.9 if example.correctness_target else .1),))
        for row, example in zip(signals.validation, dataset.development.validation))
    changed_signals = replace(signals, validation=changed_rows)
    independent_ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    independent_ledger.admit(dataset, changed_signals, changed_signals.dataset_reference)
    changed_service = SafetyTrainingService(registry, protocol, independent_ledger)
    second = changed_service.train(dataset, changed_signals)[0].artifact
    assert first.family == second.family == "l2_logistic"
    assert first.estimator_state == second.estimator_state
    assert first.preprocessing == second.preprocessing

