"""Patient-grouped correctness dataset construction (research prototype)."""

from .builder import DatasetBuilder
from .exceptions import (
    DatasetCompatibilityError, DatasetError, DatasetLeakageError,
    DatasetProtocolError, DatasetVerificationFailed, InvalidDatasetInput,
    PatientGroupingConflict,
)
from .records import (
    CorrectnessExample, DatasetBuildResult, DatasetManifest, DatasetReadiness,
    EvaluationProtocol, EvidenceTimingDeclaration, ExclusionRecord,
    IndependenceEvidence, IndependenceVerification, LinkageVerification,
    OutcomeCandidate, OutcomeVerification, PatientLinkageDeclaration,
    PartitionedDataset, PriorAssignmentManifest, PriorHistoryVerification,
    ProtectedArtifactReceipt, ProtectedTestArtifact, TargetBinding,
    TargetDefinition, TimingVerification, TransformationDeclaration,
    TransformationVerification,
)
from .verification import TrustedDatasetVerifier, ProtectedArtifactHandoff

__all__ = [
    "DatasetBuilder", "DatasetError", "InvalidDatasetInput", "DatasetVerificationFailed",
    "DatasetCompatibilityError", "PatientGroupingConflict", "DatasetLeakageError", "DatasetProtocolError",
    "TargetDefinition", "TargetBinding", "OutcomeCandidate", "OutcomeVerification",
    "IndependenceEvidence", "IndependenceVerification", "EvidenceTimingDeclaration", "TimingVerification",
    "TransformationDeclaration", "TransformationVerification", "PatientLinkageDeclaration", "LinkageVerification",
    "PriorAssignmentManifest", "PriorHistoryVerification", "EvaluationProtocol", "CorrectnessExample",
    "ExclusionRecord", "DatasetReadiness", "PartitionedDataset", "ProtectedTestArtifact",
    "ProtectedArtifactReceipt", "DatasetManifest", "DatasetBuildResult", "TrustedDatasetVerifier",
    "ProtectedArtifactHandoff",
]
