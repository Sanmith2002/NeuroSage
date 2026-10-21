"""Stable, privacy-safe errors shared by Feature 006 admission paths."""


class CalibrationError(Exception):
    """Base error whose message contains only a controlled reason code."""

    def __init__(self, reason_code: str):
        if reason_code not in {
            "input_invalid", "verification_required", "verification_rejected",
            "compatibility_rejected", "protocol_not_ready", "inventory_mismatch",
        }:
            reason_code = "input_invalid"
        self.reason_code = reason_code
        super().__init__(reason_code)


class CalibrationInputError(CalibrationError):
    pass


class CalibrationVerificationError(CalibrationError):
    pass


class CalibrationCompatibilityError(CalibrationError):
    pass
