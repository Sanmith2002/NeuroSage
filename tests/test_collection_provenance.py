"""Executed provenance checks must bind exact bytes, contributor and occurrence."""

import json
from dataclasses import replace

import pytest

from collection_fixtures import SyntheticSourceContract, SyntheticTrustedVerifier
from safira.collection import CollectionAssociation, ComponentContribution
from safira.collection.exceptions import ContributorMismatch, ProvenanceCheckFailed


def _setup(registered_collection, *, contract=None, verifier=None):
    registry, register = registered_collection
    register(model_id="external-model")
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration
    contract = contract or SyntheticSourceContract("flat-contract", "v1", "flat")
    verifier = verifier or SyntheticTrustedVerifier()
    return registry, contract, verifier, PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])


def _case(contract, verifier, association=None, selector="external-a", value=0.8, event="event-1", model="external-model", version="v1"):
    association = association or CollectionAssociation("p", "a", "o")
    contribution = ComponentContribution(contract.contract_id, contract.version, selector, model, version, "label-a", 0)
    raw = json.dumps({"schema": contract.version, "selector": selector, "value": value, "event": event})
    candidate = contract.parse(raw).outputs[0]
    verifier.add(event, raw, candidate, contribution, association)
    return association, contribution, raw


def test_positive_check_is_executed_with_exact_scope_and_provenance_is_distinct(registered_collection):
    registry, contract, verifier, collector = _setup(registered_collection)
    association, contribution, raw = _case(contract, verifier)
    result = collector.ingest(association, (contract.contract_id, contract.version), raw, [contribution])
    record = result.records[0]
    assert len(verifier.calls) == 1
    assert verifier.calls[0][0] == raw and verifier.calls[0][-1] == association
    assert record.provenance.mode == "precomputed"
    assert record.provenance.assurance == "trusted_source_checked"
    assert record.provenance.details["event_id"] == "event-1"
    assert record.input_verification == "unavailable"
    assert registry.get_metadata("external-model", "v1")


@pytest.mark.parametrize("mutation", ["content", "contributor", "association", "selector"])
def test_changed_content_contributor_selector_or_association_is_rejected(registered_collection, mutation):
    _, contract, verifier, collector = _setup(registered_collection)
    assoc, contribution, raw = _case(contract, verifier)
    if mutation == "content":
        raw = raw.replace("0.8", "0.7")
    elif mutation == "contributor":
        contribution = ComponentContribution(contract.contract_id, contract.version, "external-a", "other", "v1", "label-a", 0)
    elif mutation == "selector":
        contribution = ComponentContribution(contract.contract_id, contract.version, "external-b", "external-model", "v1", "label-a", 0)
    else:
        assoc = CollectionAssociation("different-p", "a", "o")
    with pytest.raises((ProvenanceCheckFailed, ContributorMismatch)):
        collector.ingest(assoc, (contract.contract_id, contract.version), raw, [contribution])


@pytest.mark.parametrize("status", ["stale", "revoked", "reused", "reassigned"])
def test_stale_revoked_reused_and_reassigned_evidence_fail_closed(registered_collection, status):
    class StatusVerifier(SyntheticTrustedVerifier):
        def check_output_link(self, raw_json, candidate, contributor, label, association):
            check = super().check_output_link(raw_json, candidate, contributor, label, association)
            fields = {"fresh": True, "not_revoked": True, "unused": True}
            fields[{"stale":"fresh", "revoked":"not_revoked", "reused":"unused", "reassigned":"unused"}[status]] = False
            return type(check)(**{**check.__dict__, **fields})
    _, contract, verifier, collector = _setup(registered_collection, verifier=StatusVerifier())
    assoc, contribution, raw = _case(contract, verifier)
    with pytest.raises(ProvenanceCheckFailed):
        collector.ingest(assoc, (contract.contract_id, contract.version), raw, [contribution])


@pytest.mark.parametrize("verifier", [
    type("BooleanVerifier", (), {"integration_id":"bad", "check_output_link":lambda *args: True})(),
    type("AssertionVerifier", (), {"integration_id":"bad", "check_output_link":lambda *args: {"verified": True, "event_id":"caller"}})(),
])
def test_assertion_only_boolean_or_digest_like_result_is_rejected(registered_collection, verifier):
    _, contract, _, collector = _setup(registered_collection, verifier=verifier)
    assoc = CollectionAssociation("p", "a", "o")
    contribution = ComponentContribution(contract.contract_id, contract.version, "external-a", "external-model", "v1", "label-a", 0)
    raw = json.dumps({"schema":"v1", "selector":"external-a", "value":0.8, "event":"caller-event"})
    with pytest.raises(ProvenanceCheckFailed):
        collector.ingest(assoc, (contract.contract_id, contract.version), raw, [contribution])


def test_duplicate_event_ids_within_collection_are_rejected(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model", labels=("label-a", "label-b"), scores=(0.3, 0.7))
    from safira.collection import NormalizedEnvelope, OutputCandidate, PrecomputedCollector, TrustedSourceIntegration

    class TwoOutputContract:
        contract_id = "two-output"
        version = "v1"

        def parse(self, raw_json):
            document = json.loads(raw_json)
            return NormalizedEnvelope((
                OutputCandidate("external-a", document["a"], "probability", "synthetic probability", "increasing", event_id="event-a"),
                OutputCandidate("external-b", document["b"], "probability", "synthetic probability", "increasing", event_id="event-b"),
            ))

        def validate_declarations(self, envelope, declarations):
            return envelope

    class DuplicateEventVerifier(SyntheticTrustedVerifier):
        def check_output_link(self, *args):
            return replace(super().check_output_link(*args), event_id="shared-event")

    contract, verifier = TwoOutputContract(), DuplicateEventVerifier()
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    association = CollectionAssociation("p", "a", "o")
    c1 = ComponentContribution(contract.contract_id, contract.version, "external-a", "external-model", "v1", "label-a", 0)
    c2 = ComponentContribution(contract.contract_id, contract.version, "external-b", "external-model", "v1", "label-b", 1)
    raw = json.dumps({"a":0.8, "b":0.9})
    for candidate, contribution in zip(contract.parse(raw).outputs, (c1, c2)):
        verifier.add(candidate.event_id, raw, candidate, contribution, association)
    with pytest.raises(ProvenanceCheckFailed):
        collector.ingest(association, (contract.contract_id, contract.version), raw, [c1, c2])

