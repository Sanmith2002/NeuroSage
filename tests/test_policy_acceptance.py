from dataclasses import replace

import pytest

from policy_fixtures import make_end_to_end_case
from safira.policy import PolicyError, PolicyStatus


def test_end_to_end_selects_and_freezes_only_aggregate_policy(registered_collection):
    service, _, _, policy_data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    assert next(iter(estimator.values())).family == "prevalence_baseline"
    assert next(iter(calibrator.values())).method_id == "prevalence_offset_v1"
    outcomes = service.select(policy_dataset=policy_data, original_training_dataset=original,
        original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
        calibrator_artifacts=calibrator)
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is PolicyStatus.SELECTED_UNEVALUATED
    assert outcome.artifact is not None
    assert outcome.artifact.selection_evidence_spent
    assert not outcome.artifact.protected_test_accessed
    assert not outcome.artifact.deployable
    surface = str(outcome.to_dict()) + repr(outcome)
    for forbidden in ("policy-group", "policy-patient", "correctness_target", "outcome", "patient_group_ref"):
        assert forbidden not in surface
    repeated = service.select(policy_dataset=policy_data, original_training_dataset=original,
        original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
        calibrator_artifacts=calibrator)
    assert repeated[0].artifact.digest == outcome.artifact.digest


def test_logistic_estimator_and_calibrator_match_direct_sigmoid_mapping(registered_collection, monkeypatch):
    import math
    import safira.policy.service as service_module
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    from safira.policy.scoring import reconstruct_calibrated_scores as apply_chain

    service, _, _, policy_data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(
        registered_collection, force_logistic=True)
    base = next(iter(estimator.values()))
    mapping = next(iter(calibrator.values())).mapping
    assert base.family == "l2_logistic"
    assert next(iter(calibrator.values())).method_id == "logistic_calibration_v1"
    captured = {}
    def capture(artifact, calibration, rows, parameters):
        captured["rows"] = tuple(rows)
        result = apply_chain(artifact, calibration, rows, parameters)
        captured["result"] = result
        return result
    monkeypatch.setattr(service_module, "reconstruct_calibrated_scores", capture)
    outcomes = service.select(policy_dataset=policy_data, original_training_dataset=original,
        original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
        calibrator_artifacts=calibrator)
    assert outcomes[0].status is PolicyStatus.SELECTED_UNEVALUATED
    state = _reconstruct_feature_state(base, {item.method_id: item.parameters
        for item in signal_protocol.method_configs.values()})
    raw = _reconstruct_scores(state, captured["rows"])
    expected = tuple(1 / (1 + math.exp(-(float(mapping["intercept"])
        + float(mapping["slope"]) * score))) for score in raw.scores)
    assert captured["result"].values == pytest.approx(expected)


def test_unadmitted_prediction_and_unapproved_protocol_fail_at_full_boundary(registered_collection):
    service, ledger, protocol, policy_data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    ledger.approved_protocols.clear()
    with pytest.raises(PolicyError):
        service.select(policy_dataset=policy_data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)
    ledger.admit_protocol(protocol)
    changed = replace(policy_data, manifest_reference="caller-forged")
    with pytest.raises(PolicyError):
        service.select(policy_dataset=changed, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)


def test_incomplete_or_overlapping_patient_history_fails_closed(registered_collection):
    service, ledger, _, policy_data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    ledger.complete_history = False
    with pytest.raises(PolicyError):
        service.select(policy_dataset=policy_data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)
    ledger.complete_history = True
    policy_id = service._protocol.policy_evidence.dataset_id
    original_id = next(key for key in ledger.groups if key != policy_id)
    ledger.groups[policy_id] = set(ledger.groups[original_id])
    with pytest.raises(PolicyError):
        service.select(policy_dataset=policy_data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)


def test_calibrator_origin_must_be_independently_ledgered(registered_collection):
    service, ledger, _, policy_data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    ledger.origin.artifacts.clear()
    for item in estimator.values():
        ledger.origin.admit_artifact(item)
    with pytest.raises(PolicyError):
        service.select(policy_dataset=policy_data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)


def test_aggregate_results_require_explicit_protocol_disclosure(registered_collection):
    from dataclasses import replace
    from safira.policy.service import PolicySelectionService

    service, ledger, protocol, policy_data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    undisclosed = replace(protocol, disclose_support=False)
    ledger.admit_protocol(undisclosed)
    restricted_service = PolicySelectionService(service._registry, undisclosed, ledger)
    outcomes = restricted_service.select(policy_dataset=policy_data, original_training_dataset=original,
        original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
        calibrator_artifacts=calibrator)
    assert all(item.status is PolicyStatus.NOT_READY and item.artifact is None and item.summary is None
               for item in outcomes)
    assert all(item.reason_code == "aggregate_disclosure_not_authorized" for item in outcomes)
