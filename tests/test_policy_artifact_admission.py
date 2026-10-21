"""Exact Feature 001/005/006 bundle admission checks."""

import pytest

from policy_fixtures import make_end_to_end_case
from safira.policy import PolicyError


def test_estimator_origin_must_be_independently_ledgered(registered_collection):
    service, host, _, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    host.origin.artifacts.clear()
    for artifact in calibrator.values():
        host.origin.admit_artifact(artifact)
    with pytest.raises(PolicyError):
        service.select(policy_dataset=data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=estimator,
            calibrator_artifacts=calibrator)


def test_wrong_scope_key_and_wrong_upstream_artifact_type_are_rejected(registered_collection):
    service, _, _, data, original, signal_protocol, estimator, calibrator = make_end_to_end_case(registered_collection)
    wrong_key = {("another-model", "v1", "label-a"): next(iter(estimator.values()))}
    with pytest.raises(PolicyError):
        service.select(policy_dataset=data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=wrong_key,
            calibrator_artifacts=calibrator)
    wrong_type = {key: object() for key in estimator}
    with pytest.raises(PolicyError):
        service.select(policy_dataset=data, original_training_dataset=original,
            original_signal_protocol=signal_protocol, estimator_artifacts=wrong_type,
            calibrator_artifacts=calibrator)
