from dataclasses import replace

import pytest

from runtime_fixtures import build_runtime_fixture
from safira.runtime._verification import admit_runtime_request
from safira.runtime._policy import map_runtime_policy_status


def test_policy_uses_the_exact_frozen_comparison_and_cutoff(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    policy = fixture.request.policy
    cutoff = policy.selection.cutoff
    if policy.selection_configuration["comparison"] == ">=":
        assert map_runtime_policy_status(admitted, cutoff).status == "TRUST"
        assert map_runtime_policy_status(admitted, cutoff - 0.01).status == "CAUTION"
    else:
        assert map_runtime_policy_status(admitted, cutoff).status == "CAUTION"
        assert map_runtime_policy_status(admitted, cutoff + 0.01).status == "TRUST"


@pytest.mark.parametrize("comparison", [">=", ">"])
def test_inclusive_and_exclusive_equality_follow_policy_artifact(registered_collection, comparison):
    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    policy = fixture.request.policy
    configuration = dict(policy.selection_configuration)
    configuration["comparison"] = comparison
    modified_policy = replace(policy, selection_configuration=configuration, digest="")
    modified_request = replace(fixture.request, policy=modified_policy)
    modified_admitted = replace(admitted, request=modified_request)
    outcome = map_runtime_policy_status(modified_admitted, modified_policy.selection.cutoff)
    assert outcome.status == ("TRUST" if comparison == ">=" else "CAUTION")
    assert "score" not in repr(outcome).lower()


def test_policy_rejects_nonfinite_scores_and_does_not_return_numeric_value(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    for bad in (float("nan"), float("inf"), -0.1, 1.1):
        with pytest.raises(ValueError):
            map_runtime_policy_status(admitted, bad)
    outcome = map_runtime_policy_status(admitted, 0.5)
    assert not hasattr(outcome, "score")
    assert not hasattr(outcome, "value")

