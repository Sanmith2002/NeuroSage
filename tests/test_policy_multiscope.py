"""Synthetic multi-label policy selection stays independent by exact scope."""

from hashlib import sha256

from policy_fixtures import PolicyTestLedger, policy_dataset
from safira.calibration.records import CalibrationProtocol, CalibrationStatus
from safira.calibration.service import CalibrationService
from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.dataset.records import (CorrectnessExample, DatasetBuildResult, DatasetReadiness,
                                    PartitionedDataset)
from safira.policy import (PolicyEvidenceReference, PolicyScope, PolicySelectionProtocol,
                           PolicySelectionService, PolicyStatus)
from safira.signals import Feature003DatasetReference, SignalExtractor
from safira.signals.base import SignalDimension
from safira.signals.records import SignalMethodConfig, SignalProtocol, SignalSourceKey
from safira.training.records import (CandidateFailurePolicy, FeatureKind, FeaturePolicy, FeatureSpec,
    LogisticCandidateConfig, PreprocessingPolicy, TrainingProtocol, TrainingSupportCriteria,
    ValidationSupportCriteria)
from safira.training.service import SafetyTrainingService
from tests.training_fixtures import SyntheticTrainingLedger, training_scope
from signals_fixtures import SyntheticSignalVerifier
from test_calibration_bundle_gate import OriginLedger


def test_multilabel_scopes_return_success_beside_insufficient_scope(registered_collection):
    registry, register = registered_collection
    _, adapter = register(model_id="two-label-model", labels=("label-a", "label-b"), scores=(.4, .8))
    sources = (("two-label-model", "v1", "label-a"), ("two-label-model", "v1", "label-b"))
    prediction_ledger = SyntheticSignalVerifier()
    host = PolicyTestLedger(prediction_ledger)
    partitions = {"train": [], "validation": [], "calibration": []}

    def append_pair(role, group, index, targets):
        association = CollectionAssociation(group, f"{role}-assessment-{index}", f"{role}-occurrence-{index}")
        records = collect_live(registry, association,
            [LiveRequest(*source) for source in sources], {"synthetic-feature": [float(index)]}).records
        for source, record, correctness in zip(sources, records, targets):
            partitions[role].append(CorrectnessExample(record, "synthetic-target", "v1",
                correctness, correctness, group, role, "synthetic-ground-truth", "synthetic-independence"))

    for index in range(8):
        append_pair("train", f"original-train-{index}", index, (index % 2, index % 2))
    for index in range(4):
        append_pair("validation", f"original-validation-{index}", index, (index % 2, index % 2))
    for index in range(8):
        append_pair("calibration", f"original-calibration-{index}", index, (index % 2, index % 2))
    original = DatasetBuildResult(PartitionedDataset(*(tuple(partitions[name])
        for name in ("train", "validation", "calibration"))),
        DatasetReadiness("ready", scope="synthetic"), (), "original-manifest")
    original_ref = Feature003DatasetReference("original-multilabel", "original-protocol", "v1",
        "original-manifest", "builder-v1", sha256(b"multi-original").hexdigest())
    host.admit_dataset(original, original_ref)
    method = SignalMethodConfig("bernoulli_entropy", "v1", {"log_base": "e"})
    signal_protocol = SignalProtocol("original-protocol", "v1",
        tuple(SignalSourceKey(*source) for source in sources), {method.method_id: method}, {})
    signals = SignalExtractor(registry, signal_protocol, host, dataset_verifier=host).build_feature_set(
        original, original_ref)
    scopes = tuple(training_scope(registry, *source) for source in sources)
    adequacy = {scope.source_key: TrainingSupportCriteria(6, {0: 3, 1: 3}) for scope in scopes}
    validation_adequacy = {scope.source_key: ValidationSupportCriteria(4, {0: 1, 1: 1})
                           for scope in scopes}
    specs = {}
    for source, scope in zip(sources, scopes):
        result = next(item for row in signals.training if row.source_key.to_tuple() == source
                      for item in row.predictors if item.method_id == "bernoulli_entropy")
        feature = FeatureSpec(result.method_id, result.method_version, result.meaning,
            SignalDimension.PREDICTION_UNCERTAINTY, FeatureKind.NUMERIC,
            dict(result.method_parameters), True, False)
        specs[scope.source_key] = FeaturePolicy((feature,))
    preprocessing = {scope.source_key: PreprocessingPolicy("keep", "one_hot_seen_unseen",
        {"bernoulli_entropy": "none"}, {"bernoulli_entropy": "none"},
        {"bernoulli_entropy": "fail"}) for scope in scopes}
    training_protocol = TrainingProtocol("train-policy-inputs", "v1", scopes, adequacy,
        {scope.source_key: ("bernoulli_entropy",) for scope in scopes}, specs, preprocessing,
        {scope.source_key: LogisticCandidateConfig(True, 1.0, 1e-4, 200) for scope in scopes},
        validation_adequacy,
        {scope.source_key: CandidateFailurePolicy.ALLOW_REMAINING for scope in scopes})
    training_ledger = SyntheticTrainingLedger(prediction_ledger)
    training_ledger.admit(original, signals, original_ref)
    training_outcomes = SafetyTrainingService(registry, training_protocol, training_ledger).train(original, signals)
    estimators = {item.scope.source_key: item.artifact for item in training_outcomes
        if item.artifact is not None}
    assert set(estimators) == set(sources), [(item.status.value, item.reason_code) for item in training_outcomes]
    origin = OriginLedger(training_ledger)
    for artifact in estimators.values():
        origin.admit_artifact(artifact)
    calibration_key = lambda source: "\0".join(source)
    config = {"method_version": "logistic_recalibration_v1",
        "support_by_scope": {calibration_key(source): {"minimum_patient_groups": 4,
            "correctness_class_minimums": {"0": 1, "1": 1}} for source in sources},
        "selected_artifacts_by_scope": {calibration_key(source): {
            "artifact_version": estimators[source].artifact_version,
            "family": estimators[source].family} for source in sources},
        "logistic_settings_by_scope": {calibration_key(source): {"tol": 1e-8, "max_iter": 1000,
            "solver": "lbfgs", "penalty": None, "fit_intercept": True, "class_weight": None,
            "warm_start": False, "occurrence_weighting": "unit_per_occurrence",
            "convergence_criterion": "warning_and_iteration_limit_v1",
            "deterministic_expectation": "same_environment_repeat_v1",
            "score_identifiability_criterion": "intercept_plus_score_full_rank_v1",
            "separation_criterion": "scalar_range_ordering_v1", "slope_rule": "strictly_positive"}
            for source in sources}}
    calibration_protocol = CalibrationProtocol("calibration-protocol", "v1", scopes, config,
        required_settings=tuple(config))
    calibrators = {}
    for result in CalibrationService(registry, calibration_protocol, origin).calibrate(
            original, signals, estimators):
        if result.status is CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED:
            calibrators[result.scope.source_key] = result.artifact
            origin.admit_artifact(result.artifact)
    assert set(calibrators) == set(sources)
    host.origin = origin

    policy_rows = []
    for index in range(4):
        association = CollectionAssociation(f"policy-patient-{index}", f"policy-assessment-{index}",
                                            f"policy-occurrence-{index}")
        records = collect_live(registry, association, [LiveRequest(*sources[0])],
            {"synthetic-feature": [float(index)]}).records
        policy_rows.append(CorrectnessExample(records[0], "synthetic-target", "v1", 1, 1,
            f"policy-group-{index}", "validation", "synthetic-ground-truth", "synthetic-independence"))
    for index in range(2):
        association = CollectionAssociation(f"policy-small-patient-{index}", f"small-assessment-{index}",
                                            f"small-occurrence-{index}")
        record = collect_live(registry, association, [LiveRequest(*sources[1])],
            {"synthetic-feature": [float(index)]}).records[0]
        policy_rows.append(CorrectnessExample(record, "synthetic-target", "v1", 1, 1,
            f"policy-small-group-{index}", "validation", "synthetic-ground-truth", "synthetic-independence"))
    policy_data, policy_ref = policy_dataset(policy_rows, dataset_id="new-policy-cohort")
    host.admit_dataset(policy_data, policy_ref)
    bindings = {calibration_key(source): ("synthetic-target", "v1") for source in sources}
    protocol = PolicySelectionProtocol("policy-protocol", "v1",
        tuple(PolicyScope.from_training_scope(estimators[source].scope) for source in sources),
        PolicyEvidenceReference(policy_ref.dataset_id, policy_ref.protocol_id, policy_ref.protocol_version,
            policy_ref.manifest_reference, policy_ref.builder_version, policy_ref.manifest_digest),
        bindings, 1.0, (0.0, 1.0), 4, 1, {1: 1}, ">=", "lowest_cutoff",
        "lexicographic_assessment_ref_v1", True, "synthetic-policy-approval", True)
    host.admit_protocol(protocol)
    outcomes = PolicySelectionService(registry, protocol, host).select(
        policy_dataset=policy_data, original_training_dataset=original,
        original_signal_protocol=signal_protocol, estimator_artifacts=estimators,
        calibrator_artifacts=calibrators)
    assert len(outcomes) == 2
    by_source = {outcome.scope.source_key: outcome for outcome in outcomes}
    assert by_source[sources[0]].status is PolicyStatus.SELECTED_UNEVALUATED
    assert by_source[sources[0]].artifact is not None
    assert by_source[sources[1]].status is PolicyStatus.INSUFFICIENT_EVIDENCE
    assert by_source[sources[1]].artifact is None
