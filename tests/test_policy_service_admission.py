"""Atomicity checks: no scoring/reference work starts before trusted gates pass."""

import pytest

from policy_fixtures import make_end_to_end_case
from safira.policy import PolicyError
import safira.policy.service as service_module


def test_unapproved_protocol_fails_before_reference_reconstruction_or_scoring(registered_collection, monkeypatch):
    service, ledger, _, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    calls = []
    monkeypatch.setattr(service_module, "reconstruct_original_references",
                        lambda *args, **kwargs: calls.append("reference"))
    monkeypatch.setattr(service_module, "reconstruct_calibrated_scores",
                        lambda *args, **kwargs: calls.append("score"))
    ledger.approved_protocols.clear()
    with pytest.raises(PolicyError):
        service.select(policy_dataset=data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)
    assert calls == []


def test_unadmitted_prediction_fails_before_any_score_computation(registered_collection, monkeypatch):
    service, ledger, _, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    calls = []
    monkeypatch.setattr(service_module, "reconstruct_calibrated_scores",
                        lambda *args, **kwargs: calls.append("score"))
    ledger.prediction_ledger._entries.clear()
    with pytest.raises(PolicyError):
        service.select(policy_dataset=data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)
    assert calls == []
