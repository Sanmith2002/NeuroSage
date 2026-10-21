from dataclasses import FrozenInstanceError

import pytest

from safira.runtime._records import InternalResearchAssessmentResult


def make_result(**changes):
    values = {
        "scope": ("model-a", "v7", "label-x"),
        "association_fingerprint": "a" * 64,
        "status": "TRUST",
        "reason_code": "cutoff_satisfied",
        "estimator_digest": "b" * 64,
        "calibrator_digest": "c" * 64,
        "policy_digest": "d" * 64,
    }
    values.update(changes)
    return InternalResearchAssessmentResult(**values)


def test_result_is_immutable_exact_scoped_and_lifecycle_locked():
    result = make_result()
    assert result.scope == ("model-a", "v7", "label-x")
    assert result.execution_mode == "SYNTHETIC_TEST_ONLY"
    assert result.policy_status == "SELECTED_UNEVALUATED"
    assert result.independent_evaluation_complete is False
    assert result.protected_test_accessed is False
    assert result.deployable is False
    assert result.clinical_validity_established is False
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.status = "CAUTION"


def test_result_serialization_is_allowlisted_and_has_no_score_or_identifiers():
    result = make_result()
    serialized = result.to_dict()
    assert set(serialized) == {
        "scope", "association_fingerprint", "status", "reason_code",
        "estimator_digest", "calibrator_digest", "policy_digest",
        "execution_mode", "policy_status", "independent_evaluation_complete",
        "protected_test_accessed", "deployable", "clinical_validity_established",
    }
    assert not {"score", "patient_id", "assessment_id", "target", "evidence"} & set(serialized)


@pytest.mark.parametrize("field,value", [
    ("execution_mode", "LIVE"),
    ("policy_status", "EVALUATED"),
    ("independent_evaluation_complete", True),
    ("protected_test_accessed", True),
    ("deployable", True),
    ("clinical_validity_established", True),
    ("status", "DEPLOY"),
])
def test_result_rejects_lifecycle_or_status_escalation(field, value):
    with pytest.raises((TypeError, ValueError)):
        make_result(**{field: value})


def test_result_repr_and_str_do_not_expose_association_binding_or_scores():
    result = make_result(association_fingerprint="e" * 64)
    assert "e" * 32 not in repr(result)
    assert "e" * 32 not in str(result)
    assert "score" not in repr(result).lower()

