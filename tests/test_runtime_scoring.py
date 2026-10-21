from math import exp

import pytest

from runtime_fixtures import build_runtime_fixture
from safira.runtime._verification import admit_runtime_request
from safira.runtime._signals import derive_runtime_signal_record
from safira.runtime._scoring import apply_frozen_runtime_score


@pytest.mark.parametrize("force_logistic", [False, True])
def test_frozen_estimator_and_calibrator_match_independent_scalar_calculation(
        registered_collection, force_logistic):
    fixture = build_runtime_fixture(registered_collection, force_logistic=force_logistic)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    signal_record, _ = derive_runtime_signal_record(admitted)
    score = apply_frozen_runtime_score(admitted, signal_record)
    artifact = fixture.request.estimator
    calibrator = fixture.request.calibrator
    assert artifact.family == ("l2_logistic" if force_logistic else "prevalence_baseline")
    if artifact.family == "l2_logistic":
        feature = signal_record.predictors[0].value
        preprocessing = artifact.preprocessing
        column = artifact.feature_schema["columns"][0]["name"]
        normalized = (feature - preprocessing["means"][column]) / preprocessing["scales"][column]
        raw = artifact.estimator_state["intercept"] + artifact.estimator_state["coefficients"][0] * normalized
        calibrated_logit = calibrator.mapping["intercept"] + calibrator.mapping["slope"] * raw
        expected = 1.0 / (1.0 + exp(-calibrated_logit))
    else:
        expected = calibrator.mapping["constant_probability"]
    assert score.value == pytest.approx(expected, rel=0, abs=1e-12)
    assert 0.0 <= score.value <= 1.0


def test_nonfinite_or_incompatible_runtime_signal_never_produces_a_score(registered_collection):
    from dataclasses import replace
    from safira.runtime._exceptions import RuntimeReadinessFailure
    from safira.signals.base import SignalState

    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    signal_record, _ = derive_runtime_signal_record(admitted)
    changed = replace(signal_record.predictors[0], state=SignalState.INVALID, value=None,
                      reason_code="evidence_invalid")
    invalid_record = replace(signal_record, predictors=(changed,))
    with pytest.raises(RuntimeReadinessFailure):
        apply_frozen_runtime_score(admitted, invalid_record)

