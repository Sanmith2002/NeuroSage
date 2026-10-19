from dataclasses import replace

import pytest

from safira.signals.exceptions import SignalCompatibilityError
from safira.signals.records import SignalMethodConfig, SignalSourceKey
from safira.signals.reference import (
    ReferenceCompatibilityKey,
    ReferenceFitConfig,
    ReferenceObservation,
    _assert_reference_compatible,
    fit_knn_reference,
)


def setup_reference():
    key = ReferenceCompatibilityKey(
        SignalSourceKey("classifier-a", "v1", "label-a"),
        "knn_distance", "v1", {"k": 1, "metric": "euclidean"},
        "schema-a", "preprocess-a", "dataset-a", "protocol-a", "p1", "manifest-a",
    )
    config = ReferenceFitConfig(
        key,
        SignalMethodConfig("knn_distance", "v1", {"k": 1, "metric": "euclidean"}),
        fold_count=2,
        seed="approved-seed",
    )
    rows = (
        ReferenceObservation("r1", key.source_key, "patient-1", "schema-a", "preprocess-a", (0.0, 0.0), evidence_ref="ev-r1"),
        ReferenceObservation("r2", key.source_key, "patient-2", "schema-a", "preprocess-a", (1.0, 0.0), evidence_ref="ev-r2"),
    )
    return key, config, rows


def test_fitted_reference_accepts_only_exact_model_version_label_and_preprocessing():
    key, config, rows = setup_reference()
    state = fit_knn_reference(rows, config)
    _assert_reference_compatible(state, key)
    for changes in (
        {"source_key": SignalSourceKey("classifier-b", "v1", "label-a")},
        {"source_key": SignalSourceKey("classifier-a", "v2", "label-a")},
        {"source_key": SignalSourceKey("classifier-a", "v1", "label-b")},
        {"preprocessing_identity": "preprocess-b"},
        {"evidence_schema": "schema-b"},
        {"dataset_id": "dataset-b"},
        {"manifest_reference": "manifest-b"},
    ):
        with pytest.raises(SignalCompatibilityError):
            _assert_reference_compatible(state, replace(key, **changes))


def test_reference_configuration_and_state_are_detached_and_immutable():
    key, config, rows = setup_reference()
    parameters = {"k": 1, "metric": "euclidean"}
    method = SignalMethodConfig("knn_distance", "v1", parameters)
    params_key = ReferenceCompatibilityKey(
        key.source_key, key.method_id, key.method_version, parameters,
        key.evidence_schema, key.preprocessing_identity, key.dataset_id,
        key.protocol_id, key.protocol_version, key.manifest_reference,
    )
    fit_config = ReferenceFitConfig(params_key, method, 2, "approved-seed")
    parameters["k"] = 99
    state = fit_knn_reference(rows, fit_config)
    assert state.compatibility_key.parameters["k"] == 1
    with pytest.raises(TypeError):
        state.compatibility_key.parameters["k"] = 3


def test_method_version_parameters_and_reference_cohort_are_compatibility_fields():
    key, config, rows = setup_reference()
    state = fit_knn_reference(rows, config)
    for changes in (
        {"method_version": "v2"},
        {"parameters": {"k": 2, "metric": "euclidean"}},
        {"reference_cohort": "cohort-other"},
    ):
        with pytest.raises(SignalCompatibilityError):
            _assert_reference_compatible(state, replace(key, **changes))
