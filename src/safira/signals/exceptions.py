"""Typed, privacy-safe Feature 004 failures."""


class SignalError(RuntimeError):
    code = "signal_error"

    def __init__(self, code=None):
        safe = code if type(code) is str and code.replace("_", "").isalnum() else self.code
        self.reason_code = safe
        super().__init__(safe)


class SignalInputError(SignalError):
    code = "signal_input_invalid"


class SignalVerificationError(SignalError):
    code = "signal_input_not_verified"


class SignalProtocolError(SignalError):
    code = "signal_protocol_invalid"


class SignalCompatibilityError(SignalError):
    code = "signal_compatibility_error"


class SignalNotReady(SignalError):
    code = "signal_not_ready"


class SignalPrivacyError(SignalError):
    code = "signal_privacy_error"
