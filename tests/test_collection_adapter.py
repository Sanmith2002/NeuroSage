"""The precomputed adapter is a scoped view over one admitted record."""

import json

import pytest

from collection_fixtures import SyntheticSourceContract, SyntheticTrustedVerifier
from safira.collection import CollectionAssociation
from safira.collection.exceptions import EvidenceUnavailable, InvalidCollectionRequest


def test_adapter_returns_only_saved_values_for_exact_label_and_occurrence(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration, precomputed_adapter
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    association = CollectionAssociation("p", "a", "occurrence-1")
    from safira.collection import ComponentContribution
    contribution = ComponentContribution("flat", "v1", "external-a", "external-model", "v1", "label-a", 0)
    raw = json.dumps({"schema":"v1", "selector":"external-a", "value":0.8, "event":"event-1"})
    verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    result = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)]).ingest(
        association, ("flat", "v1"), raw, [contribution])
    view = precomputed_adapter(result.records[0])
    assert view.predict_probability(association, "label-a") == 0.8
    assert view.capabilities.prediction_probability is True
    assert view.capabilities.feature_representation is False
    with pytest.raises(InvalidCollectionRequest):
        view.predict_probability(association, "another-label")
    with pytest.raises(InvalidCollectionRequest):
        view.predict_probability(CollectionAssociation("p", "a", "occurrence-2"), "label-a")
    with pytest.raises(EvidenceUnavailable):
        view.extract_features(association, "label-a")


def test_adapter_defensive_copy_and_no_classifier_inference(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration, precomputed_adapter, ComponentContribution
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    association = CollectionAssociation("p", "a", "o")
    contribution = ComponentContribution("flat", "v1", "external-a", "external-model", "v1", "label-a", 0)
    raw = json.dumps({"schema":"v1", "selector":"external-a", "value":0.8, "event":"event-1"})
    verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    record = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)]).ingest(
        association, ("flat", "v1"), raw, [contribution]).records[0]
    view = precomputed_adapter(record)
    before = view.predict_probability(association, "label-a")
    assert before == 0.8
    assert view.predict(association, "label-a") == "positive"
    assert record.to_dict() == record.to_dict()


def test_score_adapter_preserves_score_and_does_not_advertise_probability(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model", kinds=("continuous_score",), scores=(0.4,))
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration, precomputed_adapter, ComponentContribution
    contract, verifier = SyntheticSourceContract("score", "v1", "flat"), SyntheticTrustedVerifier()
    association = CollectionAssociation("p", "a", "o")
    contribution = ComponentContribution("score", "v1", "external-a", "external-model", "v1", "label-a", 0)
    raw = json.dumps({"schema":"v1", "selector":"external-a", "value":0.4, "event":"event-1"})
    from safira.collection.precomputed import NormalizedEnvelope, OutputCandidate
    contract.parse = lambda raw_json: NormalizedEnvelope((OutputCandidate(
        "external-a", json.loads(raw_json)["value"], "continuous_score", "synthetic margin", "increasing",
        event_id=json.loads(raw_json)["event"]),))
    contract.validate_declarations = lambda envelope, declarations: envelope
    verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    record = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)]).ingest(
        association, ("score", "v1"), raw, [contribution]).records[0]
    view = precomputed_adapter(record)
    assert view.predict(association, "label-a") == 0.4
    assert view.capabilities.prediction_probability is False
    with pytest.raises(EvidenceUnavailable):
        view.predict_probability(association, "label-a")

