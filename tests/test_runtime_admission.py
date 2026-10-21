from dataclasses import replace

import pytest

from runtime_fixtures import build_runtime_fixture
from safira.runtime._exceptions import RuntimeAdmissionRejected
from safira.runtime._verification import admit_runtime_request


def test_exact_synthetic_prediction_registry_and_original_inventory_are_admitted(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    assert admitted.scope_key == fixture.expected["scope"]
    assert admitted.prediction_fingerprint
    assert admitted.request.estimator.digest == fixture.expected["estimator"].digest
    assert admitted.request.calibrator.digest == fixture.expected["calibrator"].digest
    assert admitted.request.policy.digest == fixture.expected["policy"].digest
    assert fixture.verifier.synthetic_calls == 1
    assert fixture.verifier.predictor_calls == 1
    assert fixture.verifier.artifact_calls >= 3


def test_changed_prediction_or_cross_scope_artifact_fails_before_admission_token(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    changed = replace(fixture.request, prediction=fixture.request.original_dataset.development.train[0].prediction)
    with pytest.raises(RuntimeAdmissionRejected):
        admit_runtime_request(fixture.registry, changed, fixture.verifier)

    object.__setattr__(fixture.request.policy, "scope", replace(
        fixture.request.policy.scope, label_id="other-label"))
    with pytest.raises(RuntimeAdmissionRejected):
        admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)


def test_untrusted_synthetic_or_predictor_inventory_receipt_is_rejected(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    fixture.verifier.allow_synthetic = False
    with pytest.raises(RuntimeAdmissionRejected):
        admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    fixture.verifier.allow_synthetic = True
    fixture.verifier.tamper_predictors = True
    with pytest.raises(RuntimeAdmissionRejected):
        admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)


def test_missing_artifact_origin_and_policy_protocol_approval_fail_atomically(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    fixture.verifier.deny_artifact = fixture.request.policy.digest
    with pytest.raises(RuntimeAdmissionRejected):
        admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    fixture.verifier.deny_artifact = None
    fixture.verifier.deny_policy_protocol = True
    with pytest.raises(RuntimeAdmissionRejected):
        admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)


def test_trust_error_is_safe_and_unexpected_programming_error_remains_distinct(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    fixture.verifier.allow_synthetic = False
    with pytest.raises(RuntimeAdmissionRejected) as caught:
        admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    assert str(caught.value) == "synthetic_fixture_rejected"
    assert "synthetic-query-patient" not in str(caught.value)
    assert caught.value.__cause__ is None

    def broken_verifier(_record):
        raise RuntimeError("unexpected implementation defect")

    fixture.verifier.verify_prediction = broken_verifier
    with pytest.raises(RuntimeError, match="unexpected implementation defect"):
        admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)


def test_admission_never_reads_original_supervised_targets_or_accepts_unlisted_prediction(
        registered_collection, monkeypatch):
    from safira.collection import CollectionAssociation, LiveRequest, collect_live
    from safira.dataset.records import CorrectnessExample

    fixture = build_runtime_fixture(registered_collection)
    monkeypatch.setattr(CorrectnessExample, "correctness_target",
                        property(lambda _self: pytest.fail("runtime accessed correctness target")),
                        raising=False)
    monkeypatch.setattr(CorrectnessExample, "outcome",
                        property(lambda _self: pytest.fail("runtime accessed ground truth")), raising=False)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    assert admitted.scope_key == fixture.expected["scope"]

    source = fixture.expected["scope"]
    prediction = collect_live(
        fixture.registry,
        CollectionAssociation("unlisted-synthetic-patient", "unlisted-assessment", "unlisted-occurrence"),
        [LiveRequest(*source)], {"synthetic-feature": [29.0]},
    ).records[0]
    fixture.verifier.prediction_ledger.admit(prediction)
    assert fixture.verifier.verify_prediction(prediction)
    with pytest.raises(RuntimeAdmissionRejected, match="synthetic_fixture_rejected"):
        admit_runtime_request(fixture.registry, replace(fixture.request, prediction=prediction),
                              fixture.verifier)

