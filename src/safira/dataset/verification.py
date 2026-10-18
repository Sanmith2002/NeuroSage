"""Explicit verifier interfaces and exact-scope result checks."""

from hashlib import sha256
import json
from typing import Protocol, runtime_checkable

from .exceptions import DatasetVerificationFailed
from .records import *


@runtime_checkable
class TrustedDatasetVerifier(Protocol):
    def verify_prediction_admission(self, prediction) -> PredictionAdmissionVerification: ...
    def verify_outcome(self, outcome, prediction, target_definition, target_binding) -> OutcomeVerification: ...
    def verify_independence(self, prediction, model_metadata, independence_evidence, protocol) -> IndependenceVerification: ...
    def verify_linkage(self, linkage_declaration, candidate_patient_refs, protocol) -> LinkageVerification: ...
    def verify_prior_history(self, prior_manifest, requested_scope, protocol) -> PriorHistoryVerification: ...
    def verify_timing(self, declaration, prediction, protocol) -> TimingVerification: ...
    def verify_transformation(self, declaration, protocol) -> TransformationVerification: ...


@runtime_checkable
class ProtectedArtifactHandoff(Protocol):
    def accept(self, artifact, protocol, manifest_reference) -> ProtectedArtifactReceipt: ...


@runtime_checkable
class DatasetManifestHandoff(Protocol):
    """Explicit custodian boundary for restricted immutable manifests."""

    def accept(self, manifest, protocol, manifest_reference) -> DatasetManifestReceipt: ...


def prediction_fingerprint(prediction):
    """Canonical fingerprint of the complete Feature 002 record value."""
    try:
        body = json.dumps(prediction.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        raise DatasetVerificationFailed("prediction_admission_failed") from None
    return sha256(body.encode("utf-8")).hexdigest()


def validate_prediction_admission(check, prediction):
    if type(check) is not PredictionAdmissionVerification:
        raise DatasetVerificationFailed("prediction_admission_failed")
    expected = (prediction_fingerprint(prediction), prediction.source_key, prediction.association,
                prediction.provenance.mode, "verified")
    actual = (check.record_fingerprint, check.source_key, check.association,
              check.provenance_mode, check.state)
    if actual != expected or not all((check.authority, check.method, check.evidence_ref)):
        raise DatasetVerificationFailed("prediction_admission_failed")


def validate_manifest_receipt(receipt, manifest, manifest_reference):
    if type(receipt) is not DatasetManifestReceipt or receipt.status != "accepted":
        raise DatasetVerificationFailed("manifest_handoff_failed")
    expected_reference = "manifest:" + manifest.digest
    expected = (expected_reference, manifest.digest, manifest.dataset_id,
                manifest.protocol_id, manifest.protocol_version, manifest.builder_version)
    actual = (receipt.manifest_reference, receipt.manifest_digest, receipt.dataset_id,
              receipt.protocol_id, receipt.protocol_version, receipt.builder_version)
    if (manifest_reference != expected_reference or actual != expected
            or not all((receipt.receipt_ref, receipt.custodian_id,
                        receipt.verification_method, receipt.evidence_ref))):
        raise DatasetVerificationFailed("manifest_handoff_failed")


def validate_outcome_check(check, outcome, binding):
    if type(check) is not OutcomeVerification:
        raise DatasetVerificationFailed("outcome_verification_failed")
    expected = (outcome.content_ref, outcome.source_contract_id, outcome.source_contract_version,
                outcome.patient_ref, outcome.assessment_ref, outcome.label_id,
                outcome.target_id, outcome.target_version,outcome.source_namespace,outcome.source_record_ref)
    actual = (check.content_ref, check.source_contract_id, check.source_contract_version,
              check.patient_ref, check.assessment_ref, check.label_id,
              check.target_id, check.target_version,check.source_namespace,check.source_record_ref)
    if actual != expected or check.state != "verified" or not all((check.authority,check.method,check.evidence_ref)):
        raise DatasetVerificationFailed("outcome_verification_failed")
    if (check.target_id, check.target_version) != (binding.target_id,binding.target_version):
        raise DatasetVerificationFailed("outcome_scope_mismatch")


def validate_independence_check(check, prediction, evidence, protocol):
    if type(check) is not IndependenceVerification:
        raise DatasetVerificationFailed("independence_verification_failed")
    key=(prediction.model_id,prediction.model_version,prediction.label_id,evidence.target_id,evidence.target_version)
    actual=(check.model_id,check.model_version,check.label_id,check.target_id,check.target_version)
    lineage=(check.development_source_ref,check.lineage_ref)
    if actual != key or check.state != "eligible" or lineage!=(evidence.development_source_ref,evidence.lineage_ref) or not all((check.authority,check.method,check.evidence_ref)):
        raise DatasetVerificationFailed("independence_verification_failed")


def validate_linkage_check(check, declaration, candidate_aliases):
    if type(check) is not LinkageVerification or (check.linkage_id,check.linkage_version,check.scope,check.state) != (declaration.linkage_id,declaration.linkage_version,declaration.scope,"verified") or not all((check.authority,check.method,check.evidence_ref)):
        raise DatasetVerificationFailed("linkage_verification_failed")
    expected_aliases=tuple(sorted(set(tuple(alias) for alias in candidate_aliases)))
    if dict(check.checked_entries)!=dict(declaration.entries) or tuple(sorted(set(check.checked_aliases)))!=expected_aliases or not set(expected_aliases).issubset(declaration.entries):
        raise DatasetVerificationFailed("linkage_scope_mismatch")


def validate_timing_check(check, declaration):
    expected=(declaration.source_key,declaration.occurrence_ref,declaration.category,declaration.available_at,"verified")
    actual=(check.source_key,check.occurrence_ref,check.category,check.available_at,check.state) if type(check) is TimingVerification else None
    if actual!=expected or not all((check.authority,check.method,check.evidence_ref)):
        raise DatasetVerificationFailed("timing_verification_failed")


def validate_transformation_check(check, declaration):
    expected=(declaration.transform_id,declaration.transform_version,declaration.source_key,"verified")
    actual=(check.transform_id,check.transform_version,check.source_key,check.state) if type(check) is TransformationVerification else None
    if actual!=expected or not all((check.authority,check.method,check.evidence_ref)):
        raise DatasetVerificationFailed("transformation_verification_failed")


def validate_prior_check(check, manifest, requested_scope):
    expected=(manifest.manifest_id,manifest.content_version,manifest.origin,manifest.source_id,requested_scope,manifest.scope,"verified_complete",tuple(manifest.protected_membership))
    actual=(check.manifest_id,check.content_version,check.origin,check.source_id,check.requested_scope,check.declared_scope,check.state,tuple(check.protected_membership))
    if type(check) is not PriorHistoryVerification or actual != expected or not all((check.completeness_evidence_ref,check.authority,check.method,check.evidence_ref)):
        raise DatasetVerificationFailed("prior_history_verification_failed")
