import pytest

from safira.policy.records import (PolicyEvidenceReference, PolicyScope,
    PolicySelectionProtocol, PolicySelectionSummary, SelectivePolicyArtifact)


def scope():
    return PolicyScope("m", "v1", "l", "a" * 64, "adapter", "v1", "b" * 64,
                       {"steps": ["normalize"]})


def reference():
    return PolicyEvidenceReference("policy-data", "policy-protocol", "v1", "manifest:policy", "builder-v1", "c" * 64)


def test_protocol_recursively_detaches_scope_and_fixes_all_settings():
    nested = {"steps": ["normalize"]}
    item = PolicyScope("m", "v1", "l", "a" * 64, "adapter", "v1", "b" * 64, nested)
    nested["steps"].append("later")
    assert item.preprocessing_identity["steps"] == ("normalize",)
    protocol = PolicySelectionProtocol("p", "v1", (item,), reference(), {"m\0v1\0l": ("target", "v1")}, .1, (.2, .8), 2, 1,
        {0: 1, 1: 1}, ">=", "lowest_cutoff", "lexicographic_assessment_ref_v1", True, "approval-ref")
    assert protocol.digest == PolicySelectionProtocol("p", "v1", (item,), reference(), {"m\0v1\0l": ("target", "v1")}, .1, (.2, .8), 2, 1,
        {0: 1, 1: 1}, ">=", "lowest_cutoff", "lexicographic_assessment_ref_v1", True, "approval-ref").digest
    with pytest.raises(TypeError):
        item.preprocessing_identity["steps"] = ()


def test_protocol_rejects_missing_approval_and_ambiguous_scope():
    with pytest.raises(ValueError):
        PolicySelectionProtocol("p", "v1", (scope(),), reference(), {"m\0v1\0l": ("target", "v1")}, .1, (), 1, 1, {}, ">=", "lowest_cutoff", "lexicographic_assessment_ref_v1", True, "approval")
    with pytest.raises(ValueError):
        PolicySelectionProtocol("p", "v1", (scope(), scope()), reference(), {"m\0v1\0l": ("target", "v1")}, .1, (.5,), 1, 1, {}, ">=", "lowest_cutoff", "lexicographic_assessment_ref_v1", True, "approval")


def test_success_artifact_is_immutable_allowlisted_and_selected_unevaluated():
    dataset_ref = {"dataset_id": "original", "manifest_reference": "mref", "manifest_digest": "c" * 64,
        "protocol_id": "p", "protocol_version": "v1", "builder_version": "b",
        "dataset_fingerprint": "1" * 64, "admitted_inventory_digest": "2" * 64}
    signal_ref = {"run_version": "signals-v1", "feature_set_fingerprint": "3" * 64,
        "method_ids": [["evidence_coverage", "v1", "4" * 64]], "fitted_state_ids": [],
        "scope_key": ["m", "v1", "l"]}
    selection_config = {"risk_ceiling": .1, "candidate_cutoffs": [.8], "target_bindings": {"m\0v1\0l": ["target", "v1"]},
        "minimum_eligible_patients": 2, "minimum_selected_patients": 1,
        "correctness_support": {}, "comparison": ">=", "tie_rule": "lowest_cutoff",
        "index_rule": "lexicographic_assessment_ref_v1", "valid_below_cutoff_status": "CAUTION",
        "invalid_input_status": "DEFER"}
    artifact = SelectivePolicyArtifact(scope(), "p", "v1", "d" * 64, "e" * 64, "f" * 64,
        dataset_ref, signal_ref, reference(), selection_config, PolicySelectionSummary(.8, .05, .5, 5, 10))
    signal_ref["method_ids"].append(["untrusted", "v1", "5" * 64])
    dataset_ref["extra"] = "not accepted"
    selection_config["candidate_cutoffs"].append(.99)
    assert artifact.original_dataset_reference["dataset_id"] == "original"
    assert artifact.selection_configuration["candidate_cutoffs"] == (.8,)
    data = artifact.to_dict()
    data["original_signal_reference"]["method_ids"][0].append("mutated")
    assert artifact.original_signal_reference["method_ids"][0] == ("evidence_coverage", "v1", "4" * 64)
    assert artifact.selection_evidence_spent and not artifact.deployable
    assert not artifact.protected_test_accessed and not artifact.independent_evaluation_complete


def test_empty_selected_set_cannot_be_encoded_as_zero_risk():
    with pytest.raises(ValueError):
        PolicySelectionSummary(.5, 0.0, 0.0, 0, 10)


def test_scope_repr_and_artifact_serialization_exclude_row_level_inputs():
    artifact = SelectivePolicyArtifact(scope(), "p", "v1", "d" * 64, "e" * 64, "f" * 64,
        {"dataset_id": "original", "manifest_reference": "mref", "manifest_digest": "1" * 64,
         "protocol_id": "p", "protocol_version": "v1", "builder_version": "b",
         "dataset_fingerprint": "2" * 64, "admitted_inventory_digest": "3" * 64},
        {"run_version": "signals-v1", "feature_set_fingerprint": "4" * 64,
         "method_ids": [], "fitted_state_ids": [], "scope_key": ["m", "v1", "l"]},
        reference(), {"risk_ceiling": .1, "candidate_cutoffs": [.8],
         "target_bindings": {"m\0v1\0l": ["target", "v1"]}, "minimum_eligible_patients": 2,
         "minimum_selected_patients": 1, "correctness_support": {}, "comparison": ">=",
         "tie_rule": "lowest_cutoff", "index_rule": "lexicographic_assessment_ref_v1",
         "valid_below_cutoff_status": "CAUTION", "invalid_input_status": "DEFER"},
        PolicySelectionSummary(.8, .05, .5, 1, 2))
    surface = repr(artifact) + repr(artifact.scope) + repr(artifact.to_dict())
    for forbidden in ("patient_group_ref", "correctness_target", "raw_evidence", "protected_rows"):
        assert forbidden not in surface
