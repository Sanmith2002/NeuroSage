"""Component records remain independently attributable and complete or fail."""

import json

import pytest

from collection_fixtures import SyntheticTrustedVerifier
from safira.collection import CollectionAssociation, ComponentContribution, ComponentIdentity
from safira.collection.exceptions import ContributorMismatch, InvalidCollectionRequest, UnknownSourceContract


class ComponentContract:
    contract_id = "synthetic-component-export"
    version = "contract-v7"

    def parse(self, raw_json):
        from safira.collection.precomputed import NormalizedEnvelope, OutputCandidate
        doc = json.loads(raw_json)
        candidates = tuple(OutputCandidate(
            item["selector"], item["value"], item.get("value_kind", "probability"),
            item.get("meaning", "synthetic probability"), item.get("direction", "increasing"),
            supplied_class=item.get("class"), event_id=item["event"],
        ) for item in doc["outputs"])
        association = tuple(doc["association"]) if "association" in doc else None
        return NormalizedEnvelope(candidates, association)

    def validate_declarations(self, envelope, declarations):
        return envelope


def _register_models(register, definitions):
    registered = {}
    for model_id, version, labels in definitions:
        definition, adapter = register(model_id=model_id, version=version, labels=labels,
                                       kinds=("probability",) * len(labels),
                                       scores=tuple(0.15 + index * 0.2 for index in range(len(labels))))
        registered[(model_id, version)] = (definition, adapter)
    return registered


def _payload(association, specs, embedded_association=None):
    outputs = [{"selector": external, "value": value, "event": event} for external, value, event, *_ in specs]
    source_association = embedded_association or association
    return json.dumps({"association": [source_association.patient_ref, source_association.assessment_ref, source_association.occurrence_ref],
                       "outputs": outputs})


def _contributions(specs, contract):
    return tuple(ComponentContribution(contract.contract_id, contract.version, external,
                                       model_id, version, label_id, selector)
                 for external, _value, _event, model_id, version, label_id, selector in specs)


def _ingest(registry, contract, verifier, association, specs, expected=None, component=None,
            embedded_association=None):
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration, SourceDeclarations
    raw = _payload(association, specs, embedded_association)
    declarations = _contributions(specs, contract)
    for candidate, contribution in zip(contract.parse(raw).outputs, declarations):
        verifier.add(candidate.event_id, raw, candidate, contribution, association)
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    return collector.ingest(association, (contract.contract_id, contract.version), raw,
                           SourceDeclarations(declarations, expected_contributors=tuple(expected or ())),
                           component=component)


@pytest.mark.parametrize("count", [2, 4])
def test_arbitrary_all_single_label_component_contributors_remain_distinct(registered_collection, count):
    registry, register = registered_collection
    definitions = [(f"model-{index}", "v1", ("shared-label",)) for index in range(count)]
    _register_models(register, definitions)
    association = CollectionAssociation("opaque-patient", "assessment", "occurrence")
    component = ComponentIdentity("synthetic-component", "component-v3")
    contract, verifier = ComponentContract(), SyntheticTrustedVerifier()
    specs = [(f"external/path/{index}", 0.25 + index * 0.1, f"event-{index}", model, "v1", "shared-label", 0)
             for index, (model, _, _) in enumerate(definitions)]
    keys = tuple((s[3], s[4], s[5]) for s in specs)
    result = _ingest(registry, contract, verifier, association, specs, keys, component)
    assert len(result.records) == count
    assert [record.source_key for record in result.records] == list(keys)
    assert [record.primary.value for record in result.records] == [spec[1] for spec in specs]
    assert all(record.component == component for record in result.records)
    assert all(record.association == association for record in result.records)


def test_mixed_single_and_multilabel_component_keeps_overlapping_labels_and_versions(registered_collection):
    registry, register = registered_collection
    _register_models(register, [
        ("model-a", "v1", ("label-a",)),
        ("model-a", "v2", ("label-a",)),
        ("model-b", "v1", ("label-a",)),
        ("model-c", "v1", ("label-a", "label-b")),
    ])
    association = CollectionAssociation("p", "assessment", "occurrence")
    component = ComponentIdentity("mixed-component", "component-v1")
    contract, verifier = ComponentContract(), SyntheticTrustedVerifier()
    specs = [
        ("external/a-v1", 0.21, "evt-1", "model-a", "v1", "label-a", 0),
        ("external/a-v2", 0.39, "evt-2", "model-a", "v2", "label-a", 0),
        ("external/b", 0.62, "evt-3", "model-b", "v1", "label-a", 0),
        ("external/c-a", 0.77, "evt-4", "model-c", "v1", "label-a", 0),
        ("external/c-b", 0.88, "evt-5", "model-c", "v1", "label-b", 1),
    ]
    keys = tuple((s[3], s[4], s[5]) for s in specs)
    result = _ingest(registry, contract, verifier, association, specs, keys, component)
    assert len(result.records) == 5
    assert len({record.source_key for record in result.records}) == 5
    assert [r.primary.value for r in result.records] == [s[1] for s in specs]
    assert [r.primary.predicted_class for r in result.records] == ["negative", "negative", "positive", "positive", "positive"]
    assert all(r.component == component for r in result.records)
    assert len({r.component.component_version for r in result.records}) == 1


def test_component_expected_contributor_set_must_be_complete(registered_collection):
    registry, register = registered_collection
    _register_models(register, [("model-a", "v1", ("label-a",)), ("model-b", "v1", ("label-a",))])
    association = CollectionAssociation("p", "a", "o")
    contract, verifier = ComponentContract(), SyntheticTrustedVerifier()
    partial = [("external/a", 0.8, "event-a", "model-a", "v1", "label-a", 0)]
    expected = (("model-a", "v1", "label-a"), ("model-b", "v1", "label-a"))
    with pytest.raises(ContributorMismatch):
        _ingest(registry, contract, verifier, association, partial, expected,
                ComponentIdentity("component", "v1"))


def test_component_cannot_claim_completeness_without_an_expected_set(registered_collection):
    registry, register = registered_collection
    _register_models(register, [("model-a", "v1", ("label-a",))])
    association = CollectionAssociation("p", "a", "o")
    contract, verifier = ComponentContract(), SyntheticTrustedVerifier()
    specs = [("external/a", 0.8, "event-a", "model-a", "v1", "label-a", 0)]
    with pytest.raises(ContributorMismatch):
        _ingest(registry, contract, verifier, association, specs, component=ComponentIdentity("component", "v1"))


def test_component_output_semantics_must_match_exact_registered_label(registered_collection):
    registry, register = registered_collection
    _register_models(register, [("model-a", "v1", ("label-a",))])
    association = CollectionAssociation("p", "a", "o")
    contract, verifier = ComponentContract(), SyntheticTrustedVerifier()
    contribution = ComponentContribution(contract.contract_id, contract.version, "external/a",
                                         "model-a", "v1", "label-a", 0)
    raw = json.dumps({"association":["p","a","o"], "outputs":[{
        "selector":"external/a", "value":0.8, "event":"event-a",
        "value_kind":"continuous_score", "meaning":"synthetic margin"}]})
    verifier.add("event-a", raw, contract.parse(raw).outputs[0], contribution, association)
    from safira.collection import PrecomputedCollector, SourceDeclarations, TrustedSourceIntegration
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    with pytest.raises(ContributorMismatch):
        collector.ingest(association, (contract.contract_id, contract.version), raw,
                         SourceDeclarations((contribution,), expected_contributors=(contribution.source_key,)),
                         component=ComponentIdentity("component", "v1"))


@pytest.mark.parametrize("mutation", ["unknown-version", "wrong-selector", "duplicate-selector", "duplicate-source"])
def test_ambiguous_or_conflicting_contributor_mapping_fails_atomically(registered_collection, mutation):
    registry, register = registered_collection
    _register_models(register, [("model-a", "v1", ("label-a",)), ("model-b", "v1", ("label-a",))])
    association = CollectionAssociation("p", "a", "o")
    contract, verifier = ComponentContract(), SyntheticTrustedVerifier()
    specs = [
        ("external/a", 0.8, "event-a", "model-a", "v1", "label-a", 0),
        ("external/b", 0.6, "event-b", "model-b", "v1", "label-a", 0),
    ]
    if mutation == "unknown-version":
        specs[0] = ("external/a", 0.8, "event-a", "model-a", "latest", "label-a", 0)
    elif mutation == "wrong-selector":
        specs[0] = ("external/a", 0.8, "event-a", "model-a", "v1", "label-a", "another-output")
    elif mutation == "duplicate-selector":
        specs[1] = ("external/a", 0.6, "event-b", "model-b", "v1", "label-a", 0)
    else:
        specs[1] = ("external/b", 0.6, "event-b", "model-a", "v1", "label-a", 0)
    with pytest.raises((ContributorMismatch, InvalidCollectionRequest)):
        _ingest(registry, contract, verifier, association, specs,
                tuple((s[3], s[4], s[5]) for s in specs), ComponentIdentity("component", "v1"))
    assert verifier.calls == []


def test_mixed_associations_and_invalid_provenance_reject_entire_component(registered_collection):
    registry, register = registered_collection
    _register_models(register, [("model-a", "v1", ("label-a",)), ("model-b", "v1", ("label-a",))])
    association = CollectionAssociation("p", "a", "o")
    contract, verifier = ComponentContract(), SyntheticTrustedVerifier()
    specs = [("ext-a", 0.8, "event-a", "model-a", "v1", "label-a", 0),
             ("ext-b", 0.7, "event-b", "model-b", "v1", "label-a", 0)]
    result = _ingest(registry, contract, verifier, association, specs,
                     tuple((s[3], s[4], s[5]) for s in specs), ComponentIdentity("component", "v1"))
    assert len(result.records) == 2
    changed = CollectionAssociation("different-patient", "a", "o")
    with pytest.raises(UnknownSourceContract):
        _ingest(registry, contract, SyntheticTrustedVerifier(), association, specs,
                tuple((s[3], s[4], s[5]) for s in specs), ComponentIdentity("component", "v1"),
                embedded_association=changed)


def test_live_component_records_keep_exact_contributors_and_require_complete_set(registered_collection):
    registry, register = registered_collection
    _register_models(register, [("live-a", "v1", ("shared",)), ("live-b", "v1", ("shared",))])
    from safira.collection import LiveRequest, collect_live
    association = CollectionAssociation("p", "a", "o")
    component = ComponentIdentity("live-component", "v2")
    expected = (("live-a", "v1", "shared"), ("live-b", "v1", "shared"))
    result = collect_live(registry, association,
                          [LiveRequest("live-a", "v1", "shared"), LiveRequest("live-b", "v1", "shared")],
                          {"synthetic-feature": [0.4]}, component=component,
                          expected_contributors=expected)
    assert [r.source_key for r in result.records] == list(expected)
    assert [r.primary.value for r in result.records] == [0.15, 0.15]
    assert all(r.component == component for r in result.records)
    with pytest.raises(ContributorMismatch):
        collect_live(registry, association, [LiveRequest("live-a", "v1", "shared")],
                     {"synthetic-feature": [0.4]}, component=component,
                     expected_contributors=expected)
