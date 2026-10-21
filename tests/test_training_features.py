from dataclasses import FrozenInstanceError

import pytest


def _imports():
    from safira.training.features import (
        FeatureKind, FeaturePolicy, FeatureSpec, FrozenFeatureSchema,
        build_feature_schema, encode_rows,
    )
    from safira.training.records import TrainingScope
    from safira.training.records import TrainingProtocol, TrainingSupportCriteria
    from safira.signals import SignalDimension, SignalResult, SignalSourceKey, SignalState

    return (FeatureKind, FeaturePolicy, FeatureSpec, FrozenFeatureSchema,
            build_feature_schema, encode_rows, TrainingScope, SignalDimension,
            SignalResult, SignalSourceKey, SignalState, TrainingProtocol, TrainingSupportCriteria)


def _scope(TrainingScope):
    return TrainingScope("model", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "prep-v1")


def _protocol(Protocol, Support, scope, policy):
    return Protocol("feature-test", "v1", (scope,), {scope.source_key: Support(1)},
                    {scope.source_key: ()}, {scope.source_key: policy})


def _signal(SignalResult, SignalSourceKey, SignalDimension, SignalState, *, method="entropy", version="v1",
            meaning="binary_predictive_entropy", state=None, value=0.5):
    state = state or SignalState.AVAILABLE
    return SignalResult(SignalSourceKey("model", "v1", "label"), SignalDimension.PREDICTION_UNCERTAINTY,
                        method, version, {"base": "natural"}, state, value, meaning,
                        ("synthetic",), {"method": "synthetic"},
                        None if state is SignalState.AVAILABLE else "evidence_missing")


def test_schema_is_ordered_exact_scope_and_only_admits_declared_signal_semantics():
    (FeatureKind, FeaturePolicy, FeatureSpec, FrozenFeatureSchema, build_schema,
     encode_rows, TrainingScope, Dimension, Result, SourceKey, State, Protocol, Support) = _imports()
    scope = _scope(TrainingScope)
    policy = FeaturePolicy((
        FeatureSpec("entropy", "v1", "binary_predictive_entropy", Dimension.PREDICTION_UNCERTAINTY,
                   FeatureKind.NUMERIC, {"base": "natural"}, required=True, state_indicators=True,
                   allowed_nonvalue_states=("missing", "unavailable")),
        FeatureSpec("domain", "v2", "domain_familiarity", Dimension.DOMAIN_FAMILIARITY,
                   FeatureKind.SEEN_UNSEEN, {}, required=False, state_indicators=False),
    ), omitted_dimensions={"explanation_reliability": "no_numeric_v1_method"})
    row = (scope.source_key, (
        _signal(Result, SourceKey, Dimension, State),
        Result(SourceKey(*scope.source_key), Dimension.DOMAIN_FAMILIARITY, "domain", "v2", {}, State.AVAILABLE,
               "seen", "domain_familiarity", ("synthetic",), {"category": "restricted"}),
        Result(SourceKey(*scope.source_key), Dimension.EXPLANATION_RELIABILITY, "explanation_metadata", "v1", {},
               State.AVAILABLE, {"method": "shap"}, "metadata_only", ("synthetic",), {}),
    ))
    schema = build_schema(_protocol(Protocol, Support, scope, policy), scope, (row,))
    matrix, state_rows = encode_rows(schema, (row,))
    assert schema.columns[0].method_id == "entropy"
    assert schema.columns[4].method_id == "domain"
    assert matrix == ((0.5, 1.0, 0.0, 0.0, 1.0, 0.0),)
    assert state_rows == (("available", "available"),)
    assert schema.omitted_dimensions["explanation_reliability"] == "no_numeric_v1_method"
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        schema.columns = ()
    with pytest.raises(ValueError, match="feature"):
        build_schema(_protocol(Protocol, Support, scope, policy), scope,
                     ((("other", "v1", "label"), row[1]),))


def test_schema_rejects_unapproved_semantics_nonfinite_values_and_invalid_states():
    (FeatureKind, FeaturePolicy, FeatureSpec, _, build_schema, encode_rows,
     TrainingScope, Dimension, Result, SourceKey, State, Protocol, Support) = _imports()
    scope = _scope(TrainingScope)
    policy = FeaturePolicy((FeatureSpec("entropy", "v1", "binary_predictive_entropy",
                                       Dimension.PREDICTION_UNCERTAINTY, FeatureKind.NUMERIC,
                                       {"base": "natural"}, required=True, state_indicators=False),))
    wrong = _signal(Result, SourceKey, Dimension, State, meaning="different_meaning")
    with pytest.raises(ValueError, match="feature"):
        build_schema(_protocol(Protocol, Support, scope, policy), scope, ((scope.source_key, (wrong,)),))
    stale_version = Result(SourceKey(*scope.source_key), Dimension.PREDICTION_UNCERTAINTY, "entropy", "v9",
                           {"base": "natural"}, State.AVAILABLE, .5, "binary_predictive_entropy", (), {})
    with pytest.raises(ValueError, match="feature"):
        build_schema(_protocol(Protocol, Support, scope, policy), scope,
                     ((scope.source_key, (stale_version,)),))
    with pytest.raises(ValueError):
        _signal(Result, SourceKey, Dimension, State, value=float("inf"))
    invalid = _signal(Result, SourceKey, Dimension, State, state=State.INVALID, value=None)
    with pytest.raises(ValueError, match="feature"):
        build_schema(_protocol(Protocol, Support, scope, policy), scope, ((scope.source_key, (invalid,)),))


def test_optional_unsupported_dimension_is_omitted_with_reason_and_no_primary_or_explanation_predictor():
    (FeatureKind, FeaturePolicy, FeatureSpec, _, build_schema, encode_rows,
     TrainingScope, Dimension, Result, SourceKey, State, Protocol, Support) = _imports()
    scope = _scope(TrainingScope)
    policy = FeaturePolicy((FeatureSpec("entropy", "v1", "binary_predictive_entropy",
                                       Dimension.PREDICTION_UNCERTAINTY, FeatureKind.NUMERIC,
                                       {"base": "natural"}, required=True, state_indicators=False),),
                           omitted_dimensions={"distribution_conformity_ood": "unsupported_for_source"})
    row = (_signal(Result, SourceKey, Dimension, State), Result(SourceKey(*scope.source_key),
           Dimension.DISTRIBUTION_CONFORMITY, "knn", "v1", {}, State.UNSUPPORTED, None,
           "training_reference_distance", (), {}, "evidence_unsupported"))
    schema = build_schema(_protocol(Protocol, Support, scope, policy), scope, ((scope.source_key, row),))
    assert schema.omitted_dimensions["distribution_conformity_ood"] == "unsupported_for_source"
    assert all("primary" not in column.name and "explanation" not in column.name for column in schema.columns)
    assert encode_rows(schema, ((scope.source_key, row),))[0] == ((0.5,),)


@pytest.mark.parametrize("state,reason", [
    ("unsupported", "evidence_unsupported"), ("missing", "evidence_missing"),
    ("unavailable", "evidence_unavailable"), ("insufficient_evidence", "reference_support_insufficient"),
])
def test_nonvalue_states_remain_distinct_and_are_not_fabricated_as_measurements(state, reason):
    (FeatureKind, FeaturePolicy, FeatureSpec, _, build_schema, encode_rows,
     TrainingScope, Dimension, Result, SourceKey, State, Protocol, Support) = _imports()
    scope = _scope(TrainingScope)
    allowed = ("unsupported", "missing", "unavailable", "insufficient_evidence")
    spec = FeatureSpec("entropy", "v1", "binary_predictive_entropy", Dimension.PREDICTION_UNCERTAINTY,
                       FeatureKind.NUMERIC, {"base": "natural"}, required=False, state_indicators=True,
                       allowed_nonvalue_states=allowed)
    result = Result(SourceKey(*scope.source_key), Dimension.PREDICTION_UNCERTAINTY, "entropy", "v1",
                    {"base": "natural"}, State(state), None, "binary_predictive_entropy", ("synthetic",), {}, reason)
    policy = FeaturePolicy((spec,))
    schema = build_schema(_protocol(Protocol, Support, scope, policy), scope, ((scope.source_key, (result,)),))
    matrix, states = encode_rows(schema, ((scope.source_key, (result,)),))
    assert matrix[0][0] is None
    assert states == ((state,),)
    assert matrix[0][1:] == tuple(float(candidate == state) for candidate in
                                  ("available", "unsupported", "missing", "unavailable", "insufficient_evidence"))


def test_not_ready_evidence_is_rejected_and_unapproved_omission_reason_is_rejected():
    (FeatureKind, FeaturePolicy, FeatureSpec, _, build_schema, encode_rows,
     TrainingScope, Dimension, Result, SourceKey, State, Protocol, Support) = _imports()
    scope = _scope(TrainingScope)
    with pytest.raises(ValueError):
        FeaturePolicy((), omitted_dimensions={"distribution_conformity_ood": "patient-specific explanation"})
    spec = FeatureSpec("entropy", "v1", "binary_predictive_entropy", Dimension.PREDICTION_UNCERTAINTY,
                       FeatureKind.NUMERIC, {"base": "natural"}, required=False, state_indicators=True,
                       allowed_nonvalue_states=("missing",))
    result = Result(SourceKey(*scope.source_key), Dimension.PREDICTION_UNCERTAINTY, "entropy", "v1",
                    {"base": "natural"}, State.NOT_READY, None, "binary_predictive_entropy", ("synthetic",), {},
                    "reference_not_ready")
    with pytest.raises(ValueError, match="feature_state"):
        policy = FeaturePolicy((spec,))
        build_schema(_protocol(Protocol, Support, scope, policy), scope, ((scope.source_key, (result,)),))


def test_schema_rejects_reordered_or_forged_columns():
    from dataclasses import replace
    (FeatureKind, FeaturePolicy, FeatureSpec, _, build_schema, encode_rows,
     TrainingScope, Dimension, Result, SourceKey, State, Protocol, Support) = _imports()
    scope = _scope(TrainingScope)
    policy = FeaturePolicy((FeatureSpec("entropy", "v1", "binary_predictive_entropy",
        Dimension.PREDICTION_UNCERTAINTY, FeatureKind.NUMERIC, {"base": "natural"}, required=True,
        state_indicators=False),
        FeatureSpec("domain", "v1", "domain_familiarity", Dimension.DOMAIN_FAMILIARITY,
                    FeatureKind.SEEN_UNSEEN, required=True, state_indicators=False)))
    row = (_signal(Result, SourceKey, Dimension, State), Result(SourceKey(*scope.source_key),
        Dimension.DOMAIN_FAMILIARITY, "domain", "v1", {}, State.AVAILABLE, "seen",
        "domain_familiarity", (), {}))
    schema = build_schema(_protocol(Protocol, Support, scope, policy), scope, ((scope.source_key, row),))
    with pytest.raises(ValueError, match="feature_schema_columns"):
        replace(schema, columns=tuple(reversed(schema.columns)))
