from dataclasses import replace

from safira.calibration.records import CalibrationProtocol, CalibrationStatus
from safira.calibration.verification import _evaluate_scope_readiness
from test_training_acceptance import _make_service
from tests.training_fixtures import training_scope


def _protocol(scope, artifact, minimum_groups=1, class_minimums=None, required_settings=True):
    key = "\0".join(scope.source_key)
    config = {"support_by_scope": {key: {
        "minimum_patient_groups": minimum_groups,
        "correctness_class_minimums": {str(k): v for k, v in (class_minimums or {}).items()},
    }}, "method_version": "logistic_recalibration_v1",
        "selected_artifacts_by_scope": {key: {"artifact_version": artifact.artifact_version,
                                               "family": artifact.family}}}
    required = ("support_by_scope", "method_version", "selected_artifacts_by_scope") if required_settings else (
        "support_by_scope", "method_version", "selected_artifacts_by_scope", "missing_approval")
    return CalibrationProtocol("calibration", "v1", (scope,), config, required_settings=required)


def _setup(registered_collection):
    partitions = {"train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
                  "validation": (("v1", 0), ("v2", 1), ("v3", 0), ("v4", 1)),
                  "calibration": (("c1", 0), ("c2", 1))}
    registry, dataset, signals, _, ledger, service = _make_service(
        registered_collection, partitions=partitions)
    artifact = service.train(dataset, signals)[0].artifact
    scope = training_scope(registry, artifact.scope.model_id, artifact.scope.model_version,
                           artifact.scope.label_id)
    return dataset, signals, artifact, scope


def test_scope_readiness_uses_exact_patient_group_and_class_criteria(registered_collection):
    dataset, signals, artifact, scope = _setup(registered_collection)
    result = _evaluate_scope_readiness(dataset, signals, artifact, scope,
                                       _protocol(scope, artifact, minimum_groups=3))
    assert result.status is CalibrationStatus.INSUFFICIENT_EVIDENCE
    assert result.reason_code == "support_insufficient"


def test_missing_protocol_approval_is_not_ready_not_insufficient(registered_collection):
    dataset, signals, artifact, scope = _setup(registered_collection)
    protocol = _protocol(scope, artifact, required_settings=False)
    result = _evaluate_scope_readiness(dataset, signals, artifact, scope, protocol)
    assert result.status is CalibrationStatus.NOT_READY


def test_unapproved_or_mismatched_selected_artifact_is_not_eligible(registered_collection):
    dataset, signals, artifact, scope = _setup(registered_collection)
    approved = _protocol(scope, artifact)
    changed = dict(approved.configuration)
    key = "\0".join(scope.source_key)
    changed["selected_artifacts_by_scope"] = {key: {
        "artifact_version": "stale-version", "family": artifact.family}}
    mismatch = CalibrationProtocol("calibration", "v1", (scope,), changed,
        required_settings=("support_by_scope", "method_version", "selected_artifacts_by_scope"))
    assert _evaluate_scope_readiness(dataset, signals, artifact, scope, mismatch).status is CalibrationStatus.INCOMPATIBLE_INPUT


def test_required_class_support_is_checked_per_exact_scope(registered_collection):
    dataset, signals, artifact, scope = _setup(registered_collection)
    result = _evaluate_scope_readiness(
        dataset, signals, artifact, scope, _protocol(scope, artifact, class_minimums={0: 1, 1: 2}),
    )
    assert result.status is CalibrationStatus.INSUFFICIENT_EVIDENCE


def test_exactly_supported_scope_is_ready_without_publishing_a_fit(registered_collection):
    dataset, signals, artifact, scope = _setup(registered_collection)
    # Two independent synthetic groups provide both correctness classes.
    protocol = CalibrationProtocol("calibration", "v1", (scope,),
        {"support_by_scope": {"\0".join(scope.source_key): {
            "minimum_patient_groups": 1, "correctness_class_minimums": {}}},
         "method_version": "logistic_recalibration_v1",
         "selected_artifacts_by_scope": {"\0".join(scope.source_key): {
             "artifact_version": artifact.artifact_version, "family": artifact.family}}},
        required_settings=("support_by_scope", "method_version", "selected_artifacts_by_scope"))
    result = _evaluate_scope_readiness(dataset, signals, artifact, scope, protocol)
    assert result.status is None
    assert not hasattr(result, "artifact")


def test_unavailable_required_signal_is_distinct_from_missing_approval(registered_collection):
    dataset, signals, artifact, scope = _setup(registered_collection)
    from safira.signals.base import SignalState
    changed_rows = []
    for row in signals.calibration:
        predictor = replace(row.predictors[0], state=SignalState.UNAVAILABLE, value=None,
                            reason_code="evidence_unavailable")
        changed_rows.append(replace(row, predictors=(predictor,)))
    changed_signals = replace(signals, calibration=tuple(changed_rows))
    protocol = CalibrationProtocol("calibration", "v1", (scope,),
        {"support_by_scope": {"\0".join(scope.source_key): {
            "minimum_patient_groups": 1, "correctness_class_minimums": {}}},
         "method_version": "logistic_recalibration_v1",
         "selected_artifacts_by_scope": {"\0".join(scope.source_key): {
             "artifact_version": artifact.artifact_version, "family": artifact.family}}},
        required_settings=("support_by_scope", "method_version", "selected_artifacts_by_scope"))
    result = _evaluate_scope_readiness(dataset, changed_signals, artifact, scope, protocol)
    assert result.status is CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE


def test_repeated_calibration_occurrences_count_one_patient_group(registered_collection):
    from test_training_acceptance import _make_service
    from tests.training_fixtures import training_scope
    registry, register = registered_collection
    partitions = {
        "train": (("t1", 0), ("t2", 0), ("t3", 1), ("t4", 1)),
        "validation": (("v1", 0), ("v2", 1), ("v3", 0), ("v4", 1)),
        "calibration": (("same-patient", 0), ("same-patient", 1)),
    }
    _, dataset, signals, _, _, service = _make_service(registered_collection, partitions=partitions)
    artifact = service.train(dataset, signals)[0].artifact
    scope = training_scope(registry, artifact.scope.model_id, artifact.scope.model_version,
                           artifact.scope.label_id)
    protocol = CalibrationProtocol("calibration", "v1", (scope,),
        {"support_by_scope": {"\0".join(scope.source_key): {
            "minimum_patient_groups": 2, "correctness_class_minimums": {}}},
         "method_version": "logistic_recalibration_v1",
         "selected_artifacts_by_scope": {"\0".join(scope.source_key): {
             "artifact_version": artifact.artifact_version, "family": artifact.family}}},
        required_settings=("support_by_scope", "method_version", "selected_artifacts_by_scope"))
    result = _evaluate_scope_readiness(dataset, signals, artifact, scope, protocol)
    assert result.status is CalibrationStatus.INSUFFICIENT_EVIDENCE
