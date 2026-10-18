"""Feature 004 safety signal extraction primitives."""

from safira.signals.base import SignalDimension, SignalInputVerifier, SignalState
from safira.signals.exceptions import (
    SignalCompatibilityError,
    SignalError,
    SignalInputError,
    SignalNotReady,
    SignalPrivacyError,
    SignalProtocolError,
    SignalVerificationError,
)
from safira.signals.records import (
    FittedStateReference,
    SignalInputCheck,
    SignalMethodConfig,
    SignalProtocol,
    SignalResult,
    SignalSourceKey,
)
from safira.signals.service import SignalExtractor

__all__ = [
    "SignalDimension", "SignalState", "SignalInputVerifier", "SignalError", "SignalInputError",
    "SignalVerificationError", "SignalProtocolError", "SignalCompatibilityError",
    "SignalNotReady", "SignalPrivacyError", "SignalSourceKey", "SignalMethodConfig",
    "SignalProtocol", "SignalInputCheck", "SignalResult", "FittedStateReference",
    "SignalExtractor",
]
