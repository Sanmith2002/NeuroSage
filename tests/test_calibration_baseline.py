"""Closed-form constant-offset calibration tests."""

import math

import pytest


def test_baseline_offset_is_occurrence_weighted_and_constant():
    from safira.calibration.fitting import _fit_baseline
    from safira.calibration.fitting import _FitVectors
    vectors = _FitVectors((.2, .2, .2), (0, 0, 1), ("g1", "g1", "g2"), 2, (1, 1))
    result = _fit_baseline(vectors, .25)
    p_cal = 1 / 3
    expected = math.log(p_cal / (1 - p_cal)) - math.log(.25 / .75)
    assert result.status is None
    assert result.offset == pytest.approx(expected)
    assert result.constant_probability == pytest.approx(p_cal)
    assert result.constant_probability == pytest.approx(1 / 3)


@pytest.mark.parametrize("p0,targets", [(0.0, (0, 1)), (1.0, (0, 1)), (.5, (1, 1)), (float("nan"), (0, 1))])
def test_baseline_rejects_boundary_probability_or_missing_class(p0, targets):
    from safira.calibration.fitting import _fit_baseline, _FitVectors
    from safira.calibration.records import CalibrationStatus
    vectors = _FitVectors((.4,) * len(targets), targets, tuple(f"g{i}" for i in range(len(targets))),
                          len(set(targets)), (targets.count(0), targets.count(1)))
    expected = (CalibrationStatus.INSUFFICIENT_EVIDENCE if 0 not in targets or 1 not in targets
                else CalibrationStatus.NUMERICAL_FAILURE)
    assert _fit_baseline(vectors, p0).status is expected
