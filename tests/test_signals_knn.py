import math

import pytest

from safira.signals.exceptions import SignalCompatibilityError, SignalInputError
from safira.signals.records import SignalMethodConfig, SignalSourceKey
from safira.signals.reference import (
    ReferenceCompatibilityKey,
    ReferenceFitConfig,
    ReferenceObservation,
    apply_knn_reference,
    fit_knn_reference,
    knn_distance,
)


def test_kth_euclidean_distance_is_raw_and_uses_declared_k_and_metric():
    value = knn_distance((0.0, 0.0), ((1.0, 0.0), (0.0, 2.0), (3.0, 0.0)), k=2, metric="euclidean")
    assert value == pytest.approx(2.0)


@pytest.mark.parametrize("query,reference,k,metric", [
    ((0.0,), ((1.0, 2.0),), 1, "euclidean"),
    ((0.0,), ((1.0,),), 0, "euclidean"),
    ((0.0,), ((1.0,),), 1, "cosine"),
    ((float("nan"),), ((1.0,),), 1, "euclidean"),
    ((0.0,), ((float("inf"),),), 1, "euclidean"),
    ((), ((1.0,),), 1, "euclidean"),
])
def test_knn_rejects_invalid_dimensions_nonfinite_values_k_and_unapproved_metrics(query, reference, k, metric):
    with pytest.raises(SignalInputError):
        knn_distance(query, reference, k=k, metric=metric)


def test_final_reference_is_deeply_immutable_and_application_checks_exact_scope():
    source = SignalSourceKey("m", "v1", "l")
    key = ReferenceCompatibilityKey(source, "knn_distance", "v1", {"k": 1, "metric": "euclidean"},
                                   "repr-schema", "prep", "d", "p", "1", "manifest", "cohort")
    config = ReferenceFitConfig(key, SignalMethodConfig("knn_distance", "v1", {"k": 1, "metric": "euclidean"}),
                                2, "seed")
    vector = [0.0, 0.0]
    rows = (ReferenceObservation("r1", source, "g1", "repr-schema", "prep", vector, evidence_ref="ev-r1"),
            ReferenceObservation("r2", source, "g2", "repr-schema", "prep", [2.0, 0.0], evidence_ref="ev-r2"))
    state = fit_knn_reference(rows, config)
    vector[0] = 100.0
    result = apply_knn_reference(state, (1.0, 0.0), key, query_evidence_ref="query-ev")
    assert result.value == pytest.approx(1.0)
    assert math.isfinite(result.value)
    assert "query-ev" in result.evidence_refs
    incompatible = ReferenceCompatibilityKey(source, "knn_distance", "v1", {"k": 1, "metric": "euclidean"},
                                             "repr-schema", "new-prep", "d", "p", "1", "manifest", "cohort")
    with pytest.raises(SignalCompatibilityError):
        apply_knn_reference(state, (1.0, 0.0), incompatible)


def test_insufficient_reference_support_is_explicit_not_zero():
    with pytest.raises(SignalInputError):
        knn_distance((0.0,), (), k=1, metric="euclidean")


def test_empty_final_training_reference_is_insufficient_and_missing_state_is_not_ready():
    source = SignalSourceKey("m", "v1", "l")
    key = ReferenceCompatibilityKey(source, "knn_distance", "v1", {"k": 1, "metric": "euclidean"},
                                    "schema", "prep", "d", "p", "1", "manifest", "cohort")
    config = ReferenceFitConfig(key, SignalMethodConfig("knn_distance", "v1", {"k": 1, "metric": "euclidean"}),
                                2, "seed")
    state = fit_knn_reference((), config)
    assert state.status == "insufficient_evidence"
    assert apply_knn_reference(None, (0.0,), key).state == "not_ready"
