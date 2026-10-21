"""Private immutable records for a synthetic-only runtime simulation."""

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import secrets


_ASSOCIATION_KEY = secrets.token_bytes(32)
_STATUSES = frozenset({"TRUST", "CAUTION", "DEFER"})
_REASONS = frozenset({
    "cutoff_satisfied", "cutoff_not_satisfied", "required_evidence_unavailable",
    "evidence_invalid", "evidence_incompatible", "evidence_not_ready",
})


def association_fingerprint(prediction) -> str:
    """Return a process-keyed binding without retaining the association values."""
    material = json.dumps(
        {"scope": tuple(prediction.source_key),
         "association": prediction.association.to_dict(),
         "prediction": prediction.to_dict()},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hmac.new(_ASSOCIATION_KEY, material, sha256).hexdigest()


@dataclass(frozen=True, repr=False)
class SyntheticRuntimeRequest:
    prediction: object
    scope: object
    original_dataset: object
    original_reference: object
    original_signal_protocol: object
    original_signal_set: object
    estimator: object
    calibrator: object
    policy_protocol: object
    policy: object

    def __post_init__(self):
        from safira.calibration.records import CalibratorArtifact
        from safira.collection.records import PredictionRecord
        from safira.dataset.records import DatasetBuildResult
        from safira.policy.records import PolicyScope, PolicySelectionProtocol, SelectivePolicyArtifact
        from safira.signals.records import Feature003DatasetReference, SignalFeatureSet, SignalProtocol
        from safira.training.records import SafetyEstimatorArtifact

        expected = (
            (self.prediction, PredictionRecord),
            (self.scope, PolicyScope),
            (self.original_dataset, DatasetBuildResult),
            (self.original_reference, Feature003DatasetReference),
            (self.original_signal_protocol, SignalProtocol),
            (self.original_signal_set, SignalFeatureSet),
            (self.estimator, SafetyEstimatorArtifact),
            (self.calibrator, CalibratorArtifact),
            (self.policy_protocol, PolicySelectionProtocol),
            (self.policy, SelectivePolicyArtifact),
        )
        if any(type(value) is not cls for value, cls in expected):
            raise TypeError("runtime_request_invalid")
        source = tuple(self.prediction.source_key)
        if (source != self.scope.source_key
                or self.estimator.scope != self.scope.to_training_scope()
                or self.calibrator.scope != self.estimator.scope
                or self.policy.scope != self.scope
                or self.policy_protocol.digest != self.policy.protocol_digest
                or self.original_signal_protocol.protocol_id != self.original_reference.protocol_id
                or self.original_signal_protocol.protocol_version != self.original_reference.protocol_version):
            raise ValueError("runtime_request_scope_mismatch")

    def __repr__(self):
        return "SyntheticRuntimeRequest(<private synthetic fixture>)"


@dataclass(frozen=True, repr=False)
class InternalResearchAssessmentResult:
    scope: tuple[str, str, str]
    association_fingerprint: str
    status: str
    reason_code: str
    estimator_digest: str
    calibrator_digest: str
    policy_digest: str
    execution_mode: str = "SYNTHETIC_TEST_ONLY"
    policy_status: str = "SELECTED_UNEVALUATED"
    independent_evaluation_complete: bool = False
    protected_test_accessed: bool = False
    deployable: bool = False
    clinical_validity_established: bool = False

    def __post_init__(self):
        if (not isinstance(self.scope, tuple) or len(self.scope) != 3
                or any(type(item) is not str or not item.strip() for item in self.scope)):
            raise ValueError("result_scope_invalid")
        if (type(self.association_fingerprint) is not str or len(self.association_fingerprint) != 64
                or any(char not in "0123456789abcdef" for char in self.association_fingerprint)):
            raise ValueError("result_association_invalid")
        if self.status not in _STATUSES:
            raise ValueError("result_status_invalid")
        if self.reason_code not in _REASONS:
            raise ValueError("result_reason_invalid")
        for name in ("estimator_digest", "calibrator_digest", "policy_digest"):
            value = getattr(self, name)
            if (type(value) is not str or len(value) != 64
                    or any(char not in "0123456789abcdef" for char in value)):
                raise ValueError("result_artifact_digest_invalid")
        if (self.execution_mode != "SYNTHETIC_TEST_ONLY"
                or self.policy_status != "SELECTED_UNEVALUATED"
                or self.independent_evaluation_complete is not False
                or self.protected_test_accessed is not False
                or self.deployable is not False
                or self.clinical_validity_established is not False):
            raise ValueError("result_lifecycle_invalid")

    def to_dict(self):
        return {
            "scope": self.scope,
            "association_fingerprint": self.association_fingerprint,
            "status": self.status,
            "reason_code": self.reason_code,
            "estimator_digest": self.estimator_digest,
            "calibrator_digest": self.calibrator_digest,
            "policy_digest": self.policy_digest,
            "execution_mode": self.execution_mode,
            "policy_status": self.policy_status,
            "independent_evaluation_complete": self.independent_evaluation_complete,
            "protected_test_accessed": self.protected_test_accessed,
            "deployable": self.deployable,
            "clinical_validity_established": self.clinical_validity_established,
        }

    def __repr__(self):
        return (f"InternalResearchAssessmentResult(scope={self.scope!r}, status={self.status!r}, "
                "execution_mode='SYNTHETIC_TEST_ONLY', policy_status='SELECTED_UNEVALUATED')")

    __str__ = __repr__

