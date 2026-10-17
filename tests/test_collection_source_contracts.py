"""Generic source contract selection and strict JSON admission tests."""

import json

import pytest

from collection_fixtures import SyntheticSourceContract, SyntheticTrustedVerifier
from safira.collection import CollectionAssociation, ComponentContribution
from safira.collection.exceptions import InvalidCollectionRequest, UnknownSourceContract


def _declaration(contract, selector="external-a"):
    return ComponentContribution(contract.contract_id, contract.version, selector,
                                 "external-model", "v1", "label-a", 0)


def _payload(contract, selector="external-a", value=0.8, event="event-1"):
    if contract.layout == "flat":
        return json.dumps({"schema": contract.version, "selector": selector, "value": value, "event": event})
    return json.dumps({"release": contract.version, "items": [{"path": selector, "reading": value, "event": event}]})


def test_two_unrelated_layouts_and_exact_contract_selection(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration
    association = CollectionAssociation("opaque-p", "assessment", "occurrence")
    contracts = [SyntheticSourceContract("flat-contract", "v1", "flat"),
                 SyntheticSourceContract("nested-contract", "v1", "nested")]
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(c, SyntheticTrustedVerifier()) for c in contracts])
    assert collector.contract_keys == frozenset({("flat-contract", "v1"), ("nested-contract", "v1")})
    for contract in contracts:
        raw = _payload(contract)
        contribution = _declaration(contract)
        verifier = collector._integrations[(contract.contract_id, contract.version)].verifier
        verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
        assert collector.ingest(association, (contract.contract_id, contract.version), raw,
                                [contribution]).records[0].primary.value == 0.8


def test_collector_isolation_and_no_payload_or_call_handler_installation(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration
    association = CollectionAssociation("p", "a", "o")
    c1, c2 = SyntheticSourceContract("c1", "1", "flat"), SyntheticSourceContract("c2", "1", "flat")
    v1, v2 = SyntheticTrustedVerifier(), SyntheticTrustedVerifier()
    first = PrecomputedCollector(registry, [TrustedSourceIntegration(c1, v1)])
    second = PrecomputedCollector(registry, [TrustedSourceIntegration(c2, v2)])
    with pytest.raises(UnknownSourceContract):
        first.ingest(association, ("c2", "1"), _payload(c2), [_declaration(c2)])
    with pytest.raises((TypeError, InvalidCollectionRequest)):
        first.ingest(association, ("c1", "1"), _payload(c1), [_declaration(c1)], verifier=v2)
    with pytest.raises(UnknownSourceContract):
        first.ingest(association, ("c1", "2"), _payload(c1), [_declaration(c1)])
    assert len(v1.calls) == len(v2.calls) == 0
    assert second.contract_keys == frozenset({("c2", "1")})


def test_duplicate_conflicting_contract_keys_rejected(registered_collection):
    registry, _ = registered_collection
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration
    c1, c2 = SyntheticSourceContract("same", "1", "flat"), SyntheticSourceContract("same", "1", "nested")
    with pytest.raises(InvalidCollectionRequest):
        PrecomputedCollector(registry, [TrustedSourceIntegration(c1, SyntheticTrustedVerifier()),
                                        TrustedSourceIntegration(c2, SyntheticTrustedVerifier())])


@pytest.mark.parametrize("raw", [
    '{"schema":"v1","selector":"external-a","selector":"external-b","value":0.8,"event":"e"}',
    '{"schema":"v1","selector":"external-a","value":NaN,"event":"e"}',
    '{"schema":"v1","selector":"external-a","value":Infinity,"event":"e"}',
])
def test_duplicate_members_and_nonfinite_json_rejected_before_verification(registered_collection, raw):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration
    contract, verifier = SyntheticSourceContract("flat-contract", "v1", "flat"), SyntheticTrustedVerifier()
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    with pytest.raises(UnknownSourceContract):
        collector.ingest(CollectionAssociation("p", "a", "o"), ("flat-contract", "v1"), raw, [_declaration(contract)])
    assert verifier.calls == []


def test_required_fields_extensions_and_association_declaration_are_contract_scoped(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration, SourceDeclarations
    contract, verifier = SyntheticSourceContract("flat-contract", "v1", "flat"), SyntheticTrustedVerifier()
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    assoc = CollectionAssociation("p", "a", "o")
    declaration = _declaration(contract)
    with pytest.raises(UnknownSourceContract):
        collector.ingest(assoc, ("flat-contract", "v1"), '{"schema":"v1","selector":"external-a"}', [declaration])
    with pytest.raises(UnknownSourceContract):
        collector.ingest(assoc, ("flat-contract", "v1"), _payload(contract)[:-1] + ',"unknown":"x"}', [declaration])
    matching = json.dumps({"schema":"v1","selector":"external-a","value":0.8,"event":"event-1",
                           "association":["p","a","o"]})
    verifier.add("event-1", matching, type("C", (), {"external_selector":"external-a","source_key":declaration.source_key})(),
                 type("D", (), {"source_key":declaration.source_key})(), assoc)
    out = collector.ingest(assoc, ("flat-contract", "v1"), matching,
                           SourceDeclarations((declaration,), association=assoc))
    assert out.records[0].association == assoc
    conflict = CollectionAssociation("p", "a", "other")
    with pytest.raises(InvalidCollectionRequest):
        collector.ingest(assoc, ("flat-contract", "v1"), matching,
                         SourceDeclarations((declaration,), association=conflict))


def test_duplicate_contribution_declarations_fail_without_inferred_meaning(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration, SourceDeclarations
    contract, verifier = SyntheticSourceContract("flat-contract", "v1", "flat"), SyntheticTrustedVerifier()
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    declaration = _declaration(contract)
    from safira.collection.exceptions import ContributorMismatch
    with pytest.raises(ContributorMismatch):
        collector.ingest(CollectionAssociation("p", "a", "o"), ("flat-contract", "v1"), _payload(contract),
                         SourceDeclarations((declaration, declaration)))


def test_separate_meaning_declaration_is_required_and_must_match_registration(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration, SourceDeclarations
    from safira.collection.exceptions import ContributorMismatch
    import json
    contract = SyntheticSourceContract("flat-contract", "v1", "flat")
    original_parse = contract.parse
    def parse_without_meaning(raw_json):
        document = json.loads(raw_json)
        parsed = original_parse(raw_json)
        return type(parsed)((type(parsed.outputs[0])("external-a", document["value"], "", "", "",
                                                     event_id=document.get("event")),), parsed.association)
    contract.parse = parse_without_meaning
    verifier = SyntheticTrustedVerifier()
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    association, declaration = CollectionAssociation("p", "a", "o"), _declaration(contract)
    raw = _payload(contract)
    candidate = contract.parse(raw).outputs[0]
    verifier.add("event-1", raw, candidate, declaration, association)
    declarations = SourceDeclarations((declaration,), meanings={"external-a": {
        "value_kind":"probability", "meaning":"synthetic probability", "positive_direction":"increasing"}})
    assert collector.ingest(association, ("flat-contract", "v1"), raw, declarations).records[0].primary.value == 0.8
    wrong = SourceDeclarations((declaration,), meanings={"external-a": {
        "value_kind":"probability", "meaning":"different meaning", "positive_direction":"increasing"}})
    with pytest.raises(ContributorMismatch):
        collector.ingest(association, ("flat-contract", "v1"), raw, wrong)

