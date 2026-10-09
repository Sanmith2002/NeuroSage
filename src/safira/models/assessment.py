from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class SafetyStatus(str, Enum):
    """Possible final Safira safety decisions."""

    TRUST = "TRUST"
    CAUTION = "CAUTION"
    DEFER = "DEFER"


@dataclass
class SafetyAssessment:
    """
    Represents Safira's safety assessment for one patient and one label.

    Example:
        Patient P001 + AD prediction -> one SafetyAssessment
    """

    patient_id: str
    label: str

    prediction_probability: float | None = None

    signal_scores: dict[str, float | None] = field(default_factory=dict)

    reliability_score: float | None = None
    status: SafetyStatus | None = None

    reasons: list[str] = field(default_factory=list)
    recommended_action: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Perform basic validation after object creation."""

        if not self.patient_id.strip():
            raise ValueError("patient_id cannot be empty.")

        if not self.label.strip():
            raise ValueError("label cannot be empty.")

        if self.prediction_probability is not None:
            if not 0.0 <= self.prediction_probability <= 1.0:
                raise ValueError(
                    "prediction_probability must be between 0.0 and 1.0."
                )

        if self.reliability_score is not None:
            if not 0.0 <= self.reliability_score <= 1.0:
                raise ValueError(
                    "reliability_score must be between 0.0 and 1.0."
                )

    def to_dict(self) -> dict[str, Any]:
        """Convert the assessment into a dictionary."""

        result = asdict(self)

        if self.status is not None:
            result["status"] = self.status.value

        return result