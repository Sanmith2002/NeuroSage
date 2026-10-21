"""Feature 005 exact-scope correctness-estimator training.

The public service admits complete trusted Feature 002/003/004 inputs, trains
and selects within the approved train/validation lifecycle, and returns only
uncalibrated, non-deployable research artifacts. Numerical candidate helpers
and feature-matrix builders remain internal.
"""

from safira.training.exceptions import (
    TrainingArtifactError, TrainingCompatibilityError, TrainingError, TrainingInputError,
    TrainingVerificationError,
)
from safira.training.records import (
    CandidateFailurePolicy, FeatureKind, FeaturePolicy, FeatureSpec, LogisticCandidateConfig,
    PreprocessingPolicy, SafetyEstimatorArtifact, TrainingInputCheck, TrainingOutcome,
    TrainingProtocol, TrainingScope, TrainingStatus, TrainingSupportCriteria, ValidationSupportCriteria,
)
from safira.training.service import SafetyTrainingService
from safira.training.verification import TrainingInputVerifier
from safira.training.artifacts import ArtifactCompatibility, ArtifactOriginCheck, validate_artifact

__all__ = [
    "SafetyTrainingService", "TrainingScope", "TrainingSupportCriteria", "TrainingProtocol",
    "TrainingInputCheck", "TrainingStatus", "TrainingOutcome", "SafetyEstimatorArtifact",
    "ValidationSupportCriteria", "CandidateFailurePolicy", "ArtifactCompatibility",
    "ArtifactOriginCheck", "validate_artifact", "TrainingError",
    "FeatureKind", "FeatureSpec", "FeaturePolicy", "PreprocessingPolicy", "LogisticCandidateConfig",
    "TrainingInputError", "TrainingVerificationError", "TrainingCompatibilityError",
    "TrainingArtifactError", "TrainingInputVerifier",
]

