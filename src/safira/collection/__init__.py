"""Safira prediction and evidence collection foundations."""

from safira.collection.exceptions import (
    CollectionError,
    ContributorMismatch,
    EvidenceUnavailable,
    InvalidCollectionRequest,
    InvalidPrimaryOutput,
    ProvenanceCheckFailed,
    UnknownSourceContract,
)
from safira.collection.records import (
    CollectionAssociation,
    CollectionResult,
    ComponentContribution,
    ComponentIdentity,
    EvidenceItem,
    PredictionRecord,
    PrimaryOutput,
    SourceProvenance,
)
from safira.collection.live import LiveRequest, collect_live

__all__ = [
    "LiveRequest",
    "collect_live",
    "CollectionAssociation",
    "CollectionError",
    "CollectionResult",
    "ComponentContribution",
    "ComponentIdentity",
    "ContributorMismatch",
    "EvidenceItem",
    "EvidenceUnavailable",
    "InvalidCollectionRequest",
    "InvalidPrimaryOutput",
    "PredictionRecord",
    "PrimaryOutput",
    "ProvenanceCheckFailed",
    "SourceProvenance",
    "UnknownSourceContract",
]
