"""Test-first validation of frozen Feature 005 score reconstruction."""

from dataclasses import replace
import hashlib
import json

import pytest

from test_training_acceptance import _make_service
from tests.training_fixtures import build_inputs


def _artifact(registered_collection, validation_values=(1.0, 0.0, 1.0, 0.0)):
    registry, register = registered_collection
    _, dataset, signals, _, _, service = _make_service(
        registered_collection, validation_values=validation_values,
        train_values=(.05, .10, .90, .95))
    outcome = service.train(dataset, signals)[0]
    artifact = outcome.artifact
    return artifact, signals


def _parameters_from_signals(signals):
    return {config.method_id: dict(config.parameters) for config in signals.manifest.method_configs}


def test_reconstructs_exact_allowlisted_frozen_schema_and_preprocessing(registered_collection):
    from safira.calibration.scores import _reconstruct_feature_state
    artifact, signals = _artifact(registered_collection)
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    assert state.schema.scope == artifact.scope
    assert tuple(column.name for column in state.schema.columns) == tuple(
        item["name"] for item in artifact.feature_schema["columns"])
    assert state.preprocessing.to_dict() == artifact.to_dict()["preprocessing"]
    assert state.family == artifact.family
    assert state.estimator_classes == (0, 1)


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(artifact_version="unknown-v99"),
    lambda p: p["feature_schema"].update(extra="not-allowlisted"),
    lambda p: p["preprocessing"].update(active_indices=[999]),
    lambda p: p["estimator_state"].update(classes=[1, 0]),
    lambda p: p["estimator_state"].update(coefficients=[float("nan")]),
])
def test_rejects_malformed_or_incompatible_frozen_artifact(registered_collection, mutate):
    from safira.calibration.scores import _reconstruct_feature_state
    from safira.training.records import SafetyEstimatorArtifact
    artifact, signals = _artifact(registered_collection)
    payload = artifact.to_dict()
    payload.pop("digest")
    mutate(payload)
    with pytest.raises(ValueError):
        malformed = SafetyEstimatorArtifact.from_dict(payload)
        _reconstruct_feature_state(malformed, _parameters_from_signals(signals))


def test_schema_and_preprocessing_parser_never_fits_on_calibration_rows(registered_collection, monkeypatch):
    from safira.calibration.scores import _reconstruct_feature_state
    import safira.training.features as features
    artifact, signals = _artifact(registered_collection)
    def forbidden(*args, **kwargs):
        raise AssertionError("fit or schema construction is forbidden during calibration")
    monkeypatch.setattr(features, "build_feature_schema", forbidden)
    monkeypatch.setattr(features, "fit_preprocessing", forbidden)
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    assert state.schema.scope == artifact.scope


def test_calibration_score_reconstruction_matches_independent_frozen_z(registered_collection, monkeypatch):
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    import safira.training.features as features
    import safira.training.artifacts as artifacts
    artifact, signals = _artifact(registered_collection)
    monkeypatch.setattr(artifacts, "_reproduce_probability_for_test",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("test-only API called")))
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    transformed = features.transform_rows(state.preprocessing, state.schema, signals.calibration)
    expected = tuple(state.intercept + sum(c * x for c, x in zip(state.coefficients, row))
                     for row in transformed)
    result = _reconstruct_scores(state, signals.calibration)
    assert result.status is None
    assert result.scores == pytest.approx(expected, abs=1e-12)
    assert len(result.scores) == len(signals.calibration)


def test_required_unavailable_predictor_returns_no_fabricated_score(registered_collection):
    from dataclasses import replace
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    from safira.calibration.records import CalibrationStatus
    from safira.signals.base import SignalState
    artifact, signals = _artifact(registered_collection)
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    row = signals.calibration[0]
    changed = replace(row.predictors[0], state=SignalState.UNAVAILABLE, value=None,
                      reason_code="evidence_unavailable")
    result = _reconstruct_scores(state, (replace(row, predictors=(changed,)),))
    assert result.status is CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE
    assert result.scores == ()


def test_baseline_score_is_strict_interior_constant(registered_collection):
    from safira.calibration.scores import _reconstruct_feature_state, _reconstruct_scores
    from dataclasses import replace
    from safira.calibration.records import CalibrationStatus
    artifact, signals = _artifact(registered_collection, validation_values=(0.0, 1.0, 0.0, 1.0))
    assert artifact.family == "prevalence_baseline"
    state = _reconstruct_feature_state(artifact, _parameters_from_signals(signals))
    result = _reconstruct_scores(state, signals.calibration)
    assert result.status is None
    assert result.scores == (artifact.estimator_state["probability"],) * len(signals.calibration)
    boundary = _reconstruct_scores(replace(state, probability=0.0), signals.calibration)
    assert boundary.status is CalibrationStatus.NUMERICAL_FAILURE
    assert boundary.scores == ()
