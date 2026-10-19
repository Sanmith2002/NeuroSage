"""Feature 004 safety signal extraction primitives."""

from safira.signals.base import (DatasetInputVerifier, ProtectedSignalApplyHandoff,
                                 SignalDimension, SignalInputVerifier, SignalState)
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
    CohortAdequacyCriteria,
    Feature003DatasetReference,
    FittedStateReference,
    ProtectedApplyReceipt,
    ProtectedApplyRequest,
    SignalDatasetCheck,
    SignalDatasetRowCheck,
    SignalFeatureRecord,
    SignalFeatureSet,
    SignalInputCheck,
    SignalMethodConfig,
    SignalProtocol,
    SignalResult,
    SignalRowKey,
    SignalRunManifest,
    SignalSourceKey,
)
from safira.signals.service import SignalExtractor

__all__ = [
    "SignalDimension", "SignalState", "SignalInputVerifier", "DatasetInputVerifier",
    "ProtectedSignalApplyHandoff", "SignalError", "SignalInputError",
    "SignalVerificationError", "SignalProtocolError", "SignalCompatibilityError",
    "SignalNotReady", "SignalPrivacyError", "SignalSourceKey", "SignalMethodConfig",
    "SignalProtocol", "CohortAdequacyCriteria", "SignalInputCheck", "SignalResult", "FittedStateReference",
    "SignalExtractor", "Feature003DatasetReference", "SignalDatasetRowCheck",
    "SignalDatasetCheck", "SignalRowKey", "SignalFeatureRecord", "SignalFeatureSet",
    "SignalRunManifest", "ProtectedApplyRequest", "ProtectedApplyReceipt",
]
