"""Compatibility projection tests for the existing SafetyContext contract."""

from safira.collection import CollectionAssociation, LiveRequest, collect_live, to_safety_context
from safira.adapters import AdapterCapabilities


def test_probability_projection_is_detached_and_preserves_exact_evidence_states(registered_collection):
    registry, register = registered_collection
    definition, _ = register(model_id="context-model", capabilities=AdapterCapabilities(
        prediction_probability=True, input_metadata=True), evidence={"input_metadata": {"complete": True}})
    association = CollectionAssociation("opaque-patient", "assessment-1", "occurrence-7")
    record = collect_live(registry, association,
                          [LiveRequest(definition.model_id, "v1", "label-a")],
                          {"synthetic-feature": [0.3]}).records[0]
    context = to_safety_context(record, patient_data={"synthetic": [1]})
    assert context.patient_id == "opaque-patient"
    assert context.label == "label-a"
    assert context.prediction_probability == record.primary.value
    assert context.model_metadata["safira_collection"]["source_key"] == ["context-model", "v1", "label-a"]
    states = context.model_metadata["safira_collection"]["evidence_states"]
    assert states["input_metadata"] == "available"
    assert states["explanation"] == "unsupported"
    context.model_metadata["safira_collection"]["source_key"][0] = "changed"
    context.input_metadata["complete"] = False
    context.patient_data["synthetic"].append(2)
    assert record.source_key[0] == "context-model"
    assert record.evidence[5].value["complete"] is True
    assert record.association.patient_ref == "opaque-patient"
    assert "reliability_score" not in context.model_metadata
    assert "status" not in context.model_metadata


def test_continuous_score_never_populates_probability_field(registered_collection):
    registry, register = registered_collection
    definition, _ = register(model_id="score-context", kinds=("continuous_score",), scores=(-0.4,))
    record = collect_live(registry, CollectionAssociation("p", "a", "o"),
                          [(definition.model_id, "v1", "label-a")],
                          {"synthetic-feature": [0.2]}).records[0]
    context = to_safety_context(record)
    assert context.prediction_probability is None
    assert context.model_metadata["safira_collection"]["continuous_score"]["value"] == -0.4
    assert context.model_metadata["safira_collection"]["primary"]["value_kind"] == "continuous_score"

