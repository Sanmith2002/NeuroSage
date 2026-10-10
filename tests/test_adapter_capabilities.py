from dataclasses import FrozenInstanceError

import pytest

from safira import AdapterCapabilities


def test_default_capabilities_are_disabled():
    capabilities = AdapterCapabilities()

    assert capabilities.prediction_probability is False
    assert capabilities.feature_representation is False
    assert capabilities.repeated_outputs is False
    assert capabilities.modality_outputs is False
    assert capabilities.domain_metadata is False
    assert capabilities.explanation is False
    assert capabilities.input_metadata is False
    assert capabilities.available_modalities is False


def test_create_custom_capabilities():
    capabilities = AdapterCapabilities(
        prediction_probability=True,
        feature_representation=True,
        explanation=True,
    )

    assert capabilities.prediction_probability is True
    assert capabilities.feature_representation is True
    assert capabilities.explanation is True

    assert capabilities.repeated_outputs is False
    assert capabilities.modality_outputs is False


def test_capabilities_to_dict():
    capabilities = AdapterCapabilities(
        prediction_probability=True,
        domain_metadata=True,
    )

    result = capabilities.to_dict()

    assert result["prediction_probability"] is True
    assert result["domain_metadata"] is True
    assert result["explanation"] is False


def test_supports_enabled_capability():
    capabilities = AdapterCapabilities(
        feature_representation=True,
    )

    assert capabilities.supports(
        "feature_representation"
    ) is True


def test_supports_disabled_capability():
    capabilities = AdapterCapabilities(
        modality_outputs=False,
    )

    assert capabilities.supports(
        "modality_outputs"
    ) is False


def test_unknown_capability_raises_error():
    capabilities = AdapterCapabilities()

    with pytest.raises(
        ValueError,
        match="Unknown adapter capability",
    ):
        capabilities.supports("magic_output")


def test_capabilities_are_immutable():
    capabilities = AdapterCapabilities(
        explanation=True,
    )

    with pytest.raises(FrozenInstanceError):
        capabilities.explanation = False