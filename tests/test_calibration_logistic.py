"""Synthetic test-first checks for the fixed unpenalized logistic mapping."""

import pytest


def test_logistic_fit_uses_approved_unpenalized_form_and_is_reproducible():
    from safira.calibration.fitting import _fit_logistic
    scores = (0., 1., 2., 1., 1.5)
    targets = (0, 0, 0, 1, 1)
    first = _fit_logistic(scores, targets, tol=1e-9, max_iter=1000)
    second = _fit_logistic(scores, targets, tol=1e-9, max_iter=1000)
    assert first.status is None
    assert first.slope > 0
    assert first.intercept == pytest.approx(second.intercept, abs=1e-10)
    assert first.slope == pytest.approx(second.slope, abs=1e-10)
    assert first.solver == "lbfgs" and first.penalty is None


def test_logistic_fit_rejects_separation_nonpositive_slope_and_nonconvergence():
    from safira.calibration.fitting import _fit_logistic
    from safira.calibration.records import CalibrationStatus
    separated = _fit_logistic((0., 1., 2., 3.), (0, 0, 1, 1), tol=1e-9, max_iter=100)
    assert separated.status is CalibrationStatus.NUMERICAL_FAILURE
    reversed_scores = _fit_logistic((0., 2., 4., 0., 1., 3.), (0, 0, 0, 1, 1, 1),
                                    tol=1e-9, max_iter=1000)
    assert reversed_scores.status is CalibrationStatus.NUMERICAL_FAILURE
    assert reversed_scores.slope is not None and reversed_scores.slope <= 0
    nonconverged = _fit_logistic((0., 1., 2., 1., 1.5), (0, 0, 0, 1, 1), tol=1e-15, max_iter=1)
    assert nonconverged.status is CalibrationStatus.NUMERICAL_FAILURE


def test_logistic_fit_rejects_nonfinite_and_invalid_targets():
    from safira.calibration.fitting import _fit_logistic
    from safira.calibration.records import CalibrationStatus
    assert _fit_logistic((0., float("nan")), (0, 1), tol=1e-6, max_iter=20).status is CalibrationStatus.INVALID_INPUT
    assert _fit_logistic((0., 1.), (0, 2), tol=1e-6, max_iter=20).status is CalibrationStatus.INVALID_INPUT


def test_logistic_constructor_and_objective_are_explicit(monkeypatch):
    import sklearn.linear_model
    from safira.calibration.fitting import _fit_logistic
    captured = {}
    class FakeLogisticRegression:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
        def fit(self, x, y, sample_weight):
            captured.update(x=x, y=y, sample_weight=sample_weight)
            self.classes_ = [0, 1]
            self.n_iter_ = [2]
            self.intercept_ = [0.1]
            self.coef_ = [[0.2]]
            return self
    monkeypatch.setattr(sklearn.linear_model, "LogisticRegression", FakeLogisticRegression)
    result = _fit_logistic((0., 1., 2., 1., 1.5), (0, 0, 0, 1, 1), tol=1e-7, max_iter=30)
    assert result.status is None
    assert captured["init"] == {"penalty": None, "solver": "lbfgs", "fit_intercept": True,
                                "class_weight": None, "warm_start": False,
                                "tol": 1e-7, "max_iter": 30}
    assert captured["y"] == [0, 0, 0, 1, 1]
    assert captured["sample_weight"] == [1.0] * 5
    assert captured["x"] == [[0.], [1.], [2.], [1.], [1.5]]
