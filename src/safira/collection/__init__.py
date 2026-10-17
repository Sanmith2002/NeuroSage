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

__all__ = [
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
