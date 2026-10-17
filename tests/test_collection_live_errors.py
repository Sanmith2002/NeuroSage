"""Fail-closed live collection and privacy cases on synthetic registrations."""

import pytest

from safira.adapters import AdapterCapabilities
from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.collection.exceptions import ContributorMismatch, InvalidCollectionRequest, InvalidPrimaryOutput
from safira.registry import ModelRegistry
from safira.registry.exceptions import UnknownModelError, UnknownVersionError, UnattachedModelError, BindingMismatchError


@pytest.mark.parametrize("kind,error", [("model", UnknownModelError), ("version", UnknownVersionError),
                                       ("label", ContributorMismatch), ("unattached", UnattachedModelError),
                                       ("incompatible", BindingMismatchError)])
def test_bad_bindings_fail_before_inference(registered_collection, tmp_path, kind, error):
    registry, register = registered_collection
    definition, adapter = register()
    request = [definition.model_id, "v1", "label-a"]
    if kind == "model": request[0] = "unknown"
    if kind == "version": request[1] = "v99"
    if kind == "label": request[2] = "unknown"
    if kind == "incompatible": adapter._capabilities = AdapterCapabilities()
    if kind == "unattached":
        registry = ModelRegistry(tmp_path / "collection.sqlite3")
    try:
        with pytest.raises(error):
            collect_live(registry, CollectionAssociation("p", "a", "o"), [tuple(request)], {"synthetic-feature": [0.4]})
        assert adapter.calls == []
    finally:
        if kind == "unattached": registry.close()


@pytest.mark.parametrize("data,modalities", [({"wrong": [0.2]}, ("synthetic",)),
    ({"synthetic-feature": ["SYNTHETIC_PRIVATE"]}, ("synthetic",)),
    ({"synthetic-feature": [0.1, 0.2]}, ("synthetic",)),
    ({"synthetic-feature": [0.1]}, ("wrong",)), ({"synthetic-feature": [0.1]}, None)])
def test_input_mismatch_before_any_adapter_method(registered_collection, data, modalities):
    registry, register = registered_collection
    definition, adapter = register(modalities=("synthetic",))
    request = LiveRequest(definition.model_id, "v1", "label-a", available_modalities=modalities)
    with pytest.raises(InvalidCollectionRequest) as caught:
        collect_live(registry, CollectionAssociation("p", "a", "o"), [request], data)
    assert "SYNTHETIC_PRIVATE" not in str(caught.value)
    assert adapter.calls == []


@pytest.mark.parametrize("value", [True, "0.4", float("nan"), float("inf"), -0.1, 1.1])
def test_bad_primary_is_atomic_and_preserves_earlier_results(registered_collection, value, caplog):
    registry, register = registered_collection
    definition, adapter = register(labels=("label-a", "label-b"), scores=(0.8, 0.9))
    requests = [(definition.model_id, "v1", label) for label in ("label-a", "label-b")]
    association = CollectionAssociation("SYNTHETIC_PRIVATE_PATIENT", "a", "o")
    result = collect_live(registry, association, requests, {"synthetic-feature": [0.2]})
    snapshot = result.to_dict()
    adapter.classifier.scores["label-b"] = value
    with pytest.raises(InvalidPrimaryOutput) as caught:
        collect_live(registry, association, requests, {"synthetic-feature": [0.2]})
    assert result.to_dict() == snapshot
    assert registry.get_metadata(definition.model_id, "v1") == definition
    assert "SYNTHETIC_PRIVATE" not in str(caught.value) + caplog.text


def test_primary_exception_is_sanitized(registered_collection, monkeypatch, caplog):
    registry, register = registered_collection
    definition, adapter = register()
    def broken(*args): raise RuntimeError("SYNTHETIC_PRIVATE_OBSERVATION")
    monkeypatch.setattr(adapter, "predict_probability", broken)
    with pytest.raises(InvalidPrimaryOutput) as caught:
        collect_live(registry, CollectionAssociation("p", "a", "o"), [(definition.model_id, "v1", "label-a")], {"synthetic-feature": [0.2]})
    assert "SYNTHETIC_PRIVATE" not in str(caught.value) + caplog.text
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("value", [True, "positive", float("nan"), float("inf"), -2.1, 2.1])
def test_score_rejects_invalid_values_without_probability_conversion(registered_collection, value):
    registry, register = registered_collection
    definition, _ = register(kinds=("continuous_score",), scores=(value,))
    with pytest.raises(InvalidPrimaryOutput):
        collect_live(registry, CollectionAssociation("p", "a", "o"),
                     [(definition.model_id, "v1", "label-a")], {"synthetic-feature": [0.2]})


def test_request_preflight_prevents_partial_inference(registered_collection):
    registry, register = registered_collection
    definition, adapter = register()
    key = (definition.model_id, "v1", "label-a")
    for requests in ([key, key], [key, (definition.model_id, "v1", "unknown")], [], ["bad"]):
        with pytest.raises((InvalidCollectionRequest, ContributorMismatch)):
            collect_live(registry, CollectionAssociation("p", "a", "o"), requests, {"synthetic-feature": [0.2]})
        assert adapter.calls == []
