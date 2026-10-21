from dataclasses import replace

import pytest

from safira.calibration.records import CalibrationProtocol, CalibrationStatus
from safira.calibration.verification import _verify_bundle
from safira.signals.records import SignalProtocol
from test_training_acceptance import _make_service
from training_fixtures import training_scope


class OriginLedger:
    def __init__(self, training_ledger):
        self.training_ledger = training_ledger
        self.artifacts = set()

    def verify_dataset(self, dataset, reference):
        return self.training_ledger.verify_dataset(dataset, reference)

    def verify_prediction(self, record):
        return self.training_ledger.verify_prediction(record)

    def admit_artifact(self, artifact):
        self.artifacts.add((artifact.digest, artifact.scope.source_key, artifact.artifact_version))

    def verify_artifact(self, digest, scope, version):
        from safira.training.artifacts import ArtifactOriginCheck
        if (digest, tuple(scope), version) not in self.artifacts:
            raise ValueError("not in independent artifact ledger")
        return ArtifactOriginCheck(digest, tuple(scope), version, "synthetic-origin-ledger",
                                   "exact lookup", "artifact-entry")


def setup(registered_collection):
    partitions = {"train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
                  "validation": (("v1", 0), ("v2", 1), ("v3", 0), ("v4", 1)),
                  "calibration": (("c1", 0), ("c2", 1))}
    registry, dataset, signals, _, training_ledger, service = _make_service(
        registered_collection, partitions=partitions)
    artifact = service.train(dataset, signals)[0].artifact
    origin = OriginLedger(training_ledger)
    origin.admit_artifact(artifact)
    scope = training_scope(registry, artifact.scope.model_id, artifact.scope.model_version,
                           artifact.scope.label_id)
    protocol = CalibrationProtocol("calibration", "v1", (scope,),
        {"method_version": "logistic_recalibration_v1", "support_by_scope": {
            "\0".join(scope.source_key): {"minimum_patient_groups": 1,
                                          "correctness_class_minimums": {}}},
         "selected_artifacts_by_scope": {"\0".join(scope.source_key): {
             "artifact_version": artifact.artifact_version, "family": artifact.family}}},
        required_settings=("method_version", "support_by_scope", "selected_artifacts_by_scope"))
    return registry, dataset, signals, artifact, scope, protocol, origin


def test_complete_bundle_runs_all_independent_gates_before_readiness(registered_collection):
    registry, dataset, signals, artifact, scope, protocol, verifier = setup(registered_collection)
    token = _verify_bundle(registry, dataset, signals, {scope.source_key: artifact}, protocol, verifier)
    assert token is not None
    assert token.readiness[scope.source_key].status is None


def test_shared_admission_failure_is_atomic_and_publishes_no_scope_readiness(registered_collection):
    registry, dataset, signals, artifact, scope, protocol, verifier = setup(registered_collection)
    changed = replace(dataset, manifest_reference="other-manifest")
    with pytest.raises(Exception):
        _verify_bundle(registry, changed, signals, {scope.source_key: artifact}, protocol, verifier)

    with pytest.raises(Exception):
        _verify_bundle(registry, dataset, signals, {}, protocol, verifier)


def test_independently_eligible_scope_keeps_readiness_when_another_is_insufficient(registered_collection):
    registry, dataset, signals, artifact, scope, protocol, verifier = setup(registered_collection)
    # This verifies scope-local criteria do not mutate the shared verified input token.
    strict = CalibrationProtocol("calibration", "v1", (scope,),
        {"method_version": "logistic_recalibration_v1", "support_by_scope": {
            "\0".join(scope.source_key): {"minimum_patient_groups": 9,
                                          "correctness_class_minimums": {}}},
         "selected_artifacts_by_scope": {"\0".join(scope.source_key): {
             "artifact_version": artifact.artifact_version, "family": artifact.family}}},
        required_settings=("method_version", "support_by_scope", "selected_artifacts_by_scope"))
    token = _verify_bundle(registry, dataset, signals, {scope.source_key: artifact}, strict, verifier)
    assert token.readiness[scope.source_key].status is CalibrationStatus.INSUFFICIENT_EVIDENCE


def test_complete_bundle_accepts_multilabel_and_independent_overlapping_contributors(registered_collection):
    from test_training_acceptance import _make_multi_model_service, _make_service

    registry, register = registered_collection
    partitions = {
        "train": (("t1", 0), ("t2", 0), ("t3", 0), ("t4", 0),
                  ("t5", 1), ("t6", 1), ("t7", 1), ("t8", 1)),
        "validation": (("v1", 0), ("v2", 0), ("v3", 1), ("v4", 1),
                       ("v5", 0), ("v6", 0), ("v7", 1), ("v8", 1)),
        "calibration": (("c1", 0), ("c2", 0), ("c3", 1), ("c4", 1)),
    }
    _, dataset, signals, _, _, service = _make_service(
        registered_collection, labels=("label-a", "label-b"), partitions=partitions,
    )
    outcomes = service.train(dataset, signals)
    artifacts = {item.scope.source_key: item.artifact for item in outcomes if item.artifact is not None}
    assert len(artifacts) == 2
    training_ledger = service._verifier
    origin = OriginLedger(training_ledger)
    for artifact in artifacts.values():
        origin.admit_artifact(artifact)
    scopes = tuple(item.scope for item in outcomes)
    config = {"method_version": "logistic_recalibration_v1", "support_by_scope": {
        "\0".join(scope.source_key): {"minimum_patient_groups": 3 if scope.label_id == "label-b" else 1,
                                       "correctness_class_minimums": {}}
        for scope in scopes}, "selected_artifacts_by_scope": {
            "\0".join(scope.source_key): {"artifact_version": artifacts[scope.source_key].artifact_version,
                                           "family": artifacts[scope.source_key].family}
            for scope in scopes}}
    protocol = CalibrationProtocol("calibration", "v1", scopes, config,
                                   required_settings=("method_version", "support_by_scope",
                                                      "selected_artifacts_by_scope"))
    token = _verify_bundle(registry, dataset, signals, artifacts, protocol, origin)
    assert set(token.readiness) == set(artifacts)
    assert token.readiness[("training-model", "v1", "label-a")].status is None
    assert token.readiness[("training-model", "v1", "label-b")].status is CalibrationStatus.INSUFFICIENT_EVIDENCE

    registry, register = registered_collection
    dataset, signals, training_protocol, service = _make_multi_model_service(registered_collection)
    outcomes = service.train(dataset, signals)
    artifacts = {item.scope.source_key: item.artifact for item in outcomes if item.artifact is not None}
    assert len(artifacts) == 2
    origin = OriginLedger(service._verifier)
    for artifact in artifacts.values():
        origin.admit_artifact(artifact)
    scopes = tuple(item.scope for item in outcomes)
    protocol = CalibrationProtocol("calibration", "v1", scopes,
        {"method_version": "logistic_recalibration_v1", "support_by_scope": {
            "\0".join(scope.source_key): {"minimum_patient_groups": 1,
                                           "correctness_class_minimums": {}}
            for scope in scopes}, "selected_artifacts_by_scope": {
                "\0".join(scope.source_key): {"artifact_version": artifacts[scope.source_key].artifact_version,
                                               "family": artifacts[scope.source_key].family}
                for scope in scopes}}, required_settings=("method_version", "support_by_scope",
                                                           "selected_artifacts_by_scope"))
    token = _verify_bundle(registry, dataset, signals, artifacts, protocol, origin)
    assert len(token.readiness) == 2
    assert len({key[0] for key in token.readiness}) == 2


def test_unavailable_scope_does_not_block_an_independently_ready_scope(registered_collection):
    from dataclasses import replace
    from safira.dataset import DatasetBuildResult
    from safira.signals import SignalFeatureSet
    from safira.signals.base import SignalState
    from safira.training.service import SafetyTrainingService
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import SyntheticTrainingLedger
    from test_training_acceptance import _make_service

    registry, register = registered_collection
    partitions = {
        "train": (("t1", 0), ("t2", 0), ("t3", 0), ("t4", 0),
                  ("t5", 1), ("t6", 1), ("t7", 1), ("t8", 1)),
        "validation": (("v1", 0), ("v2", 0), ("v3", 1), ("v4", 1),
                       ("v5", 0), ("v6", 0), ("v7", 1), ("v8", 1)),
        "calibration": (("c1", 0), ("c2", 0), ("c3", 1), ("c4", 1)),
    }
    _, dataset, signals, feature005_protocol, _, _ = _make_service(
        registered_collection, labels=("label-a", "label-b"), partitions=partitions,
    )
    calibration_rows = []
    for row in signals.calibration:
        if row.source_key.label_id == "label-b":
            predictor = replace(row.predictors[0], state=SignalState.UNAVAILABLE,
                                value=None, reason_code="evidence_unavailable")
            row = replace(row, predictors=(predictor,))
        calibration_rows.append(row)
    signals = replace(signals, calibration=tuple(calibration_rows))
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, signals.dataset_reference)
    service = SafetyTrainingService(registry, feature005_protocol, ledger)
    training_outcomes = service.train(dataset, signals)
    artifacts = {item.scope.source_key: item.artifact for item in training_outcomes
                 if item.artifact is not None}
    assert len(artifacts) == 2
    origin = OriginLedger(ledger)
    for artifact in artifacts.values():
        origin.admit_artifact(artifact)
    scopes = tuple(item.scope for item in training_outcomes)
    protocol = CalibrationProtocol("calibration", "v1", scopes,
        {"method_version": "logistic_recalibration_v1", "support_by_scope": {
            "\0".join(scope.source_key): {"minimum_patient_groups": 1,
                                           "correctness_class_minimums": {}}
            for scope in scopes}, "selected_artifacts_by_scope": {
                "\0".join(scope.source_key): {"artifact_version": artifacts[scope.source_key].artifact_version,
                                               "family": artifacts[scope.source_key].family}
                for scope in scopes}}, required_settings=("method_version", "support_by_scope",
                                                           "selected_artifacts_by_scope"))
    token = _verify_bundle(registry, dataset, signals, artifacts, protocol, origin)
    assert token.readiness[("training-model", "v1", "label-a")].status is None
    assert token.readiness[("training-model", "v1", "label-b")].status is CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE
