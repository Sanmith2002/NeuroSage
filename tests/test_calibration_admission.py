from __future__ import annotations

import pytest

from signals_fixtures import SyntheticSignalVerifier, make_live_record, signal_protocol

from safira.calibration.verification import verify_prediction_admission
from safira.signals.records import SignalInputCheck


def test_prediction_admission_executes_injected_verifier_and_rejects_assertions(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    verifier = SyntheticSignalVerifier()
    verifier.admit(record)
    protocol = signal_protocol(record.source_key, {"evidence_coverage": {"required_evidence": []}})
    check = verify_prediction_admission(registry, protocol, verifier, record)
    assert type(check) is SignalInputCheck
    assert verifier.calls

    for fake in (True, "verified", check, "a" * 64):
        with pytest.raises(Exception):
            verify_prediction_admission(registry, protocol, fake, record)
    with pytest.raises(Exception):
        verify_prediction_admission(registry, protocol, None, record)


def test_unledgered_caller_constructed_prediction_fails_closed(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    verifier = SyntheticSignalVerifier()
    protocol = signal_protocol(record.source_key, {"evidence_coverage": {"required_evidence": []}})
    with pytest.raises(Exception):
        verify_prediction_admission(registry, protocol, verifier, record)
