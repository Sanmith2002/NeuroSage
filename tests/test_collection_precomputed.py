"""Precomputed values use exact metadata and never load/call the classifier."""

import json
import subprocess
import sys

import pytest

from collection_fixtures import SyntheticSourceContract, SyntheticTrustedVerifier
from safira.collection import CollectionAssociation, ComponentContribution
from safira.collection.exceptions import ContributorMismatch, InvalidPrimaryOutput, ProvenanceCheckFailed, UnknownSourceContract


def _build(registry, contract, verifier):
    from safira.collection import PrecomputedCollector, TrustedSourceIntegration
    return PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])


def _payload(contract, *, value=0.8, selector="external-a", event="event-1", supplied_class=None):
    doc = {"schema": contract.version, "selector": selector, "value": value, "event": event}
    if supplied_class is not None:
        doc["class"] = supplied_class
    return json.dumps(doc)


def _contribution(contract, *, model="external-model", version="v1", label="label-a", selector="external-a", registered_selector=0):
    return ComponentContribution(contract.contract_id, contract.version, selector, model, version, label, registered_selector)


def test_metadata_survives_real_subprocess_restart_without_restoring_binding(registered_collection, tmp_path):
    registry, register = registered_collection
    definition, _adapter = register(model_id="external-model")
    db_path = tmp_path / "collection.sqlite3"
    registry.close()
    script = (
        "from safira.registry import ModelRegistry; import json; "
        f"r=ModelRegistry({str(db_path)!r}); "
        f"d=r.get_metadata({definition.model_id!r}, {definition.model_version!r}); "
        "print(json.dumps({'model_id':d.model_id,'version':d.model_version})); "
        f"r.resolve_usable({definition.model_id!r}, {definition.model_version!r})"
    )
    process = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert process.returncode != 0
    assert 'UnattachedModelError' in process.stderr
    assert f'"model_id": "{definition.model_id}"' in process.stdout
    from safira.registry import ModelRegistry
    reopened = ModelRegistry(db_path)
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    collector = _build(reopened, contract, verifier)
    association = CollectionAssociation("p", "a", "o")
    contribution = _contribution(contract)
    raw = _payload(contract)
    verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    record = collector.ingest(association, ("flat", "v1"), raw, [contribution]).records[0]
    assert record.primary.value == 0.8
    reopened.close()


def test_registered_primary_mapping_semantics_and_immutable_admission(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model", labels=("label-a", "label-b"), scores=(0.75, 0.4))
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    collector = _build(registry, contract, verifier)
    association = CollectionAssociation("p", "a", "o")
    declarations = [_contribution(contract, label="label-a"), _contribution(contract, label="label-b", selector="external-b", registered_selector=1)]
    # Synthetic flat contract can be extended by a contract-specific parser; one candidate is enough here.
    raw = _payload(contract, value=0.75)
    candidate = contract.parse(raw).outputs[0]
    verifier.add("event-1", raw, candidate, declarations[0], association)
    result = collector.ingest(association, ("flat", "v1"), raw, [declarations[0]])
    snapshot = result.to_dict()
    assert result.records[0].primary.predicted_class == "positive"
    assert result.records[0].input_verification == "unavailable"
    assert {item.state for item in result.records[0].evidence} == {"missing"}
    assert "reliability_score" not in snapshot["records"][0]
    snapshot["records"][0]["primary"]["scale"]["meaning"] = "changed"
    assert result.to_dict()["records"][0]["primary"]["meaning"] != "changed"


def test_live_and_precomputed_primary_meaning_match_but_assurance_remains_distinct(registered_collection):
    registry, register = registered_collection
    definition, adapter = register(model_id="external-model", scores=(0.8,))
    association = CollectionAssociation("p", "a", "o")
    from safira.collection import collect_live
    live = collect_live(registry, association, [("external-model", "v1", "label-a")],
                       {"synthetic-feature": [0.2]}).records[0]
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    contribution = _contribution(contract)
    raw = _payload(contract, value=0.8)
    verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    precomputed = _build(registry, contract, verifier).ingest(association, ("flat", "v1"), raw, [contribution]).records[0]
    assert (live.primary.value, live.primary.value_kind, live.primary.predicted_class, live.primary.meaning) == (
        precomputed.primary.value, precomputed.primary.value_kind, precomputed.primary.predicted_class, precomputed.primary.meaning)
    assert live.provenance.assurance != precomputed.provenance.assurance
    assert adapter.calls.count(("predict_probability", "label-a")) == 1


def test_external_class_declaration_must_match_registered_mapping(registered_collection):
    registry, register = registered_collection
    register(model_id="external-model")
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    association, contribution = CollectionAssociation("p", "a", "o"), _contribution(contract)
    raw = _payload(contract, value=0.8)
    # The payload's declared class contradicts the registered >= 0.6 mapping.
    raw = json.dumps({"schema":"v1", "selector":"external-a", "value":0.8,
                      "class":"negative", "event":"event-1"})
    verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    with pytest.raises(InvalidPrimaryOutput):
        _build(registry, contract, verifier).ingest(association, ("flat", "v1"), raw, [contribution])


@pytest.mark.parametrize("declared", ["unknown-model", "external-model"])
def test_unregistered_contributor_or_missing_mapping_rejected_without_fallback(registered_collection, declared):
    registry, register = registered_collection
    register(model_id="external-model")
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    collector = _build(registry, contract, verifier)
    association = CollectionAssociation("p", "a", "o")
    contribution = _contribution(contract, model=declared)
    raw = _payload(contract)
    if declared == "unknown-model":
        verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    with pytest.raises((ContributorMismatch, ProvenanceCheckFailed)):
        collector.ingest(association, ("flat", "v1"), raw, [contribution])


@pytest.mark.parametrize("value", [True, "0.8", float("nan"), float("inf"), 1.01])
def test_invalid_primary_fails_without_partial_result(registered_collection, value):
    registry, register = registered_collection
    register(model_id="external-model")
    contract, verifier = SyntheticSourceContract("flat", "v1", "flat"), SyntheticTrustedVerifier()
    collector = _build(registry, contract, verifier)
    association = CollectionAssociation("p", "a", "o")
    contribution = _contribution(contract)
    raw = _payload(contract, value=value)
    verifier.add("event-1", raw, contract.parse(raw).outputs[0], contribution, association)
    with pytest.raises(UnknownSourceContract if type(value) is float and (value != value or value in (float("inf"), float("-inf"))) else InvalidPrimaryOutput):
        collector.ingest(association, ("flat", "v1"), raw, [contribution])

