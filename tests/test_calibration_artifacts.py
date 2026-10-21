"""Test-first contracts for immutable, safe Feature 006 calibrator artifacts."""

from dataclasses import FrozenInstanceError

import pytest

from safira.training.records import TrainingScope


def _artifact_type():
    import safira.calibration.records as records
    artifact_type = getattr(records, "CalibratorArtifact", None)
    assert artifact_type is not None, "Feature 006 CalibratorArtifact contract is not implemented"
    return artifact_type


def _scope():
    return TrainingScope("model-a", "v1", "label-a", "a" * 64, "adapter", "1", "b" * 64,
                         {"pipeline": {"steps": ["normalize-v1"]}})


def _artifact_payload():
    return {
        "scope": _scope(),
        "base_artifact_digest": "c" * 64,
        "base_artifact_version": "safira-correctness-estimator-v1",
        "base_family": "l2_logistic",
        "base_feature_schema_digest": "d" * 64,
        "base_preprocessing_digest": "e" * 64,
        "dataset_reference": {
            "dataset_id": "dataset-a", "manifest_reference": "manifest-a",
            "manifest_digest": "f" * 64, "protocol_id": "dataset-protocol",
            "protocol_version": "v1", "builder_version": "builder-v1",
            "inventory_digest": "1" * 64,
        },
        "signal_run_reference": {
            "run_version": "run-v1", "feature_set_fingerprint": "2" * 64,
            "method_ids": [["entropy", "v1", "3" * 64]],
            "fitted_state_ids": ("state-a",), "scope_key": _scope().source_key,
        },
        "calibration_protocol": {"protocol_id": "dataset-protocol", "version": "v1",
                                 "configuration_digest": "4" * 64},
        "method_id": "logistic_calibration_v1",
        "method_version": "1",
        "mapping": {"intercept": -0.2, "slope": 1.1,
                    "input_semantics": "feature005_logistic_linear_predictor"},
        "fitting_configuration": {"solver": "lbfgs", "penalty": None,
                                  "fit_intercept": True, "class_weight": None,
                                  "warm_start": False, "tol": 1e-8, "max_iter": 1000,
                                  "occurrence_weighting": "unit_per_occurrence",
                                  "convergence_criterion": "warning_and_iteration_limit_v1",
                                  "deterministic_expectation": "same_environment_repeat_v1",
                                  "score_identifiability_criterion": "intercept_plus_score_full_rank_v1",
                                  "separation_criterion": "scalar_range_ordering_v1",
                                  "slope_rule": "strictly_positive", "converged": True,
                                  "iterations": 7},
        "dependency_versions": {"scikit_learn": "1.7.1", "numpy": "2.0.0",
                                "scipy": "1.14.0"},
        "lifecycle": {
            "status": "CALIBRATOR_FITTED_UNEVALUATED",
            "not_independently_evaluated": True, "non_deployable": True,
            "not_clinically_validated": True, "calibration_partition_spent": True,
            "protected_test_accessed": False, "validation_selection_spent": True,
        },
    }


def test_calibrator_artifact_is_deeply_immutable_and_defensively_detached():
    source = _artifact_payload()
    artifact = _artifact_type()(**source)
    source["dataset_reference"]["manifest_reference"] = "mutated"
    source["signal_run_reference"]["method_ids"][0] = ("bad", "v0", "0" * 64)
    source["mapping"]["slope"] = 9.0
    assert artifact.dataset_reference["manifest_reference"] == "manifest-a"
    assert artifact.mapping["slope"] == 1.1
    with pytest.raises(TypeError):
        artifact.mapping["slope"] = 2.0
    detached = artifact.to_dict()
    detached["mapping"]["slope"] = 8.0
    assert artifact.mapping["slope"] == 1.1
    with pytest.raises(FrozenInstanceError):
        artifact.method_id = "changed"


@pytest.mark.parametrize("changes", [
    {"mapping": {"intercept": float("nan"), "slope": 1.0,
                  "input_semantics": "feature005_logistic_linear_predictor"}},
    {"mapping": {"intercept": 0.0, "slope": 0.0,
                  "input_semantics": "feature005_logistic_linear_predictor"}},
    {"lifecycle": {"status": "CALIBRATOR_FITTED_UNEVALUATED",
                    "not_independently_evaluated": False, "non_deployable": True,
                    "not_clinically_validated": True, "calibration_partition_spent": True,
                    "protected_test_accessed": False, "validation_selection_spent": True}},
    {"scope": TrainingScope("model-b", "v1", "label-a", "a" * 64, "adapter", "1", "b" * 64,
                             {"pipeline": {"steps": ["normalize-v1"]}})},
])
def test_calibrator_artifact_rejects_invalid_parameters_lifecycle_or_inconsistent_scope(changes):
    payload = _artifact_payload()
    payload.update(changes)
    with pytest.raises(ValueError):
        _artifact_type()(**payload)


def test_baseline_artifact_has_only_constant_non_individualized_mapping():
    payload = _artifact_payload()
    payload.update({"method_id": "prevalence_offset_v1", "base_family": "prevalence_baseline",
                    "mapping": {"base_probability": 0.25, "offset": 0.4,
                                "constant_probability": 0.5, "constant_output": True,
                                "no_individualized_discrimination": True},
                        "fitting_configuration": {"occurrence_weighting": "unit_per_occurrence",
                            "closed_form": True, "converged": True, "iterations": 0}})
    artifact = _artifact_type()(**payload)
    assert artifact.mapping["constant_output"] is True
    assert artifact.mapping["no_individualized_discrimination"] is True
    assert "slope" not in artifact.mapping


def test_calibration_outcome_rejects_artifact_for_non_success_and_requires_it_for_success():
    from safira.calibration.records import CalibrationOutcome, CalibrationStatus

    scope = _scope()
    with pytest.raises(ValueError):
        CalibrationOutcome(scope, CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED,
                           "admission_complete")
    with pytest.raises(ValueError):
        CalibrationOutcome(scope, CalibrationStatus.NOT_READY, "approval_missing", object())


def test_allowlisted_export_has_integrity_digest_and_exact_compatibility():
    import importlib
    artifacts = importlib.util.find_spec("safira.calibration.artifacts")
    assert artifacts is not None, "allowlisted artifact module is not implemented"
    artifacts = importlib.import_module("safira.calibration.artifacts")
    artifact = _artifact_type()(**_artifact_payload())
    exporter = getattr(artifacts, "export_calibrator_artifact", None)
    validator = getattr(artifacts, "validate_calibrator_artifact", None)
    assert callable(exporter), "allowlisted artifact export is not implemented"
    assert callable(validator), "exact compatibility validation is not implemented"
    payload = exporter(artifact)
    expected = {"scope": _scope(), "base_artifact_digest": "c" * 64,
                "base_artifact_version": "safira-correctness-estimator-v1",
                "base_family": "l2_logistic"}
    assert validator(payload, expected=expected).digest == artifact.digest
    payload["mapping"]["slope"] = 1.2
    with pytest.raises(ValueError):
        validator(payload, expected=expected)
    unchanged = exporter(artifact)
    with pytest.raises(ValueError):
        validator(unchanged, expected={**expected, "base_artifact_digest": "9" * 64})
    with pytest.raises(ValueError):
        validator(unchanged, expected={**expected, "scope": TrainingScope(
            "model-a", "v9", "label-a", "a" * 64, "adapter", "1", "b" * 64,
            {"pipeline": {"steps": ["normalize-v1"]}})})


def test_artifact_and_outcome_serialization_and_repr_exclude_restricted_payload():
    from safira.calibration.records import CalibrationOutcome, CalibrationStatus
    artifact = _artifact_type()(**_artifact_payload())
    outcome = CalibrationOutcome(_scope(), CalibrationStatus.CALIBRATOR_FITTED_UNEVALUATED,
                                 "admission_complete", artifact,
                                 ("unevaluated", "non_deployable", "not_clinically_validated"))
    surfaces = (repr(artifact), str(artifact), repr(outcome), str(outcome),
                str(artifact.to_dict()), str(outcome.to_dict()))
    forbidden = ("patient-secret", "group-secret", "occurrence-secret", "row-secret",
                 "target-secret", "outcome-secret", "protected-secret", "verifier-secret")
    assert not any(term in " ".join(surfaces) for term in forbidden)

