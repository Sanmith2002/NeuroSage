"""Shared Feature 004 signal dimensions and availability vocabulary."""

from __future__ import annotations

from enum import Enum
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from safira.collection.records import PredictionRecord
    from safira.dataset.records import DatasetBuildResult
    from safira.signals.records import (Feature003DatasetReference, ProtectedApplyReceipt,
                                        ProtectedApplyRequest, SignalDatasetCheck, SignalInputCheck)


class SignalDimension(str, Enum):
    DATA_SUFFICIENCY = "data_sufficiency"
    DISTRIBUTION_CONFORMITY = "distribution_conformity_ood"
    PREDICTION_UNCERTAINTY = "prediction_uncertainty"
    MODALITY_AGREEMENT = "modality_agreement"
    DOMAIN_FAMILIARITY = "domain_familiarity"
    EXPLANATION_RELIABILITY = "explanation_reliability"


class SignalState(str, Enum):
    AVAILABLE = "available"
    UNSUPPORTED = "unsupported"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_READY = "not_ready"


class SignalInputVerifier(Protocol):
    """Host-owned integration that checks records against independent evidence."""

    def verify_prediction(self, record: PredictionRecord) -> SignalInputCheck:
        """Return a content-, identity-, association- and scope-bound check."""
        ...

    def verify_dataset(self, result, reference):
        """Check full Feature 003 development inventory against independent evidence."""
        ...


class DatasetInputVerifier(Protocol):
    """Independently verifies complete Feature 003 development inputs."""

    def verify_dataset(self, result: DatasetBuildResult,
                       reference: Feature003DatasetReference) -> SignalDatasetCheck:
        ...


class ProtectedSignalApplyHandoff(Protocol):
    """Custodian-side apply-only bridge; accepts references, never protected rows."""

    def apply_frozen_state(self, request: ProtectedApplyRequest) -> ProtectedApplyReceipt:
        ...
