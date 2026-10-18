"""T002: immutable contracts and explicit signal states."""

from dataclasses import FrozenInstanceError

import pytest

from safira.signals.records import (
    FittedStateReference, SignalDimension, SignalMethodConfig, SignalProtocol,
    SignalResult, SignalSourceKey, SignalState,
)


def test_configuration_and_protocol_detach_nested_values():
    parameters = {"log_base": 2, "nested": {"items": [1, 2]}}
    config = SignalMethodConfig("bernoulli_entropy", "v1", parameters)
    protocol = SignalProtocol(
        "study-synthetic", "v1", (SignalSourceKey("model", "v2", "label"),),
        {config.method_id: config}, {"data_sufficiency": ("modality_outputs",)},
    )
    parameters["nested"]["items"].append(3)
    assert config.parameters["nested"]["items"] == (1, 2)
    assert protocol.method_configs[config.method_id] == config
    with pytest.raises(TypeError):
        config.parameters["nested"]["extra"] = True
    with pytest.raises((FrozenInstanceError, AttributeError)):
        config.method_version = "v2"


def test_signal_result_has_detached_value_and_serialization():
    value = {"pairs": [{"modalities": ["a", "b"], "divergence": 0.2}]}
    result = SignalResult(
        SignalSourceKey("model", "v1", "label"), SignalDimension.MODALITY_AGREEMENT,
        "modality_jsd", "v1", {"log_base": 2}, SignalState.AVAILABLE, value,
        "Pairwise Bernoulli JSD in bits.", ("modality_outputs",),
        {"source_assurance": "verified_live_binding"},
    )
    value["pairs"][0]["divergence"] = 0.9
    emitted = result.to_dict()
    emitted["value"]["pairs"][0]["divergence"] = 0.8
    assert result.value["pairs"][0]["divergence"] == 0.2
    assert result.to_dict()["value"]["pairs"][0]["divergence"] == 0.2
    assert result.method_parameters == {"log_base": 2}
    assert result.source_key.to_tuple() == ("model", "v1", "label")


def test_all_seven_signal_states_are_declared():
    assert {state.value for state in SignalState} == {
        "available", "unsupported", "missing", "unavailable", "invalid",
        "insufficient_evidence", "not_ready",
    }


def test_fitted_state_reference_is_immutable_and_exactly_scoped():
    metadata = {"representation_schema": {"shape": [2]}}
    state = FittedStateReference(
        "state-ref", SignalSourceKey("model", "v1", "label"), "knn", "v1",
        "dataset", "protocol", "protocol-v1", "manifest", "preprocessing-v1",
        metadata,
    )
    metadata["representation_schema"]["shape"].append(3)
    assert state.metadata["representation_schema"]["shape"] == (2,)
    assert state.source_key.to_tuple() == ("model", "v1", "label")
