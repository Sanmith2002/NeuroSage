from abc import ABC, abstractmethod
from typing import Any

from safira.adapters.capabilities import AdapterCapabilities
from safira.adapters.exceptions import CapabilityNotSupportedError


class ModelAdapter(ABC):
    """
    Standard interface between Safira and a clinical prediction model.

    Every Safira-compatible adapter must implement prediction.

    Additional evidence sources such as probabilities, feature
    representations, repeated outputs, modality outputs, explanations,
    and metadata are optional and declared through AdapterCapabilities.
    """

    def __init__(
        self,
        capabilities: AdapterCapabilities | None = None,
    ) -> None:
        if capabilities is None:
            capabilities = AdapterCapabilities()

        if not isinstance(capabilities, AdapterCapabilities):
            raise TypeError(
                "capabilities must be an AdapterCapabilities instance."
            )

        self._capabilities = capabilities

    @property
    def capabilities(self) -> AdapterCapabilities:
        """Return the optional capabilities supported by this adapter."""

        return self._capabilities

    def supports(self, capability: str) -> bool:
        """Check whether the adapter supports a named capability."""

        return self.capabilities.supports(capability)

    @abstractmethod
    def predict(
        self,
        patient_data: Any,
        label: str,
    ) -> Any:
        """
        Produce the model prediction for the requested label.

        This method is mandatory for every Safira adapter.
        """

        raise NotImplementedError

    def predict_probability(
        self,
        patient_data: Any,
        label: str,
    ) -> float:
        """
        Return the model probability for the requested label.
        """

        self._require_capability("prediction_probability")

        raise NotImplementedError(
            self._missing_implementation_message(
                "prediction_probability",
                "predict_probability",
            )
        )

    def extract_features(
        self,
        patient_data: Any,
        label: str,
    ) -> Any:
        """
        Return a model feature representation for the patient.

        This may later be used for methods such as OOD detection.
        """

        self._require_capability("feature_representation")

        raise NotImplementedError(
            self._missing_implementation_message(
                "feature_representation",
                "extract_features",
            )
        )

    def get_repeated_outputs(
        self,
        patient_data: Any,
        label: str,
    ) -> list[Any]:
        """
        Return repeated model outputs for uncertainty analysis.
        """

        self._require_capability("repeated_outputs")

        raise NotImplementedError(
            self._missing_implementation_message(
                "repeated_outputs",
                "get_repeated_outputs",
            )
        )

    def get_modality_outputs(
        self,
        patient_data: Any,
        label: str,
    ) -> dict[str, Any]:
        """
        Return modality-specific model outputs for the requested label.
        """

        self._require_capability("modality_outputs")

        raise NotImplementedError(
            self._missing_implementation_message(
                "modality_outputs",
                "get_modality_outputs",
            )
        )

    def get_domain_metadata(
        self,
        patient_data: Any,
    ) -> dict[str, Any]:
        """
        Return information describing the patient's source domain.
        """

        self._require_capability("domain_metadata")

        raise NotImplementedError(
            self._missing_implementation_message(
                "domain_metadata",
                "get_domain_metadata",
            )
        )

    def explain(
        self,
        patient_data: Any,
        label: str,
    ) -> Any:
        """
        Return model explanation information for the requested label.
        """

        self._require_capability("explanation")

        raise NotImplementedError(
            self._missing_implementation_message(
                "explanation",
                "explain",
            )
        )

    def get_input_metadata(
        self,
        patient_data: Any,
    ) -> dict[str, Any]:
        """
        Return metadata describing the current patient input.
        """

        self._require_capability("input_metadata")

        raise NotImplementedError(
            self._missing_implementation_message(
                "input_metadata",
                "get_input_metadata",
            )
        )

    def get_available_modalities(
        self,
        patient_data: Any,
    ) -> list[str]:
        """
        Return the modalities available for the current patient.
        """

        self._require_capability("available_modalities")

        raise NotImplementedError(
            self._missing_implementation_message(
                "available_modalities",
                "get_available_modalities",
            )
        )

    def _require_capability(
        self,
        capability: str,
    ) -> None:
        """
        Ensure that an optional capability is supported.
        """

        if not self.supports(capability):
            raise CapabilityNotSupportedError(
                f"{self.__class__.__name__} does not support "
                f"adapter capability '{capability}'."
            )

    def _missing_implementation_message(
        self,
        capability: str,
        method_name: str,
    ) -> str:
        """
        Build an error message for a capability that was declared
        as supported but whose method was not implemented.
        """

        return (
            f"{self.__class__.__name__} declares support for "
            f"'{capability}', but '{method_name}()' was not implemented."
        )