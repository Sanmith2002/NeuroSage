from dataclasses import replace

import pytest

from runtime_fixtures import build_runtime_fixture
from safira.runtime._exceptions import RuntimeAdmissionRejected
from safira.runtime._service import simulate_synthetic_assessment


@pytest.mark.parametrize("force_logistic", [False, True])
def test_synthetic_end_to_end_success_has_exact_scope_and_lifecycle(
        registered_collection, force_logistic):
    fixture = build_runtime_fixture(registered_collection, force_logistic=force_logistic)
    result = simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                           verifier=fixture.verifier)
    assert result.scope == fixture.expected["scope"]
    assert result.status in ("TRUST", "CAUTION")
    assert result.execution_mode == "SYNTHETIC_TEST_ONLY"
    assert result.policy_status == "SELECTED_UNEVALUATED"
    assert result.independent_evaluation_complete is False
    assert result.protected_test_accessed is False
    assert result.deployable is False
    assert result.clinical_validity_established is False


def test_shared_trust_failure_is_an_exception_and_never_returns_a_status(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    fixture.verifier.allow_synthetic = False
    with pytest.raises(RuntimeAdmissionRejected) as caught:
        simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                      verifier=fixture.verifier)
    assert caught.value.reason_code == "synthetic_fixture_rejected"
    assert "untrusted" not in str(caught.value).lower()


def test_admitted_required_measurement_failure_returns_scoreless_defer(
        registered_collection, monkeypatch):
    from safira.runtime import _service
    from safira.runtime._exceptions import RuntimeReadinessFailure

    fixture = build_runtime_fixture(registered_collection)
    monkeypatch.setattr(_service, "apply_frozen_runtime_score",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            RuntimeReadinessFailure("required_evidence_unavailable")))
    result = simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                           verifier=fixture.verifier)
    assert result.status == "DEFER"
    assert result.reason_code == "required_evidence_unavailable"
    assert "score" not in result.to_dict()


def test_valid_score_below_frozen_cutoff_maps_to_caution(registered_collection, monkeypatch):
    from types import SimpleNamespace
    from safira.runtime import _service

    fixture = build_runtime_fixture(registered_collection)
    monkeypatch.setattr(_service, "apply_frozen_runtime_score",
                        lambda *_args, **_kwargs: SimpleNamespace(value=0.0))
    result = simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                           verifier=fixture.verifier)
    assert result.status == "CAUTION"
    assert result.reason_code == "cutoff_not_satisfied"


def test_unexpected_programming_error_is_not_disguised_as_defer(
        registered_collection, monkeypatch):
    from safira.runtime import _service

    fixture = build_runtime_fixture(registered_collection)
    monkeypatch.setattr(_service, "derive_runtime_signal_record",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            RuntimeError("unexpected programming defect")))
    with pytest.raises(RuntimeError, match="unexpected programming defect"):
        simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                      verifier=fixture.verifier)


def test_separate_assessment_associations_have_separate_private_bindings(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    first = simulate_synthetic_assessment(fixture.request, registry=fixture.registry,
                                          verifier=fixture.verifier)
    from safira.collection import CollectionAssociation, LiveRequest, collect_live
    from dataclasses import replace

    source = fixture.expected["scope"]
    prediction = collect_live(fixture.registry,
        CollectionAssociation("another-synthetic-patient", "another-assessment", "another-occurrence"),
        [LiveRequest(*source)], {"synthetic-feature": [14.0]}).records[0]
    fixture.verifier.prediction_ledger.admit(prediction)
    fixture.verifier.admit_synthetic(prediction)
    second_request = replace(fixture.request, prediction=prediction)
    second = simulate_synthetic_assessment(second_request, registry=fixture.registry,
                                           verifier=fixture.verifier)
    assert first.scope == second.scope == source
    assert first.association_fingerprint != second.association_fingerprint
    assert first.to_dict()["policy_digest"] == second.to_dict()["policy_digest"]

