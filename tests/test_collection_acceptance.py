"""End-to-end synthetic acceptance across registered model configurations."""

import json

import pytest

from collection_fixtures import SyntheticTrustedVerifier
from safira.collection import (
    CollectionAssociation, ComponentContribution, ComponentIdentity, LiveRequest,
    NormalizedEnvelope, OutputCandidate, PrecomputedCollector, SourceDeclarations,
    TrustedSourceIntegration, collect_live, precomputed_adapter,
)
from safira.collection.exceptions import ProvenanceCheckFailed


class AcceptanceContract:
    """Small versioned batch contract with a layout unrelated to model metadata."""

    contract_id = "synthetic-acceptance-batch"
    version = "test-v1"
    last_envelope = None

    def parse(self, raw_json):
        document = json.loads(raw_json)
        candidates = tuple(OutputCandidate(
            item["path"], item["result"], "probability", "synthetic probability", "increasing",
            event_id=item["event"], evidence=item.get("evidence", {}),
        ) for item in document["entries"])
        self.last_envelope = NormalizedEnvelope(candidates)
        return self.last_envelope

    def validate_declarations(self, envelope, declarations):
        return envelope


@pytest.mark.parametrize("configuration", ["standalone_binary", "multi_label", "multi_model_component"])
def test_synthetic_configurations_match_live_and_precomputed_outputs(registered_collection, configuration):
    registry, register = registered_collection
    component = None
    if configuration == "standalone_binary":
        definitions = [register(model_id="accept-binary", labels=("label-a",), scores=(0.72,))[0]]
        labels = [(definitions[0], "label-a", 0, "external/a")]
    elif configuration == "multi_label":
        definition, _ = register(model_id="accept-multi", labels=("label-a", "label-b"), scores=(0.32, 0.81))
        definitions = [definition]
        labels = [(definition, label, index, f"external/{label}")
                  for index, label in enumerate(("label-a", "label-b"))]
    else:
        first, _ = register(model_id="accept-contributor-a", labels=("shared-label",), scores=(0.41,))
        second, _ = register(model_id="accept-contributor-b", labels=("shared-label",), scores=(0.84,))
        definitions = [first, second]
        labels = [(first, "shared-label", 0, "external/first"),
                  (second, "shared-label", 0, "external/second")]
        component = ComponentIdentity("synthetic-component", "component-test-v1")

    association = CollectionAssociation("opaque-test-patient", "assessment-test", "occurrence-test")
    keys = tuple((definition.model_id, definition.model_version, label) for definition, label, _, _ in labels)
    live = collect_live(
        registry, association,
        [LiveRequest(model_id, version, label) for model_id, version, label in keys],
        {"synthetic-feature": [0.4]}, component=component,
        expected_contributors=keys if component else None,
    )

    contract = AcceptanceContract()
    verifier = SyntheticTrustedVerifier()
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    entries = []
    contributions = []
    for index, (definition, label, selector_index, external) in enumerate(labels):
        value = live.records[index].primary.value
        event = f"accept-event-{index}"
        evidence = {"domain_metadata": {
            "value": {"cohort_in_training_scope": False, "cohort_ref": "synthetic-cohort"},
            "interpretation": {"meaning": "synthetic research scope"},
        }}
        entries.append({"path": external, "result": value, "event": event, "evidence": evidence})
        contributions.append(ComponentContribution(
            contract.contract_id, contract.version, external, definition.model_id,
            definition.model_version, label, selector_index,
        ))
    raw = json.dumps({"entries": entries}, sort_keys=True)
    parsed = contract.parse(raw)
    for candidate, contribution in zip(parsed.outputs, contributions):
        verifier.add(candidate.event_id, raw, candidate, contribution, association)
    declarations = SourceDeclarations(
        tuple(contributions), expected_contributors=keys if component else (),
    )
    precomputed = collector.ingest(association, (contract.contract_id, contract.version), raw,
                                   declarations, component=component)

    assert [record.source_key for record in live.records] == [record.source_key for record in precomputed.records]
    assert [(r.primary.value, r.primary.value_kind, r.primary.predicted_class) for r in live.records] == [
        (r.primary.value, r.primary.value_kind, r.primary.predicted_class) for r in precomputed.records
    ]
    assert all(l.provenance.assurance == "verified_live_binding"
               and p.provenance.assurance == "trusted_source_checked"
               and l.input_verification == "validated"
               and p.input_verification == "unavailable"
               for l, p in zip(live.records, precomputed.records))
    assert all("reliability_score" not in r.to_dict() and "status" not in r.to_dict()
               for r in (*live.records, *precomputed.records))
    domain = next(item for item in precomputed.records[0].evidence if item.category == "domain_metadata")
    assert domain.state == "available"
    assert domain.value["cohort_in_training_scope"] is False

    # Mutating returned nested values does not rewrite accepted records.
    snapshot = precomputed.records[0].to_dict()
    returned = precomputed.to_dict()
    returned_item = next(item for item in returned["records"][0]["evidence"]
                         if item["category"] == "domain_metadata")
    returned_item["value"]["cohort_in_training_scope"] = True
    # The parser's original mutable candidate is caller-owned after admission.
    contract.last_envelope.outputs[0].evidence["domain_metadata"]["value"]["cohort_in_training_scope"] = True
    adapter_view = precomputed_adapter(precomputed.records[0])
    adapter_value = adapter_view.get_domain_metadata(association)
    adapter_value["cohort_in_training_scope"] = True
    assert adapter_view.get_domain_metadata(association)["cohort_in_training_scope"] is False
    assert precomputed.records[0].to_dict() == snapshot


def test_acceptance_rejects_changed_content_without_leaking_private_values(registered_collection):
    registry, register = registered_collection
    definition, _ = register(model_id="accept-private", labels=("label-a",))
    association = CollectionAssociation("opaque-private-ref", "assessment", "occurrence")
    contract, verifier = AcceptanceContract(), SyntheticTrustedVerifier()
    contribution = ComponentContribution(contract.contract_id, contract.version, "external/a",
                                         definition.model_id, definition.model_version, "label-a", 0)
    raw = json.dumps({"entries": [{"path": "external/a", "result": 0.7,
                                  "event": "private-event", "private_note": "SYNTHETIC_PRIVATE_VALUE"}]})
    candidate = OutputCandidate("external/a", 0.7, "probability", "synthetic probability", "increasing",
                                event_id="private-event")
    verifier.add(candidate.event_id, raw, candidate, contribution, association)
    changed = raw.replace("0.7", "0.8")
    collector = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)])
    with pytest.raises(ProvenanceCheckFailed) as error:
        collector.ingest(association, (contract.contract_id, contract.version), changed,
                         SourceDeclarations((contribution,)))
    assert "SYNTHETIC_PRIVATE_VALUE" not in str(error.value)
    assert association.patient_ref not in str(error.value)

