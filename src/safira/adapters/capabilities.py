from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AdapterCapabilities:
    """
    Describes the optional evidence that a Safira model adapter
    is capable of providing.

    Prediction itself is mandatory for every valid ModelAdapter,
    so it is not represented as an optional capability.
    """

    prediction_probability: bool = False
    feature_representation: bool = False
    repeated_outputs: bool = False
    modality_outputs: bool = False
    domain_metadata: bool = False
    explanation: bool = False
    input_metadata: bool = False
    available_modalities: bool = False

    def to_dict(self) -> dict[str, bool]:
        """Return the capabilities as a dictionary."""

        return asdict(self)

    def supports(self, capability: str) -> bool:
        """
        Check whether a named capability is supported.

        Raises:
            ValueError: If the requested capability name is unknown.
        """

        capabilities = self.to_dict()

        if capability not in capabilities:
            raise ValueError(
                f"Unknown adapter capability: {capability}"
            )

        return capabilities[capability]