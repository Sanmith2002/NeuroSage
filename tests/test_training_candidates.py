import math
import warnings

import pytest


def _api():
    from safira.training.candidates import (
        CandidateStatus, LogisticCandidateConfig, fit_logistic_candidate,
        fit_prevalence_baseline, runtime_versions,
    )
    from safira.training.records import TrainingProtocol, TrainingScope, TrainingSupportCriteria
    return (CandidateStatus, LogisticCandidateConfig, fit_logistic_candidate,
            fit_prevalence_baseline, runtime_versions, TrainingProtocol, TrainingScope,
            TrainingSupportCriteria)


def _scope(Scope):
    return Scope("m", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "prep")


def _protocol(Protocol, Support, scope, *, groups=4, class_minimums=None, config=None):
    return Protocol("research-protocol", "v1", (scope,),
                    {scope.source_key: Support(groups, class_minimums or {})},
                    {scope.source_key: ()}, {}, {},
                    {} if config is None else {scope.source_key: config})


GROUPS = ("g1", "g2", "g3", "g4")


def test_prevalence_baseline_is_exact_scope_training_only_and_single_class_is_descriptive():
    Status, Config, fit, fit_baseline, versions, Protocol, Scope, Support = _api()
    scope = _scope(Scope)
    protocol = _protocol(Protocol, Support, scope, class_minimums={0: 2, 1: 2})
    baseline = fit_baseline(protocol, scope, (1, 0, 1, 0), patient_group_refs=GROUPS)
    assert baseline.probability == pytest.approx(.5)
    assert baseline.status is Status.FITTED
    assert baseline.versions == tuple(sorted(versions().items()))
    single_protocol = _protocol(Protocol, Support, scope, groups=2)
    single = fit_baseline(single_protocol, scope, (1, 1), patient_group_refs=("g1", "g2"))
    assert single.probability == 1.0
    assert single.status is Status.DESCRIPTIVE_ONLY
    other_scope = Scope("other", "v1", "label", "c" * 64, "adapter", "v1", "d" * 64, "prep")
    assert fit_baseline(protocol, other_scope, (1, 0), patient_group_refs=("g1", "g2")).status is Status.INCOMPATIBLE_INPUT
    assert set(versions()) == {"scikit_learn", "numpy", "scipy", "joblib", "threadpoolctl"}


def test_logistic_candidate_uses_fixed_approved_configuration_and_test_only_frozen_state_reproduction():
    Status, Config, fit, fit_baseline, versions, Protocol, Scope, Support = _api()
    scope = _scope(Scope)
    config = Config(approved=True, C=1.0, tol=1e-4, max_iter=200)
    protocol = _protocol(Protocol, Support, scope, class_minimums={0: 2, 1: 2}, config=config)
    matrix, targets = ((0.,), (.2,), (.8,), (1.,)), (0, 0, 1, 1)
    candidate = fit(protocol, scope, matrix, targets, patient_group_refs=GROUPS)
    assert candidate.status is Status.FITTED
    assert candidate.penalty == "l2" and candidate.solver == "lbfgs"
    assert candidate.class_weight is None and candidate.fit_intercept is True and candidate.warm_start is False
    assert len(candidate.coefficients) == 1 and math.isfinite(candidate.coefficients[0])
    assert math.isfinite(candidate.intercept) and candidate.classes == (0, 1)
    assert candidate.protocol_id == "research-protocol" and candidate.protocol_version == "v1"
    # Test-only reproduction from frozen coefficients/intercept; no public inference API is added.
    from sklearn.linear_model import LogisticRegression
    reference = LogisticRegression(penalty="l2", solver="lbfgs", C=1.0, tol=1e-4,
                                   max_iter=200, class_weight=None, fit_intercept=True,
                                   warm_start=False, random_state=None).fit(matrix, targets)
    score = candidate.intercept + candidate.coefficients[0] * .9
    reproduced = 1.0 / (1.0 + math.exp(-score))
    assert reference.classes_.tolist() == [0, 1]
    assert reproduced == pytest.approx(reference.predict_proba(((.9,),))[0][1], abs=1e-12)
    assert candidate.versions == tuple(sorted(versions().items()))


def test_logistic_rejects_missing_protocol_configuration_single_class_bad_matrix_and_nonfinite_inputs():
    Status, Config, fit, fit_baseline, versions, Protocol, Scope, Support = _api()
    scope = _scope(Scope)
    unconfigured = _protocol(Protocol, Support, scope, class_minimums={0: 1, 1: 1})
    assert fit(unconfigured, scope, ((0.,), (1.,)), (0, 1), patient_group_refs=("g1", "g2")).status is Status.NOT_READY
    config = Config(approved=True, C=.5, tol=1e-4, max_iter=100)
    protocol = _protocol(Protocol, Support, scope, groups=2, class_minimums={0: 1, 1: 1}, config=config)
    single = fit(protocol, scope, ((0.,), (1.,)), (1, 1), patient_group_refs=("g1", "g2"))
    assert single.status is Status.INSUFFICIENT_EVIDENCE
    bad = fit(protocol, scope, ((0.,), (float("nan"),)), (0, 1), patient_group_refs=("g1", "g2"))
    assert bad.status is Status.INVALID_INPUT
    unapproved = _protocol(Protocol, Support, scope, groups=2, class_minimums={0: 1, 1: 1},
                           config=Config(approved=False, C=.5, tol=1e-4, max_iter=100))
    assert fit(unapproved, scope, ((0.,), (1.,)), (0, 1), patient_group_refs=("g1", "g2")).status is Status.NOT_READY


def test_candidate_fit_has_no_retries_and_convergence_failure_is_explicit(monkeypatch):
    Status, Config, fit, fit_baseline, versions, Protocol, Scope, Support = _api()
    import safira.training.candidates as candidates
    calls = []
    original = candidates.LogisticRegression

    class WarningEstimator(original):
        def fit(self, X, y):
            calls.append((self.C, self.tol, self.max_iter, self.random_state))
            warnings.warn("synthetic convergence", candidates.ConvergenceWarning)
            return super().fit(X, y)

    monkeypatch.setattr(candidates, "LogisticRegression", WarningEstimator)
    scope = _scope(Scope)
    protocol = _protocol(Protocol, Support, scope, class_minimums={0: 2, 1: 2},
                         config=Config(approved=True, C=1.0, tol=1e-4, max_iter=1))
    result = fit(protocol, scope, ((0.,), (.1,), (.9,), (1.,)), (0, 0, 1, 1), patient_group_refs=GROUPS)
    assert result.status is Status.NONCONVERGED
    assert calls == [(1.0, 1e-4, 1, None)]


@pytest.mark.parametrize("failure,expected", [("exception", "FIT_FAILED"),
                                               ("nonfinite", "NONFINITE_RESULT"),
                                               ("class_shape", "NONFINITE_RESULT")])
def test_candidate_fit_and_result_validation_fail_with_safe_statuses(monkeypatch, failure, expected):
    Status, Config, fit, fit_baseline, versions, Protocol, Scope, Support = _api()
    import safira.training.candidates as candidates
    import numpy as np

    class ControlledEstimator:
        def __init__(self, **kwargs):
            pass

        def fit(self, X, y):
            if failure == "exception":
                raise RuntimeError("synthetic training rows must not escape")
            self.classes_ = np.array([0] if failure == "class_shape" else [0, 1])
            self.coef_ = np.array([[float("nan")]])
            self.intercept_ = np.array([0.0])
            return self

    monkeypatch.setattr(candidates, "LogisticRegression", ControlledEstimator)
    scope = _scope(Scope)
    protocol = _protocol(Protocol, Support, scope, class_minimums={0: 2, 1: 2},
                         config=Config(approved=True, C=1., tol=1e-4, max_iter=100))
    result = fit(protocol, scope, ((0.,), (.2,), (.8,), (1.,)), (0, 0, 1, 1), patient_group_refs=GROUPS)
    assert result.status.value == expected
    assert "synthetic training rows" not in repr(result)


def test_validation_changes_cannot_change_train_only_candidate_or_preprocessor_state():
    Status, Config, fit, fit_baseline, versions, Protocol, Scope, Support = _api()
    from safira.training.features import (FeatureKind, FeaturePolicy, FeatureSpec,
                                          build_feature_schema, fit_preprocessing, transform_rows)
    from safira.training.records import PreprocessingPolicy, TrainingSupportCriteria
    from safira.signals import SignalDimension, SignalResult, SignalSourceKey, SignalState
    scope = _scope(Scope)
    spec = FeatureSpec("entropy", "v1", "binary_predictive_entropy", SignalDimension.PREDICTION_UNCERTAINTY,
                       FeatureKind.NUMERIC, {}, required=True, state_indicators=False)
    policy = FeaturePolicy((spec,))
    rows = tuple((scope.source_key, (SignalResult(SignalSourceKey(*scope.source_key),
                         SignalDimension.PREDICTION_UNCERTAINTY, "entropy", "v1", {}, SignalState.AVAILABLE,
                         value, "binary_predictive_entropy", ("synthetic",), {}),)) for value in (.2, .4, .6, .8))
    preprocessing_policy = PreprocessingPolicy(numeric_imputation={"entropy": "none"},
                                               numeric_scaling={"entropy": "standard"},
                                               constant_features="keep", category_encoding="one_hot_seen_unseen")
    feature_protocol = Protocol("p", "v1", (scope,), {scope.source_key: TrainingSupportCriteria(4)},
                                {scope.source_key: ("entropy",)}, {scope.source_key: policy},
                                {scope.source_key: preprocessing_policy}, {})
    schema = build_feature_schema(feature_protocol, scope, rows)
    preprocess_state = fit_preprocessing(feature_protocol, schema, rows)
    matrix, targets = ((0.,), (.2,), (.8,), (1.,)), (0, 0, 1, 1)
    config = Config(approved=True, C=1., tol=1e-4, max_iter=100)
    protocol = _protocol(Protocol, Support, scope, class_minimums={0: 2, 1: 2}, config=config)
    first = fit(protocol, scope, matrix, targets, patient_group_refs=GROUPS)
    validation_record = SignalResult(SignalSourceKey(*scope.source_key), SignalDimension.PREDICTION_UNCERTAINTY,
                                     "entropy", "v1", {}, SignalState.AVAILABLE, .95,
                                     "binary_predictive_entropy", ("synthetic-validation",), {})
    validation_values = transform_rows(preprocess_state, schema,
                                       ((scope.source_key, (validation_record,)),))
    assert validation_values[0] != transform_rows(preprocess_state, schema, (rows[-1],))[0]
    second = fit(protocol, scope, matrix, targets, patient_group_refs=GROUPS)
    first_baseline = fit_baseline(protocol, scope, targets, patient_group_refs=GROUPS)
    second_baseline = fit_baseline(protocol, scope, tuple(targets), patient_group_refs=GROUPS)
    assert first == second
    assert first_baseline == second_baseline
    assert preprocess_state == fit_preprocessing(feature_protocol, schema, rows)


def test_unauthorized_validation_record_mutation_is_rejected_by_complete_service_gate(registered_collection):
    from dataclasses import replace
    from safira.training.exceptions import TrainingVerificationError
    from safira.training.records import TrainingProtocol, TrainingSupportCriteria
    from safira.training.service import SafetyTrainingService
    from tests.training_fixtures import SyntheticTrainingLedger, build_inputs, training_scope
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    _, dataset, signals, reference = build_inputs(registry, register)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())
    ledger.admit(dataset, signals, reference)
    scope = training_scope(registry, "training-model", "v1", "label-a")
    protocol = TrainingProtocol("p", "v1", (scope,), {scope.source_key: TrainingSupportCriteria(1)},
                                {scope.source_key: ()})
    service = SafetyTrainingService(registry, protocol, ledger)
    service.prepare(dataset, signals)
    changed = replace(dataset.development.validation[0], correctness_target=
                       1 - dataset.development.validation[0].correctness_target)
    changed_dataset = replace(dataset, development=replace(dataset.development, validation=(changed,)))
    from safira.training.records import TrainingInputCheck
    with pytest.raises(TrainingVerificationError):
        service.prepare(changed_dataset, signals)
