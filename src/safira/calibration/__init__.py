"""Feature 006 independent calibration research interfaces.

The public boundary fits and validates exact-scope calibrator artifacts only.
It intentionally provides no calibrated per-patient application API.
"""

from safira.calibration.exceptions import (
    CalibrationCompatibilityError, CalibrationError, CalibrationInputError,
    CalibrationVerificationError,
)
from safira.calibration.records import (
    CalibratorArtifact, CalibrationOutcome, CalibrationProtocol, CalibrationStatus,
)
from safira.calibration.artifacts import export_calibrator_artifact, validate_calibrator_artifact
from safira.calibration.service import CalibrationService
from safira.calibration.verification import CalibrationInputVerifier

__all__ = [
    "CalibrationProtocol", "CalibrationStatus", "CalibrationOutcome", "CalibratorArtifact",
    "CalibrationInputVerifier", "CalibrationService", "export_calibrator_artifact",
    "validate_calibrator_artifact",
    "CalibrationError", "CalibrationInputError", "CalibrationVerificationError",
    "CalibrationCompatibilityError",
]
