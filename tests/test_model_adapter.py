import pytest

from safira import (
    AdapterCapabilities,
    CapabilityNotSupportedError,
    ModelAdapter,
)


class MinimalAdapter(ModelAdapter):

    def predict(
        self,
        patient_data,
        label,
    ):
        return 1


class ProbabilityAdapter(ModelAdapter):

    def __init__(self):
        super().__init__(
            AdapterCapabilities(
                prediction_probability=True
            )
        )

    def predict(
        self,
        patient_data,
        label,
    ):
        return 1

    def predict_probability(
        self,
        patient_data,
        label,
    ):
        return 0.91


class BrokenFeatureAdapter(ModelAdapter):

    def __init__(self):
        super().__init__(
            AdapterCapabilities(
                feature_representation=True
            )
        )

    def predict(
        self,
        patient_data,
        label,
    ):
        return 1


def test_model_adapter_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        ModelAdapter()


def test_minimal_adapter_prediction():
    adapter = MinimalAdapter()

    result = adapter.predict(
        {"example": 123},
        "AD",
    )

    assert result == 1


def test_default_optional_capabilities_are_disabled():
    adapter = MinimalAdapter()

    assert adapter.supports(
        "prediction_probability"
    ) is False

    assert adapter.supports(
        "feature_representation"
    ) is False

    assert adapter.supports(
        "explanation"
    ) is False


def test_unsupported_capability_raises_error():
    adapter = MinimalAdapter()

    with pytest.raises(
        CapabilityNotSupportedError,
        match="feature_representation",
    ):
        adapter.extract_features(
            {"example": 123},
            "AD",
        )


def test_supported_probability_capability():
    adapter = ProbabilityAdapter()

    assert adapter.supports(
        "prediction_probability"
    ) is True

    assert adapter.predict_probability(
        {"example": 123},
        "AD",
    ) == 0.91


def test_declared_capability_requires_implementation():
    adapter = BrokenFeatureAdapter()

    with pytest.raises(
        NotImplementedError,
        match="extract_features",
    ):
        adapter.extract_features(
            {"example": 123},
            "AD",
        )


def test_invalid_capabilities_type():
    with pytest.raises(
        TypeError,
        match="AdapterCapabilities",
    ):

        class InvalidAdapter(ModelAdapter):

            def __init__(self):
                super().__init__(
                    capabilities="invalid"
                )

            def predict(
                self,
                patient_data,
                label,
            ):
                return 1

        InvalidAdapter()


def test_capabilities_property_returns_capabilities():
    adapter = ProbabilityAdapter()

    assert isinstance(
        adapter.capabilities,
        AdapterCapabilities,
    )


def test_unknown_capability_name_raises_error():
    adapter = MinimalAdapter()

    with pytest.raises(
        ValueError,
        match="Unknown adapter capability",
    ):
        adapter.supports(
            "magic_feature"
        )