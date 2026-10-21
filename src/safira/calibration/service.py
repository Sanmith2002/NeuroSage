"""Public exact-scope Feature 006 calibration orchestration.

This service fits cohort-level mapping parameters only. It intentionally has no
per-patient apply/predict method and never accesses protected test partitions.
"""

from __future__ import annotations

from hashlib import sha256
import importlib.metadata
import json
from math import isfinite
import platform
from collections.abc import Mapping

from safira.calibration.exceptions import CalibrationCompatibilityError
from safira.calibration.fitting import _fit_scope_mapping
from safira.calibration.records import (
    CalibratorArtifact, CalibrationOutcome, CalibrationProtocol, CalibrationStatus,
)
from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
from safira.calibration.verification import _verify_bundle


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _digest(value):
    return sha256(json.dumps(_plain(value), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _versions():
    values = {"python": platform.python_version()}
    for package, key in (("scikit-learn", "scikit_learn"), ("numpy", "numpy"), ("scipy", "scipy")):
        try:
            values[key] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            values[key] = "unavailable"
    return values


def _make_artifact(inputs, scope, fit):
    from safira.signals.validation import dataset_fingerprint
    from safira.training.verification import feature_set_fingerprint, _inventory, _methods

    dataset, signals = inputs._dataset, inputs._signals
    base = inputs._artifacts[scope.source_key]
    ref = signals.dataset_reference
    inventory_digest = _digest(_inventory(dataset, signals, ref))
    methods = tuple(sorted((item[0], item[1], sha256(item[2].encode("utf-8")).hexdigest())
                           for item in _methods(signals)))
    run = signals.manifest
    protocol = inputs._protocol
    dataset_reference = {
        "dataset_id": ref.dataset_id,
        "manifest_reference": ref.manifest_reference,
        "manifest_digest": ref.manifest_digest,
        "protocol_id": ref.protocol_id,
        "protocol_version": ref.protocol_version,
        "builder_version": ref.builder_version,
        "inventory_digest": inventory_digest,
    }
    signal_reference = {
        "run_version": run.run_version,
        "feature_set_fingerprint": feature_set_fingerprint(signals),
        "method_ids": methods,
        "fitted_state_ids": tuple(sorted(item.state_id for item in run.fitted_state_references)),
        "scope_key": scope.source_key,
    }
    protocol_payload = protocol.to_dict()
    calibration_protocol = {"protocol_id": protocol.protocol_id, "version": protocol.version,
                            "configuration_digest": _digest(protocol_payload)}
    if fit.slope is not None:
        method_id = "logistic_calibration_v1"
        settings = protocol.configuration.get("logistic_settings_by_scope", {}).get("\0".join(scope.source_key), {})
        mapping = {"intercept": fit.intercept, "slope": fit.slope,
                   "input_semantics": "feature005_logistic_linear_predictor"}
        fitting = {"solver": fit.solver, "penalty": fit.penalty, "fit_intercept": True,
                   "class_weight": None, "warm_start": False, "tol": settings["tol"],
                   "max_iter": settings["max_iter"], "occurrence_weighting": "unit_per_occurrence",
                   "convergence_criterion": settings["convergence_criterion"],
                   "deterministic_expectation": settings["deterministic_expectation"],
                   "score_identifiability_criterion": settings["score_identifiability_criterion"],
                   "separation_criterion": settings["separation_criterion"],
                   "slope_rule": settings["slope_rule"], "converged": True,
                   "iterations": fit.iterations}
    else:
        method_id = "prevalence_offset_v1"
        mapping = {"base_probability": base.estimator_state["probability"], "offset": fit.offset,
                   "constant_probability": fit.constant_probability, "constant_output": True,
                   "no_individualized_discrimination": True}
        fitting = {"occurrence_weighting": "unit_per_occurrence", "closed_form": True,
                   "converged": True, "iterations": 0}
    return CalibratorArtifact(
        scope=scope,
        base_artifact_digest=base.digest,
        base_artifact_version=base.artifact_version,
        base_family=base.family,
        base_feature_schema_digest=base.preprocessing["schema_digest"],
        base_preprocessing_digest=_digest(base.preprocessing),
        dataset_reference=dataset_reference,
        signal_run_reference=signal_reference,
        calibration_protocol=calibration_protocol,
        method_id=method_id,
        method_version="1",
        mapping=mapping,
        fitting_configuration=fitting,
        dependency_versions=_versions(),
        lifecycle={"status": CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED.value,
            "not_independently_evaluated": True, "non_deployable": True,
            "not_clinically_validated": True, "calibration_partition_spent": True,
            "protected_test_accessed": False, "validation_selection_spent": True},
    )


def _logistic_settings_ready(protocol, scope):
    settings_by_scope = protocol.configuration.get("logistic_settings_by_scope", {})
    settings = settings_by_scope.get("\0".join(scope.source_key)) if hasattr(settings_by_scope, "get") else None
    required = {"tol", "max_iter", "solver", "penalty", "fit_intercept", "class_weight", "warm_start",
                "occurrence_weighting", "convergence_criterion", "deterministic_expectation",
                "score_identifiability_criterion", "separation_criterion", "slope_rule"}
    if not hasattr(settings, "keys") or not required <= set(settings):
        return False
    return (
        settings["solver"] == "lbfgs" and settings["penalty"] is None
        and settings["fit_intercept"] is True and settings["class_weight"] is None
        and settings["warm_start"] is False
        and settings["occurrence_weighting"] == "unit_per_occurrence"
        and settings["convergence_criterion"] == "warning_and_iteration_limit_v1"
        and settings["deterministic_expectation"] == "same_environment_repeat_v1"
        and settings["score_identifiability_criterion"] == "intercept_plus_score_full_rank_v1"
        and settings["separation_criterion"] == "scalar_range_ordering_v1"
        and settings["slope_rule"] == "strictly_positive"
        and type(settings["tol"]) in (int, float) and type(settings["tol"]) is not bool
        and isfinite(settings["tol"]) and settings["tol"] > 0
        and type(settings["max_iter"]) is int and settings["max_iter"] > 0
    )


class CalibrationService:
    """Run approved calibration fitting after complete shared evidence admission."""

    def __init__(self, registry, protocol: CalibrationProtocol, input_verifier):
        if registry is None or type(protocol) is not CalibrationProtocol or input_verifier is None:
            raise ValueError("calibration_service_configuration")
        self._registry = registry
        self._protocol = protocol
        self._input_verifier = input_verifier

    def calibrate(self, dataset, signals, artifacts: Mapping):
        """Return one safe, exact-scope outcome after atomic input admission."""
        verified = _verify_bundle(self._registry, dataset, signals, artifacts,
                                  self._protocol, self._input_verifier)
        outcomes = []
        method_parameters = {item.method_id: item.parameters for item in signals.manifest.method_configs}
        for scope in sorted(self._protocol.scopes, key=lambda item: item.source_key):
            readiness = verified.readiness[scope.source_key]
            if readiness.status is not None:
                outcomes.append(CalibrationOutcome(scope, readiness.status, readiness.reason_code))
                continue
            base = verified._artifacts[scope.source_key]
            if not self._protocol.ready or (base.family == "l2_logistic"
                                             and not _logistic_settings_ready(self._protocol, scope)):
                outcomes.append(CalibrationOutcome(scope, CalibrationStatus.NOT_READY, "approval_missing"))
                continue
            try:
                state = _reconstruct_feature_state(base, method_parameters)
            except Exception:
                outcomes.append(CalibrationOutcome(scope, CalibrationStatus.INCOMPATIBLE_INPUT,
                                                   "scope_incompatible"))
                continue
            rows = tuple(row for row in signals.calibration if row.source_key.to_tuple() == scope.source_key)
            scores = _reconstruct_scores(state, rows)
            if scores.status is not None:
                outcomes.append(CalibrationOutcome(scope, scores.status, scores.reason_code))
                continue
            fit = _fit_scope_mapping(verified, scope, scores, self._protocol)
            if fit.status is not None:
                outcomes.append(CalibrationOutcome(scope, fit.status, fit.reason_code))
                continue
            try:
                artifact = _make_artifact(verified, scope, fit)
            except Exception:
                # No sensitive exception details leave the service boundary.
                outcomes.append(CalibrationOutcome(scope, CalibrationStatus.INVALID_INPUT, "input_invalid"))
                continue
            outcomes.append(CalibrationOutcome(
                scope, CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED, "admission_complete", artifact,
                ("unevaluated", "non_deployable", "not_clinically_validated"),
            ))
        return tuple(outcomes)
