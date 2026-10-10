from dataclasses import dataclass, field
from typing import Any


@dataclass
class SafetyContext:
    """
    Internal Safira context for one patient and one predicted label.

    The context stores the patient, prediction, and model-related evidence
    that may be required by Safira's safety-signal modules.

    It is an internal runtime object and is not the final safety assessment.
    """

    patient_id: str
    label: str

    # Original patient input used for this prediction.
    patient_data: Any = None

    # Prediction produced by the clinical model.
    prediction: Any = None
    prediction_probability: float | None = None

    # Information about the patient input.
    input_metadata: dict[str, Any] = field(default_factory=dict)
    available_modalities: list[str] = field(default_factory=list)

    # Internal model representation used by methods such as OOD detection.
    feature_representation: Any = None

    # Additional model outputs that may support uncertainty estimation.
    repeated_outputs: list[Any] = field(default_factory=list)

    # Modality-specific outputs that may support agreement analysis.
    modality_outputs: dict[str, Any] = field(default_factory=dict)

    # Information describing the patient's source domain.
    domain_metadata: dict[str, Any] = field(default_factory=dict)

    # Model explanation output such as SHAP values or Grad-CAM maps.
    explanation: Any = None

    # Optional information about the prediction model.
    model_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Perform basic validation after context creation."""

        if not isinstance(self.patient_id, str) or not self.patient_id.strip():
            raise ValueError("patient_id cannot be empty.")

        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label cannot be empty.")

        if self.prediction_probability is not None:
            if not 0.0 <= self.prediction_probability <= 1.0:
                raise ValueError(
                    "prediction_probability must be between 0.0 and 1.0."
                )

    def evidence_availability(self) -> dict[str, bool]:
        """
        Report which major pieces of safety evidence are currently available.

        This describes the current SafetyContext, not the theoretical
        capabilities of the model adapter.
        """

        return {
            "patient_data": self.patient_data is not None,
            "prediction": self.prediction is not None,
            "prediction_probability": self.prediction_probability is not None,
            "feature_representation": self.feature_representation is not None,
            "repeated_outputs": bool(self.repeated_outputs),
            "modality_outputs": bool(self.modality_outputs),
            "domain_metadata": bool(self.domain_metadata),
            "explanation": self.explanation is not None,
        }