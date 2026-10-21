from safira.policy.records import PolicyScope, PolicySelectionOutcome, PolicyStatus
from safira.policy.exceptions import PolicyError


def test_error_repr_and_serialization_are_reason_code_only():
    error = PolicyError("verification_rejected", "patient-secret row-secret")
    assert "patient-secret" not in str(error)
    assert "row-secret" not in repr(error)
    assert error.to_dict() == {"error": "PolicyError", "reason_code": "verification_rejected"}


def test_outcome_has_no_unapproved_payload_fields():
    scope = PolicyScope("m", "v1", "l", "a" * 64, "adapter", "v1", "b" * 64, {})
    outcome = PolicySelectionOutcome(scope, PolicyStatus.NOT_READY, "trusted_evidence_missing")
    assert set(outcome.to_dict()) == {"scope", "status", "reason_code", "artifact", "summary"}
    assert "patient" not in repr(outcome).lower()
