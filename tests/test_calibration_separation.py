"""Exact one-dimensional logistic separation geometry tests."""

import pytest


@pytest.mark.parametrize("scores,targets,expected", [
    ((0., 1., 2., 1.), (0, 0, 0, 1), None),  # singleton interior: finite-MLE geometry
    ((0., 1., 2., 3.), (0, 0, 1, 1), "separated"),
    ((0., 1., 1., 2.), (0, 0, 1, 1), "separated"),  # quasi-separation at equality
    ((2., 3., 0., 1.), (0, 0, 1, 1), "separated"),  # reverse direction
    ((1., 1., 1., 1.), (0, 0, 1, 1), "rank_deficient"),
])
def test_scalar_separation_geometry(scores, targets, expected):
    from safira.calibration.fitting import _separation_check
    assert _separation_check(scores, targets) == expected


def test_missing_class_and_nonfinite_scores_are_not_finite_mle_designs():
    from safira.calibration.fitting import _separation_check
    assert _separation_check((0., 1.), (0, 0)) == "class_missing"
    assert _separation_check((0., float("nan")), (0, 1)) == "nonfinite"
