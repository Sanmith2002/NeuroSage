"""Allowlisted immutable policy artifact construction and integrity checking."""

from safira.policy.exceptions import PolicyInputError
from safira.policy.records import (PolicyEvidenceReference, PolicyScope,
    PolicySelectionSummary, SelectivePolicyArtifact, canonical_digest)


_DATASET_KEYS = {"dataset_id", "manifest_reference", "manifest_digest", "protocol_id",
                 "protocol_version", "builder_version", "dataset_fingerprint",
                 "admitted_inventory_digest"}
_SIGNAL_KEYS = {"run_version", "feature_set_fingerprint", "method_ids", "fitted_state_ids", "scope_key"}


def freeze_policy_artifact(*, scope, protocol_id, protocol_version, protocol_digest,
                           estimator_digest, calibrator_digest, original_dataset_reference,
                           original_signal_reference, policy_evidence, selection_configuration, selection):
    if (type(scope) is not PolicyScope or type(policy_evidence) is not PolicyEvidenceReference
            or type(selection) is not PolicySelectionSummary
            or set(original_dataset_reference) != _DATASET_KEYS
            or set(original_signal_reference) != _SIGNAL_KEYS
            or tuple(original_signal_reference["scope_key"]) != scope.source_key):
        raise PolicyInputError("artifact_invalid")
    for key in ("manifest_digest", "dataset_fingerprint", "admitted_inventory_digest"):
        value = original_dataset_reference[key]
        if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise PolicyInputError("artifact_invalid")
    for key in ("feature_set_fingerprint",):
        value = original_signal_reference[key]
        if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise PolicyInputError("artifact_invalid")
    return SelectivePolicyArtifact(scope, protocol_id, protocol_version, protocol_digest,
        estimator_digest, calibrator_digest, original_dataset_reference, original_signal_reference,
        policy_evidence, selection_configuration, selection)


def verify_policy_artifact(artifact, *, scope, estimator_digest, calibrator_digest,
                           policy_evidence, protocol_digest):
    if (type(artifact) is not SelectivePolicyArtifact or artifact.scope != scope
            or artifact.estimator_digest != estimator_digest or artifact.calibrator_digest != calibrator_digest
            or artifact.policy_evidence != policy_evidence or artifact.protocol_digest != protocol_digest
            or canonical_digest(artifact._body()) != artifact.digest):
        raise PolicyInputError("artifact_invalid")
    return True

