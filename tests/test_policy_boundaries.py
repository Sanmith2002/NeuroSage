"""Public surface remains cohort-only; final-test evaluation/runtime is separate."""

import inspect

import safira.policy as policy


def test_public_policy_surface_has_no_patient_inference_or_protected_input_api():
    assert not hasattr(policy, "predict")
    assert not hasattr(policy, "apply")
    assert not hasattr(policy, "SafetyContext")
    assert not hasattr(policy, "SafetyAssessment")
    parameters = inspect.signature(policy.PolicySelectionService.select).parameters
    assert "protected_test" not in parameters
    assert "protected_rows" not in parameters
    assert "patient" not in parameters


def test_public_exports_are_allowlisted_cohort_operations_only():
    assert set(policy.__all__) == {
        "PolicyError", "PolicyInputError", "PolicyVerificationError",
        "PolicyEvidenceReference", "PolicyScope", "PolicySelectionOutcome",
        "PolicySelectionProtocol", "PolicySelectionSummary", "PolicyStatus",
        "SelectivePolicyArtifact", "PolicySelectionService",
    }
