"""Live collection acceptance uses real registry bindings and synthetic models."""

import pytest

from safira.adapters import AdapterCapabilities
from safira.collection import CollectionAssociation, LiveRequest, collect_live


@pytest.mark.parametrize("labels,kinds,scores,methods", [
    (("label-a",), ("probability",), (0.55,), ["predict_probability"]),
    (("label-a",), ("probability",), (0.6,), ["predict_probability"]),
    (("label-a",), ("probability",), (0.0,), ["predict_probability"]),
    (("label-a",), ("probability",), (1.0,), ["predict_probability"]),
    (("label-a",), ("continuous_score",), (-0.4,), ["predict"]),
    (("label-a", "label-b"), ("probability", "probability"), (0.8, 0.9), ["predict_probability"] * 2),
    (("label-a", "label-b"), ("probability", "continuous_score"), (0.55, 0.4), ["predict_probability", "predict"]),
])
def test_exact_live_predictions_preserve_semantics(registered_collection, labels, kinds, scores, methods):
    registry, register = registered_collection
    definition, adapter = register(labels=labels, kinds=kinds, scores=scores)
    association = CollectionAssociation("opaque-patient", "assessment", "occurrence")
    before = definition.to_dict()
    result = collect_live(registry, association,
                          [(definition.model_id, definition.model_version, label) for label in labels],
                          {"synthetic-feature": [0.4]})
    assert adapter.calls == list(zip(methods, labels))
    assert [r.primary.value for r in result.records] == list(scores)
    assert [r.primary.value_kind for r in result.records] == list(kinds)
    for index, record in enumerate(result.records):
        assert record.association == association
        assert record.source_key == (definition.model_id, definition.model_version, labels[index])
        assert record.primary.class_mapping == definition.labels[index].class_mapping
        assert record.primary.predicted_class == ("positive" if scores[index] >= (0.6 if kinds[index] == "probability" else 0) else "negative")
        assert record.input_verification == "validated"
        assert record.provenance.mode == "live"
        assert record.provenance.assurance == "verified_live_binding"
        assert record.provenance.details["classifier_sha256"] == definition.classifier_artifact["sha256"]
        assert all(item.state == "unsupported" and item.value is None for item in record.evidence)
        assert {item.category for item in record.evidence} == {
            "feature_representation", "repeated_outputs", "modality_outputs", "domain_metadata",
            "explanation", "input_metadata", "available_modalities",
        }
        assert "reliability_score" not in record.to_dict()
        assert "status" not in record.to_dict()
    assert registry.get_metadata(definition.model_id, definition.model_version).to_dict() == before


def test_capability_calls_and_initial_states_are_detached(registered_collection):
    registry, register = registered_collection
    supplied = {"feature_representation": [0.2, 0.3], "input_metadata": {"complete": True},
                "explanation": RuntimeError("SYNTHETIC_PRIVATE"), "domain_metadata": None}
    definition, adapter = register(capabilities=AdapterCapabilities(
        prediction_probability=True, feature_representation=True, input_metadata=True,
        explanation=True, domain_metadata=True), evidence=supplied, modalities=("synthetic",))
    meaning = {"feature_representation": {"meaning": "synthetic embedding", "shape": [2]}}
    request = LiveRequest(definition.model_id, definition.model_version, "label-a",
                          available_modalities=("synthetic",), evidence_interpretation=meaning)
    result = collect_live(registry, CollectionAssociation("p", "a", "o"), [request],
                          {"synthetic-feature": [0.4]})
    items = {item.category: item for item in result.records[0].evidence}
    assert items["feature_representation"].state == "available"
    assert items["input_metadata"].state == "available"
    assert items["domain_metadata"].state == "missing"
    assert items["explanation"].state == "unavailable"
    assert items["explanation"].reason_code == "extraction_failed"
    assert items["repeated_outputs"].state == "unsupported"
    assert set(adapter.calls) == {("predict_probability", "label-a"), ("extract_features", "label-a"),
                                  ("get_input_metadata", None), ("explain", "label-a"), ("get_domain_metadata", None)}
    snapshot = result.to_dict()
    supplied["feature_representation"].append(9)
    supplied["input_metadata"]["complete"] = False
    meaning["feature_representation"]["shape"].append(9)
    result.to_dict()["records"][0]["evidence"].clear()
    assert result.to_dict() == snapshot
    assert "SYNTHETIC_PRIVATE" not in str(snapshot)


@pytest.mark.parametrize("value,meaning,expected", [
    ([0.2], {}, "invalid"),
    ([float("nan")], {"meaning": "synthetic", "shape": [1]}, "invalid"),
    (object(), {"meaning": "synthetic"}, "invalid"),
])
def test_uninterpretable_optional_value_retains_primary(registered_collection, value, meaning, expected):
    registry, register = registered_collection
    definition, _ = register(capabilities=AdapterCapabilities(prediction_probability=True, feature_representation=True),
                             evidence={"feature_representation": value})
    request = LiveRequest(definition.model_id, "v1", "label-a", evidence_interpretation={"feature_representation": meaning})
    result = collect_live(registry, CollectionAssociation("p", "a", "o"), [request], {"synthetic-feature": [0.4]})
    assert result.records[0].primary.value == 0.2
    assert next(i for i in result.records[0].evidence if i.category == "feature_representation").state == expected


def test_malformed_optional_container_does_not_leak_or_reject_primary(registered_collection):
    from collections.abc import Mapping

    class BrokenMetadata(Mapping):
        def __iter__(self): raise RuntimeError("SYNTHETIC_PRIVATE")
        def __len__(self): raise RuntimeError("SYNTHETIC_PRIVATE")
        def __getitem__(self, key): raise RuntimeError("SYNTHETIC_PRIVATE")

    registry, register = registered_collection
    definition, _ = register(capabilities=AdapterCapabilities(prediction_probability=True, input_metadata=True),
                             evidence={"input_metadata": BrokenMetadata()})
    result = collect_live(registry, CollectionAssociation("p", "a", "o"),
                          [(definition.model_id, "v1", "label-a")], {"synthetic-feature": [0.2]})
    item = next(i for i in result.records[0].evidence if i.category == "input_metadata")
    assert item.state == "invalid"
    assert item.value is None
    assert "SYNTHETIC_PRIVATE" not in str(result.to_dict())


def test_optional_modality_conflict_is_incomplete_not_silently_validated(registered_collection):
    registry, register = registered_collection
    definition, _ = register(capabilities=AdapterCapabilities(prediction_probability=True, available_modalities=True),
                             evidence={"available_modalities": ["other"]}, modalities=("synthetic",))
    request = LiveRequest(definition.model_id, "v1", "label-a", available_modalities=("synthetic",))
    result = collect_live(registry, CollectionAssociation("p", "a", "o"), [request], {"synthetic-feature": [0.2]})
    item = next(i for i in result.records[0].evidence if i.category == "available_modalities")
    assert item.state == "invalid"
    assert item.reason_code == "source_mismatch"
