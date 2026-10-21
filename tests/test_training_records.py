import json

import pytest


def test_training_scope_and_protocol_are_exact_and_deeply_immutable():
    from safira.training.records import TrainingProtocol, TrainingScope, TrainingSupportCriteria

    scopes_input = [TrainingScope("m", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "none")]
    class_support_input = {0: 1, 1: 1}
    criteria_input = {("m", "v1", "label"): TrainingSupportCriteria(2, class_support_input)}
    required_input = {("m", "v1", "label"): ["evidence_coverage"]}
    protocol = TrainingProtocol("p", "v1", scopes_input, criteria_input, required_input)
    scopes_input.clear()
    class_support_input[0] = 99
    required_input[("m", "v1", "label")].append("other")

    assert protocol.scopes == (TrainingScope("m", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "none"),)
    assert protocol.adequacy[("m", "v1", "label")].correctness_class_minimums[0] == 1
    assert protocol.required_signal_methods[("m", "v1", "label")] == ("evidence_coverage",)
    with pytest.raises(TypeError):
        protocol.adequacy["m", "v1", "label"].correctness_class_minimums[0] = 4
    exported = protocol.to_dict()
    exported["required_signal_methods"]["[\"m\",\"v1\",\"label\"]"].append("mutated")
    assert protocol.required_signal_methods[("m", "v1", "label")] == ("evidence_coverage",)
    json.dumps(exported)


def test_outcome_has_distinct_readiness_and_evidence_states_and_safe_export():
    from safira.training.records import TrainingOutcome, TrainingScope, TrainingStatus

    scope = TrainingScope("m", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "none")
    outcome = TrainingOutcome(scope, TrainingStatus.INSUFFICIENT_EVIDENCE,
                              reason_code="correctness_class_support_insufficient")
    exported = json.loads(json.dumps(outcome.to_dict()))
    assert exported["scope"]["model_id"] == "m"
    assert exported["status"] == "INSUFFICIENT_EVIDENCE"
    assert exported["reason_code"] == "correctness_class_support_insufficient"
    assert "preprocessing_identity" in exported["scope"]
    assert TrainingStatus.NOT_READY is not TrainingStatus.INSUFFICIENT_EVIDENCE


def test_every_approved_batch_a_status_is_explicit():
    from safira.training.records import TrainingStatus

    assert {item.value for item in TrainingStatus} == {
        "ELIGIBLE_FOR_CANDIDATE_FITTING", "INSUFFICIENT_EVIDENCE", "NOT_READY",
        "UNAVAILABLE_REQUIRED_EVIDENCE", "INVALID_INPUT", "INCOMPATIBLE_INPUT",
        "COMPARISON_UNDEFINED", "SELECTED_BASELINE", "SELECTED_LOGISTIC",
    }


def test_training_input_check_detaches_nested_inventory_and_hides_it_from_repr():
    from safira.training.records import TrainingInputCheck

    row = ["train", "a" * 64, ["m", "v1", "label"], "row", ["m", "v1", "label"]]
    check = TrainingInputCheck("a" * 64, "b" * 64, "d", "p", "v1", "manifest", "c" * 64,
                               "builder", "signals-v1", (), (), [row], "authority", "lookup", "ref")
    row[2][0] = "changed"
    row[0] = "validation"
    assert check.row_inventory[0][0] == "train"
    assert check.row_inventory[0][2][0] == "m"
    assert "row" not in repr(check)


@pytest.mark.parametrize("bad_scope", [("", "v1", "label"), ("m", "", "label"), ("m", "v1", "")])
def test_scope_rejects_incomplete_identity(bad_scope):
    from safira.training.records import TrainingScope

    with pytest.raises(ValueError):
        TrainingScope(*bad_scope, "a" * 64, "adapter", "v1", "b" * 64, "none")
