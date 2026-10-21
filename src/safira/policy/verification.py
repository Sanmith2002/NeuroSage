"""Strict trusted-host admission helpers for Feature 007."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from safira.calibration.records import CalibratorArtifact
from safira.dataset.records import CorrectnessExample, DatasetBuildResult
from safira.policy.exceptions import PolicyVerificationError
from safira.policy.records import PolicyEvidenceReference, PolicyScope, PolicySelectionProtocol
from safira.signals.records import SignalProtocol
from safira.signals.validation import dataset_fingerprint, prediction_fingerprint
from safira.training.artifacts import ArtifactOriginCheck


class PolicyInputVerifier(Protocol):
    """Trusted-host provider. The core validates exact returned bindings."""
    def verify_prediction(self, record): ...
    def verify_dataset(self, dataset, reference): ...
    def verify_ground_truth(self, example, prediction, scope): ...
    def verify_patient_disjointness(self, policy_reference, prior_history, protected_scope): ...
    def verify_artifact(self, payload_digest, scope_key, artifact_version): ...
    def verify_protocol(self, protocol): ...


@dataclass(frozen=True)
class PolicyGroundTruthCheck:
    prediction_fingerprint: str
    source_key: tuple[str, str, str]
    patient_group_ref: str
    assessment_ref: str
    target_id: str
    target_version: str
    outcome: int
    correctness_target: int
    state: str
    authority: str
    method: str
    evidence_ref: str

    def __post_init__(self):
        object.__setattr__(self, "source_key", tuple(self.source_key))


@dataclass(frozen=True)
class PolicyProtocolCheck:
    protocol_digest: str
    state: str
    approved_before_outcomes: bool
    authority: str
    method: str
    evidence_ref: str


@dataclass(frozen=True)
class PatientDisjointnessCheck:
    policy_dataset_fingerprint: str
    policy_dataset_id: str
    policy_manifest_digest: str
    prior_dataset_refs: tuple[str, ...]
    scope_keys: tuple[tuple[str, str, str], ...]
    prior_history_version: str
    protected_scope_ref: str
    protected_scope_version: str
    history_complete: bool
    protected_membership_checked: bool
    state: str
    authority: str
    method: str
    evidence_ref: str

    def __post_init__(self):
        object.__setattr__(self, "prior_dataset_refs", tuple(self.prior_dataset_refs))
        object.__setattr__(self, "scope_keys", tuple(tuple(key) for key in self.scope_keys))


def _required_text(*values):
    return all(type(value) is str and bool(value.strip()) for value in values)


def verify_artifact_origin(verifier, digest, source_key, version):
    """Reject caller assertions and require an exact typed ledger result."""
    if (verifier is None or not callable(getattr(verifier, "verify_artifact", None))
            or not _required_text(digest, version) or len(tuple(source_key)) != 3):
        raise PolicyVerificationError("trusted_evidence_missing")
    try:
        check = verifier.verify_artifact(digest, tuple(source_key), version)
    except Exception:
        raise PolicyVerificationError("origin_rejected") from None
    if (type(check) is not ArtifactOriginCheck or check.payload_digest != digest
            or check.scope_key != tuple(source_key) or check.artifact_version != version
            or not _required_text(check.authority, check.method, check.evidence_ref)):
        raise PolicyVerificationError("origin_rejected")
    return check


def verify_protocol_approval(verifier, protocol):
    if not callable(getattr(verifier, "verify_protocol", None)):
        raise PolicyVerificationError("trusted_evidence_missing")
    try:
        check = verifier.verify_protocol(protocol)
    except Exception:
        raise PolicyVerificationError("protocol_not_approved") from None
    if (type(check) is not PolicyProtocolCheck or check.protocol_digest != protocol.digest
            or check.state != "verified" or check.approved_before_outcomes is not True
            or not _required_text(check.authority, check.method, check.evidence_ref)):
        raise PolicyVerificationError("protocol_not_approved")
    return check


def _verify_dataset(dataset_verifier, prediction_verifier, dataset, reference, signal_protocol):
    from safira.signals.validation import verify_dataset_admission
    try:
        check = verify_dataset_admission(dataset_verifier, prediction_verifier, dataset, reference)
    except Exception:
        raise PolicyVerificationError("verification_rejected") from None
    if (signal_protocol.protocol_id != reference.protocol_id
            or signal_protocol.protocol_version != reference.protocol_version
            or check.dataset_id != reference.dataset_id or check.protocol_id != reference.protocol_id):
        raise PolicyVerificationError("inventory_mismatch")
    if check.manifest_digest != reference.manifest_digest or check.authorized_partitions != (
            "train", "validation", "calibration"):
        raise PolicyVerificationError("inventory_mismatch")
    scopes = {tuple(item.to_tuple()) for item in signal_protocol.source_keys}
    if any(row.source_key not in scopes for row in check.rows):
        raise PolicyVerificationError("scope_incompatible")
    return check


def _verify_targets(verifier, dataset, protocol):
    if not callable(getattr(verifier, "verify_ground_truth", None)):
        raise PolicyVerificationError("trusted_evidence_missing")
    by_key = {scope.source_key: scope for scope in protocol.scopes}
    for role in ("train", "validation", "calibration"):
        for example in getattr(dataset.development, role):
            if type(example) is not CorrectnessExample or example.partition_role != role:
                raise PolicyVerificationError("inventory_mismatch")
            prediction = example.prediction
            source = tuple(prediction.source_key)
            scope = by_key.get(source)
            if scope is None or not example.patient_group_ref:
                raise PolicyVerificationError("scope_incompatible")
            target_binding = protocol.target_bindings.get("\0".join(source))
            if target_binding != (example.target_id, example.target_version):
                raise PolicyVerificationError("target_unverified")
            try:
                check = verifier.verify_ground_truth(example, prediction, scope)
            except Exception:
                raise PolicyVerificationError("target_unverified") from None
            expected = (prediction_fingerprint(prediction), source, example.patient_group_ref,
                        prediction.association.assessment_ref, example.target_id, example.target_version,
                        example.outcome, example.correctness_target)
            actual = (getattr(check, "prediction_fingerprint", None), getattr(check, "source_key", None),
                      getattr(check, "patient_group_ref", None), getattr(check, "assessment_ref", None),
                      getattr(check, "target_id", None), getattr(check, "target_version", None),
                      getattr(check, "outcome", None), getattr(check, "correctness_target", None))
            if (type(check) is not PolicyGroundTruthCheck or actual != expected or check.state != "verified"
                    or not _required_text(check.authority, check.method, check.evidence_ref)):
                raise PolicyVerificationError("target_unverified")


def verify_patient_disjointness(verifier, policy_dataset, policy_reference, original_reference, prior_history, scopes):
    if not callable(getattr(verifier, "verify_patient_disjointness", None)):
        raise PolicyVerificationError("trusted_evidence_missing")
    if not isinstance(prior_history, (tuple, list)):
        raise PolicyVerificationError("patient_overlap_unknown")
    try:
        protected_scope = {"original_reference": {name: getattr(original_reference, name) for name in
                               ("dataset_id", "protocol_id", "protocol_version", "manifest_reference",
                                "builder_version", "manifest_digest")},
                           "scope_keys": tuple(sorted(scope.source_key for scope in scopes)),
                           "membership": "protected_test"}
        check = verifier.verify_patient_disjointness(policy_reference, tuple(prior_history), protected_scope)
    except Exception:
        raise PolicyVerificationError("patient_overlap_unknown") from None
    policy_fp = dataset_fingerprint(policy_dataset)
    expected_refs = tuple(sorted({original_reference.dataset_id + ":" + original_reference.manifest_digest,
        *(str(item.manifest_id) + ":" + str(item.content_version) for item in prior_history)}))
    if (type(check) is not PatientDisjointnessCheck
            or check.policy_dataset_fingerprint != policy_fp
            or check.policy_dataset_id != policy_reference.dataset_id
            or check.policy_manifest_digest != policy_reference.manifest_digest
            or tuple(check.prior_dataset_refs) != expected_refs
            or tuple(tuple(key) for key in check.scope_keys) != tuple(sorted(scope.source_key for scope in scopes))
            or not _required_text(check.protected_scope_ref, check.protected_scope_version)
            or check.history_complete is not True or check.protected_membership_checked is not True
            or check.state != "verified_disjoint"
            or not _required_text(check.prior_history_version, check.authority, check.method, check.evidence_ref)):
        raise PolicyVerificationError("patient_overlap_unknown")
    return check


def verify_artifact_bundle(registry, scope, estimator, calibrator, verifier):
    """Verify Feature 001 identity, F005 origin, F006 exact base linkage and origin."""
    from safira.calibration.verification import verify_estimator_artifact
    from safira.training.records import SafetyEstimatorArtifact
    if type(estimator) is not SafetyEstimatorArtifact or type(calibrator) is not CalibratorArtifact:
        raise PolicyVerificationError("artifact_invalid")
    common_dataset_keys = ("dataset_id", "manifest_reference", "manifest_digest", "protocol_id",
                           "protocol_version", "builder_version")
    if (estimator.scope != scope.to_training_scope() or calibrator.scope != estimator.scope
            or calibrator.base_artifact_digest != estimator.digest
            or calibrator.base_artifact_version != estimator.artifact_version
            or calibrator.base_family != estimator.family
            or calibrator.base_feature_schema_digest != estimator.preprocessing["schema_digest"]
            or any(calibrator.dataset_reference[key] != estimator.dataset_reference[key]
                   for key in common_dataset_keys)
            or calibrator.dataset_reference["inventory_digest"] != estimator.dataset_reference["admitted_inventory_digest"]
            or calibrator.signal_run_reference != estimator.signal_run_reference):
        raise PolicyVerificationError("scope_incompatible")
    try:
        verify_estimator_artifact(registry, estimator, scope.to_training_scope(), verifier)
    except Exception:
        raise PolicyVerificationError("origin_rejected") from None
    verify_artifact_origin(verifier, calibrator.digest, scope.source_key, calibrator.artifact_version)
    return True

