import pytest


def _api(preprocessing_policy=None):
    from safira.training.features import FeatureKind, FeaturePolicy, FeatureSpec, build_feature_schema
    from safira.training.records import (PreprocessingPolicy, TrainingProtocol,
                                         TrainingScope, TrainingSupportCriteria)
    from safira.signals import SignalDimension, SignalResult, SignalSourceKey, SignalState
    scope = TrainingScope("model", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "prep-v1")
    spec = FeatureSpec("entropy", "v1", "binary_predictive_entropy", SignalDimension.PREDICTION_UNCERTAINTY,
                       FeatureKind.NUMERIC, required=True, state_indicators=True,
                       allowed_nonvalue_states=(SignalState.MISSING.value, SignalState.UNAVAILABLE.value))
    feature_policy = FeaturePolicy((spec,))
    results = tuple(SignalResult(SignalSourceKey(*scope.source_key), SignalDimension.PREDICTION_UNCERTAINTY,
                                 "entropy", "v1", {}, state, value, "binary_predictive_entropy", ("test",), {},
                                 None if state is SignalState.AVAILABLE else "evidence_missing")
                    for state, value in ((SignalState.AVAILABLE, .2), (SignalState.MISSING, None),
                                         (SignalState.AVAILABLE, .8)))
    rows = tuple((scope.source_key, (result,)) for result in results)
    protocol = TrainingProtocol("p", "v1", (scope,), {scope.source_key: TrainingSupportCriteria(2)},
                                {scope.source_key: ("entropy",)}, {scope.source_key: feature_policy},
                                {} if preprocessing_policy is None else {scope.source_key: preprocessing_policy}, {})
    schema = build_feature_schema(protocol, scope, rows)
    from safira.training.features import fit_preprocessing, transform_rows
    return FeatureKind, PreprocessingPolicy, fit_preprocessing, transform_rows, scope, protocol, schema, rows


def _protocol_with(policy):
    from safira.training.records import TrainingProtocol, TrainingScope, TrainingSupportCriteria, FeatureKind
    from safira.training.features import FeaturePolicy, FeatureSpec
    from safira.signals import SignalDimension
    scope = TrainingScope("model", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "prep-v1")
    feature_policy = FeaturePolicy((FeatureSpec("entropy", "v1", "binary_predictive_entropy",
        SignalDimension.PREDICTION_UNCERTAINTY, FeatureKind.NUMERIC,
        required=True, state_indicators=True, allowed_nonvalue_states=("missing", "unavailable")),))
    return TrainingProtocol("p", "v1", (scope,), {scope.source_key: TrainingSupportCriteria(2)},
                            {scope.source_key: ("entropy",)}, {scope.source_key: feature_policy},
                            {scope.source_key: policy}, {})


def test_preprocessing_fits_median_and_state_indicators_on_training_only():
    from safira.training.records import PreprocessingPolicy
    (Kind, Policy, fit, transform, scope, protocol, schema, rows) = _api(
        PreprocessingPolicy(numeric_imputation={"entropy": "median"}, numeric_scaling={"entropy": "none"},
                           optional_all_missing={"entropy": "fail"}, constant_features="keep",
                           category_encoding="one_hot_seen_unseen"))
    state = fit(protocol, schema, rows)
    assert state.medians["entropy"] == .5
    assert transform(state, schema, rows) == ((.2, 1.0, 0.0, 0.0), (.5, 0.0, 1.0, 0.0),
                                               (.8, 1.0, 0.0, 0.0))
    changed_validation = ((scope.source_key, rows[-1][1]),)
    assert fit(protocol, schema, rows) == state
    assert transform(state, schema, changed_validation) == ((.8, 1.0, 0.0, 0.0),)


def test_preprocessing_rejects_unapproved_missing_states_and_all_missing_required_measurements():
    (Kind, Policy, fit, transform, scope, _, schema, rows) = _api()
    bad = ((scope.source_key, (rows[1][1][0],)),)
    protocol = _protocol_with(Policy(numeric_imputation={"entropy": "median"}, numeric_scaling={"entropy": "none"},
                                     optional_all_missing={"entropy": "fail"}, constant_features="keep",
                                     category_encoding="one_hot_seen_unseen"))
    with pytest.raises(ValueError):
        fit(protocol, schema, bad)
    all_missing = (bad[0], bad[0])
    with pytest.raises(ValueError, match="all_missing"):
        fit(protocol, schema, all_missing)


def test_preprocessing_approval_is_required_and_validation_cannot_refit_state():
    (Kind, Policy, fit, transform, scope, _, schema, rows) = _api()
    from safira.training.records import PreprocessingPolicy
    protocol = _protocol_with(PreprocessingPolicy(numeric_imputation={"entropy": "median"},
                                                  numeric_scaling={"entropy": "none"},
                                                  constant_features="keep",
                                                  category_encoding="one_hot_seen_unseen"))
    with pytest.raises(ValueError, match="approval"):
        fit(_api()[5], schema, rows)
    state = fit(protocol, schema, rows)
    values = transform(state, schema, rows)
    assert state.medians["entropy"] == .5
    assert values[1][0] == .5
    assert state.medians["entropy"] == .5


def test_optional_all_missing_feature_uses_approved_omit_policy_without_inventing_a_median():
    from safira.training.features import FeatureKind, FeaturePolicy, FeatureSpec, build_feature_schema
    from safira.training.records import PreprocessingPolicy, TrainingProtocol, TrainingScope, TrainingSupportCriteria
    from safira.signals import SignalDimension, SignalResult, SignalSourceKey, SignalState
    scope = TrainingScope("model", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "prep-v1")
    spec = FeatureSpec("entropy", "v1", "binary_predictive_entropy", SignalDimension.PREDICTION_UNCERTAINTY,
                       FeatureKind.NUMERIC, required=False, state_indicators=True, allowed_nonvalue_states=("missing",))
    policy = FeaturePolicy((spec,))
    rows = tuple((scope.source_key, (SignalResult(SignalSourceKey(*scope.source_key),
                         SignalDimension.PREDICTION_UNCERTAINTY, "entropy", "v1", {}, SignalState.MISSING,
                         None, "binary_predictive_entropy", ("synthetic",), {}, "evidence_missing"),))
                 for _ in range(2))
    preprocessing = PreprocessingPolicy(numeric_imputation={"entropy": "median"},
                                        numeric_scaling={"entropy": "none"},
                                        optional_all_missing={"entropy": "omit"}, constant_features="keep",
                                        category_encoding="one_hot_seen_unseen")
    protocol = TrainingProtocol("p", "v1", (scope,), {scope.source_key: TrainingSupportCriteria(2)},
                                {scope.source_key: ("entropy",)}, {scope.source_key: policy},
                                {scope.source_key: preprocessing}, {})
    schema = build_feature_schema(protocol, scope, rows)
    from safira.training.features import fit_preprocessing, transform_rows
    state = fit_preprocessing(protocol, schema, rows)
    assert "entropy" not in state.medians
    assert state.omissions["entropy"] == "optional_all_missing_training"
    assert transform_rows(state, schema, rows) == ((), ())


def test_frozen_preprocessing_state_rejects_incompatible_feature_schema():
    from safira.training.features import FeatureKind, FeaturePolicy, FeatureSpec, build_feature_schema, fit_preprocessing, transform_rows
    from safira.training.records import PreprocessingPolicy, TrainingProtocol, TrainingScope, TrainingSupportCriteria
    from safira.signals import SignalDimension, SignalResult, SignalSourceKey, SignalState
    scope = TrainingScope("model", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "prep-v1")
    spec = FeatureSpec("entropy", "v1", "binary_predictive_entropy", SignalDimension.PREDICTION_UNCERTAINTY,
                       FeatureKind.NUMERIC, required=True, state_indicators=False)
    other = FeatureSpec("entropy", "v2", "different_semantics", SignalDimension.PREDICTION_UNCERTAINTY,
                        FeatureKind.NUMERIC, required=True, state_indicators=False)
    policy = FeaturePolicy((spec,))
    other_policy = FeaturePolicy((other,))
    rows = ((scope.source_key, (SignalResult(SignalSourceKey(*scope.source_key),
        SignalDimension.PREDICTION_UNCERTAINTY, "entropy", "v1", {}, SignalState.AVAILABLE, .5,
        "binary_predictive_entropy", ("synthetic",), {}),)),)
    preprocess = PreprocessingPolicy(numeric_imputation={"entropy": "none"}, numeric_scaling={"entropy": "none"},
                                     constant_features="keep", category_encoding="one_hot_seen_unseen")
    protocol = TrainingProtocol("p", "v1", (scope,), {scope.source_key: TrainingSupportCriteria(1)},
                                {scope.source_key: ("entropy",)}, {scope.source_key: policy},
                                {scope.source_key: preprocess}, {})
    incompatible = TrainingProtocol("p", "v1", (scope,), {scope.source_key: TrainingSupportCriteria(1)},
                                    {scope.source_key: ("entropy",)}, {scope.source_key: other_policy},
                                    {scope.source_key: preprocess}, {})
    schema = build_feature_schema(protocol, scope, rows)
    incompatible_schema = build_feature_schema(incompatible, scope,
        ((scope.source_key, (SignalResult(SignalSourceKey(*scope.source_key),
          SignalDimension.PREDICTION_UNCERTAINTY, "entropy", "v2", {}, SignalState.AVAILABLE, .5,
          "different_semantics", ("synthetic",), {}),)),))
    state = fit_preprocessing(protocol, schema, rows)
    with pytest.raises(ValueError, match="schema_mismatch"):
        transform_rows(state, incompatible_schema, rows)
