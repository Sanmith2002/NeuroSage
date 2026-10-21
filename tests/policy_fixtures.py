"""Synthetic Feature 007 fixtures with independently populated test ledgers."""

from __future__ import annotations

from hashlib import sha256
import json

from safira.dataset.records import (CorrectnessExample, DatasetBuildResult, DatasetReadiness,
    PartitionedDataset)
from safira.policy.records import (PolicyEvidenceReference, PolicyScope,
    PolicySelectionProtocol)
from safira.policy.verification import (PatientDisjointnessCheck, PolicyGroundTruthCheck,
    PolicyProtocolCheck)
from safira.signals.records import Feature003DatasetReference, SignalSourceKey
from safira.signals.validation import dataset_fingerprint, prediction_fingerprint


def policy_records(registry, source_key, targets=(1, 1, 1, 1), *, prefix="policy", target_id="synthetic-target"):
    from safira.collection import CollectionAssociation, LiveRequest, collect_live
    examples = []
    for index, target in enumerate(targets):
        group = f"{prefix}-group-{index}"
        association = CollectionAssociation(f"{prefix}-patient-{index}", f"{prefix}-assessment-{index}", f"{prefix}-occ-{index}")
        record = collect_live(registry, association,
            [LiveRequest(source_key[0], source_key[1], source_key[2])],
            {"synthetic-feature": [float(index + 1)]}).records[0]
        examples.append(CorrectnessExample(record, target_id, "v1", int(target), int(target),
            group, "validation", "synthetic-outcome", "synthetic-independence"))
    return tuple(examples)


def policy_dataset(rows, *, dataset_id="policy-dataset"):
    reference = Feature003DatasetReference(dataset_id, "policy-protocol", "v1",
        "manifest:" + dataset_id, "builder-v1", sha256((dataset_id + "manifest").encode()).hexdigest())
    data = DatasetBuildResult(PartitionedDataset((), tuple(rows), ()),
        DatasetReadiness("ready", scope="synthetic"), (), reference.manifest_reference)
    return data, reference


def policy_protocol(estimator, reference, *, scopes=None, target_id="synthetic-target", target_version="v1",
                    cutoffs=(0.0, 1.0), ceiling=1.0):
    scope_values = tuple(scopes or (PolicyScope.from_training_scope(estimator.scope),))
    bindings = {"\0".join(scope.source_key): (target_id, target_version) for scope in scope_values}
    return PolicySelectionProtocol("policy-selection", "v1", scope_values,
        PolicyEvidenceReference(reference.dataset_id, reference.protocol_id, reference.protocol_version,
            reference.manifest_reference, reference.builder_version, reference.manifest_digest),
        bindings, ceiling, tuple(cutoffs), 2, 1, {1: 1}, ">=", "lowest_cutoff",
        "lexicographic_assessment_ref_v1", True, "synthetic-pre-outcome-approval", True)


class PolicyTestLedger:
    """Independent synthetic authority. Not production trust infrastructure."""

    def __init__(self, prediction_ledger, artifact_origin_ledger=None):
        self.prediction_ledger = prediction_ledger
        self.origin = artifact_origin_ledger
        self.datasets = {}
        self.targets = {}
        self.groups = {}
        self.approved_protocols = set()
        self.complete_history = True
        self.protected_groups = set()

    def admit_dataset(self, dataset, reference):
        fingerprint = dataset_fingerprint(dataset)
        self.datasets[fingerprint] = (dataset, reference)
        groups = set()
        for role in ("train", "validation", "calibration"):
            for example in getattr(dataset.development, role):
                self.prediction_ledger.admit(example.prediction)
                self.targets[(fingerprint, prediction_fingerprint(example.prediction))] = (
                    example.target_id, example.target_version, example.outcome,
                    example.correctness_target, example.patient_group_ref, role,
                )
                groups.add(example.patient_group_ref)
        self.groups[reference.dataset_id] = groups

    def admit_protocol(self, protocol):
        self.approved_protocols.add(protocol.digest)

    def verify_prediction(self, record):
        return self.prediction_ledger.verify_prediction(record)

    def verify_dataset(self, dataset, reference):
        from safira.signals.records import SignalDatasetCheck
        from safira.signals.validation import _dataset_rows
        fingerprint = dataset_fingerprint(dataset)
        admitted = self.datasets.get(fingerprint)
        if admitted is None or admitted[1] != reference:
            raise ValueError("no ledger entry")
        return SignalDatasetCheck(fingerprint, reference.dataset_id, reference.protocol_id,
            reference.protocol_version, reference.manifest_reference, reference.builder_version,
            "ready", "synthetic-dataset-ledger", "exact input inventory", "dataset-entry",
            _dataset_rows(dataset), reference.manifest_digest,
            ("train", "validation", "calibration"))

    def verify_ground_truth(self, example, prediction, scope):
        from safira.policy.verification import PolicyGroundTruthCheck
        for fingerprint, (dataset, _) in self.datasets.items():
            found = self.targets.get((fingerprint, prediction_fingerprint(prediction)))
            if (found is not None and found == (example.target_id, example.target_version,
                    example.outcome, example.correctness_target, example.patient_group_ref,
                    example.partition_role)):
                return PolicyGroundTruthCheck(prediction_fingerprint(prediction), tuple(prediction.source_key),
                    example.patient_group_ref, prediction.association.assessment_ref,
                    example.target_id, example.target_version, example.outcome,
                    example.correctness_target, "verified", "synthetic-custodian-ledger",
                    "exact source-row lookup", "ground-truth-entry")
        raise ValueError("no ground-truth ledger entry")

    def verify_patient_disjointness(self, policy_reference, prior_history, protected_scope):
        policy_groups = self.groups.get(policy_reference.dataset_id)
        original = protected_scope["original_reference"]
        original_groups = self.groups.get(original["dataset_id"])
        if policy_groups is None or original_groups is None:
            raise ValueError("history unavailable")
        disjoint = not (policy_groups & (original_groups | self.protected_groups))
        return PatientDisjointnessCheck(
            dataset_fingerprint(self.datasets[next(key for key, value in self.datasets.items()
                if value[1].dataset_id == policy_reference.dataset_id)][0]),
            policy_reference.dataset_id, policy_reference.manifest_digest,
            tuple(sorted({original["dataset_id"] + ":" + original["manifest_digest"],
                *(str(item.manifest_id) + ":" + str(item.content_version) for item in prior_history)})),
            tuple(protected_scope["scope_keys"]), "synthetic-history-v1",
            "synthetic-protected-membership-v1", "v1", self.complete_history,
            True, "verified_disjoint" if disjoint and self.complete_history else "overlap",
            "synthetic-custodian-ledger", "complete synthetic group comparison", "linkage-entry")

    def verify_artifact(self, payload_digest, scope_key, artifact_version):
        if self.origin is None:
            raise ValueError("artifact origin unavailable")
        return self.origin.verify_artifact(payload_digest, scope_key, artifact_version)

    def verify_protocol(self, protocol):
        if protocol.digest not in self.approved_protocols:
            raise ValueError("protocol not approved")
        return PolicyProtocolCheck(protocol.digest, "verified", True,
            "synthetic-protocol-ledger", "exact approval record", "protocol-entry")


def make_end_to_end_case(registered_collection, *, force_logistic=False):
    """Build original F005/F006 artifacts and a distinct policy-only cohort."""
    from safira.policy.service import PolicySelectionService
    from safira.collection import CollectionAssociation, LiveRequest, collect_live
    from safira.dataset.records import CorrectnessExample, DatasetBuildResult, DatasetReadiness, PartitionedDataset
    from safira.signals import Feature003DatasetReference, SignalExtractor
    from safira.signals.records import SignalMethodConfig, SignalProtocol, SignalSourceKey
    from safira.signals.base import SignalDimension
    from safira.training.records import (CandidateFailurePolicy, FeatureKind, FeaturePolicy,
        FeatureSpec, LogisticCandidateConfig, PreprocessingPolicy, TrainingProtocol,
        TrainingSupportCriteria, ValidationSupportCriteria)
    from safira.training.service import SafetyTrainingService
    from tests.training_fixtures import SyntheticTrainingLedger, training_scope
    from signals_fixtures import SyntheticSignalVerifier
    from test_calibration_bundle_gate import OriginLedger

    registry, register = registered_collection
    _, adapter = register(model_id="policy-model", version="v1", labels=("label-a",), scores=(.7,))
    source = ("policy-model", "v1", "label-a")
    prediction_ledger = SyntheticSignalVerifier()
    host = PolicyTestLedger(prediction_ledger)
    row_spec = ({
        "train": ((.05, 0, 0), (.1, 0, 0), (.15, 0, 0), (.2, 0, 0),
                  (.3, 1, 1), (.35, 1, 1), (.4, 1, 1), (.45, 1, 1)),
        "validation": ((.05, 0, 0), (.15, 0, 0), (.35, 1, 1), (.45, 1, 1)),
        "calibration": ((.05, 0, 0), (.1, 0, 0), (.15, 1, 1), (.2, 0, 0),
                        (.3, 0, 0), (.35, 1, 1), (.4, 1, 1), (.45, 1, 1)),
    } if force_logistic else {
        "train": ((.1, 0, 1), (.9, 1, 1), (.6, 1, 1), (.95, 0, 0),
                  (.4, 1, 0), (.8, 0, 0), (.2, 0, 1), (.3, 1, 0)),
        "validation": ((.1, 0, 1), (.95, 0, 0), (.7, 1, 1), (.3, 1, 0)),
        "calibration": ((.1, 0, 1), (.2, 0, 1), (.95, 0, 0), (.3, 1, 0), (.8, 0, 0), (.9, 1, 1)),
    })
    examples = {role: [] for role in row_spec}
    for role, values in row_spec.items():
        for index, (score, outcome, correctness) in enumerate(values):
            adapter.classifier.scores["label-a"] = score
            group = f"original-{role}-{index}"
            association = CollectionAssociation(f"patient-{group}", f"assessment-{group}", f"occ-{group}")
            prediction = collect_live(registry, association, [LiveRequest(*source)],
                                      {"synthetic-feature": [float(index + 1)]}).records[0]
            examples[role].append(CorrectnessExample(prediction, "synthetic-target", "v1",
                outcome, correctness, group, role, "synthetic-ground-truth", "synthetic-lineage"))
    original = DatasetBuildResult(PartitionedDataset(*(tuple(examples[role]) for role in
        ("train", "validation", "calibration"))), DatasetReadiness("ready", scope="synthetic"),
        (), "original-manifest")
    original_ref = Feature003DatasetReference("original-data", "original-protocol", "v1",
        original.manifest_reference, "builder-v1", sha256(b"original-manifest").hexdigest())
    host.admit_dataset(original, original_ref)
    method = SignalMethodConfig("bernoulli_entropy", "v1", {"log_base": "e"})
    signal_protocol = SignalProtocol(original_ref.protocol_id, original_ref.protocol_version,
        (SignalSourceKey(*source),), {method.method_id: method}, {})
    original_signals = SignalExtractor(registry, signal_protocol, host,
        dataset_verifier=host).build_feature_set(original, original_ref)
    scope = training_scope(registry, *source)
    adequacy = {scope.source_key: TrainingSupportCriteria(6, {0: 3, 1: 3})}
    validation_adequacy = {scope.source_key: ValidationSupportCriteria(4, {0: 1, 1: 1})}
    feature = FeatureSpec("bernoulli_entropy", "v1", "Bernoulli predictive entropy in nats; not correctness or reliability.",
        SignalDimension.PREDICTION_UNCERTAINTY, FeatureKind.NUMERIC, {"log_base": "e"}, True, False)
    training_protocol = TrainingProtocol("training-protocol", "v1", (scope,), adequacy,
        {scope.source_key: ("bernoulli_entropy",)},
        {scope.source_key: FeaturePolicy((feature,))},
        {scope.source_key: PreprocessingPolicy("keep", "one_hot_seen_unseen",
            {"bernoulli_entropy": "none"}, {"bernoulli_entropy": "none"},
            {"bernoulli_entropy": "fail"})},
        {scope.source_key: LogisticCandidateConfig(True, 1.0, 1e-4, 200)}, validation_adequacy,
        {scope.source_key: CandidateFailurePolicy.ALLOW_REMAINING})
    training_ledger = SyntheticTrainingLedger(prediction_ledger)
    training_ledger.admit(original, original_signals, original_ref)
    training_service = SafetyTrainingService(registry, training_protocol, training_ledger)
    estimator_map = {item.scope.source_key: item.artifact for item in training_service.train(original, original_signals)
                     if item.artifact is not None}
    if len(estimator_map) != 1:
        raise AssertionError(f"synthetic estimator artifact unavailable: {[(item.status.value, item.reason_code) for item in training_service.train(original, original_signals)]}")
    origin = OriginLedger(training_ledger)
    for artifact in estimator_map.values():
        origin.admit_artifact(artifact)
    estimator = next(iter(estimator_map.values()))
    key = "\0".join(source)
    config = {"method_version": "logistic_recalibration_v1",
        "support_by_scope": {key: {"minimum_patient_groups": 4, "correctness_class_minimums": {"0": 1, "1": 1}}},
        "selected_artifacts_by_scope": {key: {"artifact_version": estimator.artifact_version, "family": estimator.family}},
        "logistic_settings_by_scope": {key: {"tol": 1e-8, "max_iter": 1000, "solver": "lbfgs",
            "penalty": None, "fit_intercept": True, "class_weight": None, "warm_start": False,
            "occurrence_weighting": "unit_per_occurrence", "convergence_criterion": "warning_and_iteration_limit_v1",
            "deterministic_expectation": "same_environment_repeat_v1",
            "score_identifiability_criterion": "intercept_plus_score_full_rank_v1",
            "separation_criterion": "scalar_range_ordering_v1", "slope_rule": "strictly_positive"}}}
    from safira.calibration.records import CalibrationProtocol
    calibration_protocol = CalibrationProtocol("calibration-protocol", "v1", (scope,), config,
        required_settings=tuple(config))
    from safira.calibration.service import CalibrationService
    calibrator_service = CalibrationService(registry, calibration_protocol, origin)
    calibrator_map = {}
    calibration_outcomes = calibrator_service.calibrate(original, original_signals, estimator_map)
    for outcome in calibration_outcomes:
        if outcome.artifact is not None:
            calibrator_map[outcome.scope.source_key] = outcome.artifact
            origin.admit_artifact(outcome.artifact)
    if len(calibrator_map) != 1:
        raise AssertionError(f"synthetic calibrator unavailable: {[(item.status.value, item.reason_code) for item in calibration_outcomes]}")
    host.origin = origin

    policy_examples = []
    for index in range(4):
        adapter.classifier.scores["label-a"] = (.75 + index * .03)
        group = f"policy-group-{index}"
        association = CollectionAssociation(f"policy-patient-{index}", f"policy-assessment-{index}", f"policy-occ-{index}")
        prediction = collect_live(registry, association, [LiveRequest(*source)],
                                  {"synthetic-feature": [float(index + 1)]}).records[0]
        policy_examples.append(CorrectnessExample(prediction, "synthetic-target", "v1", 1, 1,
            group, "validation", "synthetic-ground-truth", "synthetic-lineage"))
    policy_data, policy_ref = policy_dataset(policy_examples)
    host.admit_dataset(policy_data, policy_ref)
    protocol = policy_protocol(estimator, policy_ref, target_id="synthetic-target")
    host.admit_protocol(protocol)
    service = PolicySelectionService(registry, protocol, host)
    return service, host, protocol, policy_data, original, signal_protocol, estimator_map, calibrator_map
