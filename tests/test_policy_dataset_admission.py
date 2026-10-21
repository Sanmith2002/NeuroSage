"""Negative tests for exact policy-cohort and outcome admission."""

from dataclasses import replace

import pytest

from policy_fixtures import make_end_to_end_case
from safira.policy import PolicyError


def _select(service, data, original, signal_protocol, estimator, calibrator):
    return service.select(policy_dataset=data, original_training_dataset=original,
        original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
        calibrator_artifacts=calibrator)


def test_changed_correctness_target_is_rejected_before_selection(registered_collection):
    service, _, _, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    changed = replace(data.development.validation[0], correctness_target=0)
    data = replace(data, development=replace(data.development,
        validation=(changed,) + data.development.validation[1:]))
    with pytest.raises(PolicyError):
        _select(service, data, original, signal_protocol, estimator, calibrator)


def test_missing_extra_duplicate_or_changed_prediction_inventory_is_rejected(registered_collection):
    service, _, _, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    rows = data.development.validation
    mutations = (
        (),
        rows + (rows[0],),
        (replace(rows[0], correctness_target=1 - rows[0].correctness_target),) + rows[1:],
    )
    for validation in mutations:
        candidate = replace(data, development=replace(data.development, validation=validation))
        with pytest.raises(PolicyError):
            _select(service, candidate, original, signal_protocol, estimator, calibrator)


def test_wrong_target_binding_and_wrong_original_inventory_fail_closed(registered_collection):
    service, _, protocol, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    wrong_target = replace(protocol, target_bindings={"policy-model\0v1\0label-a": ("other-target", "v1")})
    from safira.policy.service import PolicySelectionService
    with pytest.raises(PolicyError):
        PolicySelectionService(service._registry, wrong_target, service._input_verifier).select(
            policy_dataset=data, original_training_dataset=original, original_signal_protocol=signal_protocol,
            estimator_artifacts=estimator, calibrator_artifacts=calibrator)
    changed_original = replace(original, manifest_reference="changed-original-manifest")
    with pytest.raises(PolicyError):
        _select(service, data, changed_original, signal_protocol, estimator, calibrator)


def test_stale_or_wrongly_scoped_disjointness_check_fails_closed(registered_collection):
    service, ledger, _, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    genuine = ledger.verify_patient_disjointness
    def stale(*args):
        return replace(genuine(*args), policy_manifest_digest="0" * 64)
    ledger.verify_patient_disjointness = stale
    with pytest.raises(PolicyError):
        _select(service, data, original, signal_protocol, estimator, calibrator)
