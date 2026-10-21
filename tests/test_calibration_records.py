from __future__ import annotations

import pytest

from safira.calibration.records import CalibrationOutcome, CalibrationProtocol, CalibrationStatus
from safira.calibration.exceptions import CalibrationError
from safira.training.records import TrainingScope


def scope():
    return TrainingScope("m", "v1", "l", "a" * 64, "adapter", "v1", "b" * 64,
                         {"pipeline": ["scaled"]})


def test_scope_and_protocol_detach_nested_values_and_outcomes_are_safe():
    identity = {"pipeline": ["scaled"]}
    source = TrainingScope("m", "v1", "l", "a" * 64, "adapter", "v1", "b" * 64, identity)
    identity["pipeline"].append("changed")
    assert source.preprocessing_identity["pipeline"] == ("scaled",)

    config = {"solver": {"name": "lbfgs"}}
    protocol = CalibrationProtocol("cal", "v1", (source,), config)
    config["solver"]["name"] = "mutated"
    assert protocol.configuration["solver"]["name"] == "lbfgs"
    with pytest.raises(TypeError):
        protocol.configuration["solver"]["name"] = "mutated"

    outcome = CalibrationOutcome(source, CalibrationStatus.NOT_READY, "approval_missing")
    assert outcome.artifact is None
    assert outcome.to_dict()["status"] == "NOT_READY"


def test_protocol_requires_exact_scope_and_approved_lifecycle_fields():
    with pytest.raises(ValueError):
        CalibrationProtocol("cal", "v1", (), {})
    with pytest.raises(ValueError):
        CalibrationProtocol("cal", "v1", (scope(),), {}, lifecycle="deployable")


def test_non_success_cannot_carry_an_artifact_or_unsafe_reason():
    with pytest.raises(ValueError):
        CalibrationOutcome(scope(), CalibrationStatus.INSUFFICIENT_EVIDENCE,
                           "patient-123", artifact=object())
    with pytest.raises(ValueError):
        CalibrationOutcome(scope(), CalibrationStatus.NOT_READY, "raw patient identifier")


def test_status_values_include_batch_a_readiness_distinctions():
    assert {"NOT_READY", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE_REQUIRED_EVIDENCE"} <= {
        status.value for status in CalibrationStatus
    }


def test_exception_messages_cannot_echo_untrusted_identifiers():
    error = CalibrationError("patient secret raw value")
    assert str(error) == "input_invalid"
    assert "patient" not in repr(error)
