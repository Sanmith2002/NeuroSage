import safira
import safira.models

from runtime_fixtures import build_runtime_fixture
from safira.runtime._service import simulate_synthetic_assessment


def test_runtime_simulation_is_not_exported_as_public_or_legacy_assessment_api():
    assert not hasattr(safira, "simulate_synthetic_assessment")
    assert not hasattr(safira.models, "simulate_synthetic_assessment")
    assert not hasattr(safira.models, "assess_runtime")


def test_result_is_not_a_safetyassessment_projection_and_cannot_claim_deployment(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    result = simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                           verifier=fixture.verifier)
    assert not isinstance(result, safira.models.SafetyAssessment)
    assert result.execution_mode == "SYNTHETIC_TEST_ONLY"
    assert result.policy_status == "SELECTED_UNEVALUATED"
    assert result.independent_evaluation_complete is False
    assert result.protected_test_accessed is False
    assert result.deployable is False
    assert result.clinical_validity_established is False
