"""Public service boundary tests for Feature 006 Batch C."""

import importlib
import importlib.util

import pytest


def _service_module():
    spec = importlib.util.find_spec("safira.calibration.service")
    assert spec is not None, "public exact-scope CalibrationService is not implemented"
    return importlib.import_module("safira.calibration.service")


def _approved_protocol(base_protocol, scope):
    from safira.calibration.records import CalibrationProtocol
    configuration = dict(base_protocol.configuration)
    configuration["logistic_settings_by_scope"] = {"\0".join(scope.source_key): {
        "tol": 1e-8, "max_iter": 1000, "solver": "lbfgs", "penalty": None,
        "fit_intercept": True, "class_weight": None, "warm_start": False,
        "occurrence_weighting": "unit_per_occurrence",
        "convergence_criterion": "warning_and_iteration_limit_v1",
        "deterministic_expectation": "same_environment_repeat_v1",
        "score_identifiability_criterion": "intercept_plus_score_full_rank_v1",
        "separation_criterion": "scalar_range_ordering_v1", "slope_rule": "strictly_positive",
    }}
    required = tuple(dict.fromkeys((*base_protocol.required_settings, "logistic_settings_by_scope")))
    return CalibrationProtocol(base_protocol.protocol_id, base_protocol.version, (scope,),
                               configuration, required_settings=required)


def test_service_executes_shared_admission_before_score_or_fit_helpers(monkeypatch, registered_collection):
    from dataclasses import replace
    from test_calibration_bundle_gate import setup

    registry, dataset, signals, artifact, scope, base_protocol, verifier = setup(registered_collection)
    protocol = _approved_protocol(base_protocol, scope)
    service_module = _service_module()
    service = service_module.CalibrationService(registry, protocol, verifier)
    calls = []
    monkeypatch.setattr("safira.calibration.service._reconstruct_feature_state",
                        lambda *a, **k: calls.append("score") or None)
    monkeypatch.setattr("safira.calibration.service._fit_scope_mapping",
                        lambda *a, **k: calls.append("fit") or None)
    changed = replace(dataset, manifest_reference="mismatched-manifest")
    with pytest.raises(Exception):
        service.calibrate(changed, signals, {scope.source_key: artifact})
    assert calls == []


def test_service_returns_one_safe_result_per_protocol_scope_in_stable_order(registered_collection):
    from test_calibration_bundle_gate import setup

    registry, dataset, signals, artifact, scope, base_protocol, verifier = setup(registered_collection)
    protocol = _approved_protocol(base_protocol, scope)
    service = _service_module().CalibrationService(registry, protocol, verifier)
    outcomes = service.calibrate(dataset, signals, {scope.source_key: artifact})
    assert len(outcomes) == 1
    assert outcomes[0].scope.source_key == scope.source_key
    assert outcomes[0].status.value in {"CALIBRATOR_FITTED_UNEVALUATED", "NUMERICAL_FAILURE",
                                        "INSUFFICIENT_EVIDENCE"}
    assert outcomes[0].artifact is None or outcomes[0].status.value == "CALIBRATOR_FITTED_UNEVALUATED"


def test_unapproved_protocol_is_not_ready_and_does_not_call_numerical_helpers(monkeypatch, registered_collection):
    from safira.calibration.records import CalibrationProtocol, CalibrationStatus
    from test_calibration_bundle_gate import setup

    registry, dataset, signals, artifact, scope, _, verifier = setup(registered_collection)
    protocol = CalibrationProtocol("not-approved", "v1", (scope,), {}, required_settings=("approval",))
    service = _service_module().CalibrationService(registry, protocol, verifier)
    monkeypatch.setattr("safira.calibration.service._reconstruct_feature_state",
                        lambda *a, **k: pytest.fail("unapproved protocol reached score reconstruction"))
    outcomes = service.calibrate(dataset, signals, {scope.source_key: artifact})
    assert outcomes[0].status is CalibrationStatus.NOT_READY
    assert outcomes[0].artifact is None


def test_protocol_with_unapproved_solver_is_rejected_before_score_reconstruction(monkeypatch, registered_collection):
    from safira.calibration.records import CalibrationStatus
    from test_calibration_acceptance import _service_case

    registry, dataset, signals, artifacts, configured_service, verifier, family = _service_case(registered_collection)
    assert family == "l2_logistic"
    _, artifact = next(iter(artifacts.items()))
    scope = artifact.scope
    protocol = configured_service._protocol
    config = dict(protocol.configuration)
    by_scope = dict(config["logistic_settings_by_scope"])
    settings = dict(by_scope["\0".join(scope.source_key)])
    settings["solver"] = "saga"
    by_scope["\0".join(scope.source_key)] = settings
    config["logistic_settings_by_scope"] = by_scope
    from safira.calibration.records import CalibrationProtocol
    protocol = CalibrationProtocol(protocol.protocol_id, protocol.version, protocol.scopes,
                                   config, required_settings=protocol.required_settings)
    service = _service_module().CalibrationService(registry, protocol, verifier)
    monkeypatch.setattr("safira.calibration.service._reconstruct_feature_state",
                        lambda *a, **k: pytest.fail("unapproved solver reached score reconstruction"))
    outcomes = service.calibrate(dataset, signals, artifacts)
    assert outcomes[0].status is CalibrationStatus.NOT_READY
