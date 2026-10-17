"""Evidence inspection behavior using synthetic adapters and source records."""

import pytest

from safira.adapters import AdapterCapabilities
from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.collection.precomputed import (
    NormalizedEnvelope, OutputCandidate, PrecomputedCollector, SourceDeclarations,
    SourceContract, TrustedSourceIntegration,
)


def _interpretations():
    return {
        "feature_representation": {"meaning": "synthetic embedding", "shape": [2], "representation_id": "embed-v1"},
        "repeated_outputs": {"meaning": "independent stochastic runs", "repeat_ids": ["r1", "r2"], "provenance": "synthetic-run-ledger"},
        "modality_outputs": {"meaning": "per-modality scores", "modality_ids": ["mri", "clinical"], "output_space": "probability"},
        "domain_metadata": {"meaning": "source cohort scope"},
        "input_metadata": {"meaning": "input completeness"},
        "available_modalities": {"meaning": "observed modality identifiers"},
        "explanation": {"meaning": "feature attribution", "target_label": "label-a", "target_output": "raw-score", "method": "synthetic-shap", "output_space": "uncalibrated_logit", "calibrated": False, "truncated": True},
    }


def test_live_evidence_categories_are_validated_with_meaning_and_provenance(registered_collection):
    registry, register = registered_collection
    evidence = {
        "feature_representation": [0.2, 0.4],
        "repeated_outputs": [0.3, 0.5],
        "modality_outputs": {"mri": 0.4, "clinical": 0.7},
        "domain_metadata": {"cohort_in_training_scope": False, "cohort": "synthetic"},
        "input_metadata": {"completeness": 0.8},
        "available_modalities": ["mri", "clinical"],
        "explanation": {"attributions": [0.1, -0.2]},
    }
    definition, _ = register(capabilities=AdapterCapabilities(
        prediction_probability=True, feature_representation=True, repeated_outputs=True,
        modality_outputs=True, domain_metadata=True, input_metadata=True,
        available_modalities=True, explanation=True,
    ), evidence=evidence, modalities=("mri", "clinical"))
    association = CollectionAssociation("p-opaque", "a-1", "o-1")
    req = LiveRequest(definition.model_id, "v1", "label-a", ("mri", "clinical"), _interpretations())
    record = collect_live(registry, association, [req], {"synthetic-feature": [0.5]}).records[0]
    items = {i.category: i for i in record.evidence}
    assert all(item.state == "available" for item in items.values())
    assert items["repeated_outputs"].interpretation["provenance"] == "synthetic-run-ledger"
    assert items["modality_outputs"].interpretation["modality_ids"] == ("mri", "clinical")
    assert items["explanation"].interpretation["output_space"] == "uncalibrated_logit"
    assert items["explanation"].interpretation["calibrated"] is False
    assert items["explanation"].interpretation["truncated"] is True
    assert items["domain_metadata"].value["cohort_in_training_scope"] is False


def test_capability_states_missing_unavailable_and_invalid_preserve_primary(registered_collection):
    registry, register = registered_collection
    definition, _ = register(capabilities=AdapterCapabilities(
        prediction_probability=True, feature_representation=True, explanation=True,
        domain_metadata=True,
    ), evidence={"feature_representation": None, "explanation": RuntimeError("SYNTHETIC_PRIVATE"),
                 "domain_metadata": {"cohort_in_training_scope": True}}, modalities=("synthetic",))
    req = LiveRequest(definition.model_id, "v1", "label-a", ("synthetic",), {
        "domain_metadata": {"meaning": "cohort scope"},
        "explanation": {"meaning": "attribution", "target_label": "label-a", "target_output": "probability",
                        "method": "synthetic", "output_space": "probability", "calibrated": True},
    })
    record = collect_live(registry, CollectionAssociation("p", "a", "o"), [req],
                          {"synthetic-feature": [0.3]}).records[0]
    items = {i.category: i for i in record.evidence}
    assert record.primary.value == 0.2
    assert items["feature_representation"].state == "missing"
    assert items["explanation"].state == "unavailable"
    assert items["domain_metadata"].state == "available"
    assert items["repeated_outputs"].state == "unsupported"
    assert "SYNTHETIC_PRIVATE" not in str(record.to_dict())


@pytest.mark.parametrize("category,value,interpretation", [
    ("feature_representation", [float("nan")], {"meaning": "embedding", "shape": [1]}),
    ("repeated_outputs", [0.2, 0.3], {"meaning": "repeat", "repeat_ids": ["same"], "provenance": "ledger"}),
    ("modality_outputs", {"mri": 0.2, "clinical": float("inf")}, {"meaning": "scores", "modality_ids": ["mri", "clinical"], "output_space": "probability"}),
    ("explanation", {"attributions": [0.2]}, {"meaning": "explanation", "method": "shap", "target_label": "other", "target_output": "p", "output_space": "uncalibrated", "calibrated": False}),
])
def test_invalid_optional_evidence_does_not_reject_valid_primary(registered_collection, category, value, interpretation):
    registry, register = registered_collection
    definition, _ = register(capabilities=AdapterCapabilities(prediction_probability=True, **{category: True}),
                             evidence={category: value})
    req = LiveRequest(definition.model_id, "v1", "label-a", evidence_interpretation={category: interpretation})
    record = collect_live(registry, CollectionAssociation("p", "a", "o"), [req],
                          {"synthetic-feature": [0.3]}).records[0]
    item = next(item for item in record.evidence if item.category == category)
    assert record.primary.value == 0.2
    assert item.state == "invalid"
    assert item.value is None


def test_precomputed_evidence_normalization_retains_five_states_and_cohort_scope():
    association = CollectionAssociation("p", "a", "o")
    key = ("m", "v1", "label-a")
    candidate = OutputCandidate("out", 0.5, "probability", "probability", "increasing", evidence={
        "domain_metadata": {"value": {"cohort_in_training_scope": False},
                            "interpretation": {"meaning": "cohort scope"}},
        "input_metadata": None,
        "explanation": {"value": {"attributions": [0.2]}, "interpretation": {}},
    })
    items = {i.category: i for i in PrecomputedCollector._evidence_items(candidate, association, key)}
    assert items["domain_metadata"].state == "available"
    assert items["domain_metadata"].value["cohort_in_training_scope"] is False
    assert items["input_metadata"].state == "missing"
    assert items["explanation"].state == "invalid"
    assert items["repeated_outputs"].state == "missing"


def test_precomputed_calibration_and_explanation_output_spaces_remain_distinct(registered_collection):
    from collection_fixtures import SyntheticTrustedVerifier
    from safira.collection import ComponentContribution, PrecomputedCollector

    registry, register = registered_collection
    register(model_id="calibrated-source")
    association = CollectionAssociation("p", "a", "o")
    contribution = ComponentContribution("calibrated-contract", "v1", "out", "calibrated-source",
                                         "v1", "label-a", 0)
    raw = '{"synthetic":"calibrated output"}'
    evidence = {"explanation": {"value": {"attributions": [0.1]}, "interpretation": {
        "meaning": "attribution", "target_label": "label-a", "target_output": "raw-score",
        "method": "synthetic", "output_space": "uncalibrated_score", "calibrated": False,
    }}}

    class Contract:
        contract_id = "calibrated-contract"
        version = "v1"

        def parse(self, raw_json):
            return NormalizedEnvelope((OutputCandidate(
                "out", 0.8, "probability", "synthetic probability", "increasing",
                calibration={"method": "synthetic-held-out"}, evidence=evidence, event_id="cal-event",
            ),))

        def validate_declarations(self, envelope, declarations):
            return envelope

    contract = Contract()
    verifier = SyntheticTrustedVerifier()
    candidate = contract.parse(raw).outputs[0]
    verifier.add("cal-event", raw, candidate, contribution, association)
    record = PrecomputedCollector(registry, [TrustedSourceIntegration(contract, verifier)]).ingest(
        association, (contract.contract_id, contract.version), raw,
        SourceDeclarations((contribution,)),
    ).records[0]
    explanation = next(item for item in record.evidence if item.category == "explanation")
    assert record.primary.calibration["method"] == "synthetic-held-out"
    assert explanation.state == "available"
    assert explanation.interpretation["calibrated"] is False
    assert explanation.interpretation["output_space"] == "uncalibrated_score"

