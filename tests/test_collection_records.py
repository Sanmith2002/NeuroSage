"""Foundational collection records and validation with synthetic values only."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import pytest

from safira.collection import (
    CollectionAssociation,
    CollectionResult,
    ComponentContribution,
    ComponentIdentity,
    EvidenceItem,
    PredictionRecord,
    PrimaryOutput,
    SourceProvenance,
)
from safira.collection.exceptions import InvalidCollectionRequest, InvalidPrimaryOutput
from safira.collection.validation import (
    validate_input_structure,
    validate_primary_output,
    validate_source_key,
)
from safira.registry.definitions import InputDefinition, LabelDefinition
from collection_fixtures import source_payload_a, source_payload_b


def test_synthetic_fixtures_cover_classifier_forms_and_independent_source_shapes(
    collection_single_pair, collection_multi_pair, collection_manifest
):
    assert len(collection_single_pair[0].scores) == 1
    assert len(collection_multi_pair[0].scores) == 2
    flat = json.loads(source_payload_a("output-a", 0.3))
    nested = json.loads(source_payload_b("output-a", 0.3))
    assert flat["score"] == nested["entries"][0]["result"]["value"]
    assert set(flat) != set(nested)
    key = ("synthetic-a", "v1", "label-a")
    association = ("opaque-patient", "assessment-1", "occurrence-1")
    collection_manifest.add("event-1", b"content-a", key, association)
    assert collection_manifest.matches("event-1", b"content-a", key, association)
    assert not collection_manifest.matches("event-1", b"changed", key, association)
    assert not collection_manifest.matches("event-1", b"content-a", key, ("other", *association[1:]))


def _record(
    *,
    association: CollectionAssociation | None = None,
    model_id: str = "synthetic-a",
    model_version: str = "v1",
    label_id: str = "label-a",
    details: dict | None = None,
    evidence: tuple[EvidenceItem, ...] = (),
) -> PredictionRecord:
    association = association or CollectionAssociation("opaque-patient", "assessment-1", "occurrence-1")
    key = (model_id, model_version, label_id)
    return PredictionRecord(
        association=association,
        model_id=model_id,
        model_version=model_version,
        label_id=label_id,
        primary=PrimaryOutput(
            value=0.7,
            value_kind="probability",
            scale={"minimum": 0.0, "maximum": 1.0, "nested": ["unit"]},
            meaning="synthetic positive-class probability",
            positive_direction="increasing",
            class_mapping={"positive_when": ">=", "boundary": 0.5},
            predicted_class="positive",
        ),
        provenance=SourceProvenance(
            mode="live",
            association=association,
            source_key=key,
            assurance="verified_live_binding",
            details=details or {"checks": {"names": ["pair"]}},
        ),
        evidence=evidence,
        input_verification="validated",
    )


def test_source_qualified_records_are_unique_within_an_occurrence():
    first = _record()
    second = _record(model_id="synthetic-b")
    third = _record(model_version="v2")
    accepted = CollectionResult(first.association, (first, second, third))
    assert len(accepted.records) == 3
    assert [record.source_key for record in accepted.records] == [
        ("synthetic-a", "v1", "label-a"),
        ("synthetic-b", "v1", "label-a"),
        ("synthetic-a", "v2", "label-a"),
    ]
    with pytest.raises(InvalidCollectionRequest):
        CollectionResult(first.association, (first, first))
    with pytest.raises(InvalidCollectionRequest):
        CollectionResult(
            first.association,
            (first, _record(association=CollectionAssociation("other", "assessment-1", "occurrence-1"))),
        )


@pytest.mark.parametrize("state", ["available", "unsupported", "missing", "unavailable", "invalid"])
def test_evidence_distinguishes_all_five_states_without_fabricated_value(state):
    association = CollectionAssociation("opaque-patient", "assessment-1", "occurrence-1")
    item = EvidenceItem(
        association=association,
        source_key=("synthetic-a", "v1", "label-a"),
        category="feature_representation",
        state=state,
        value=[0.0] if state == "available" else None,
        reason_code=None if state == "available" else state,
        interpretation={"shape": [1]} if state == "available" else {},
    )
    assert item.state == state
    if state == "available":
        assert item.value == (0.0,)
    else:
        assert item.value is None
    if state != "available":
        assert item.reason_code == state


def test_unsupported_evidence_with_supplied_value_is_invalid():
    association = CollectionAssociation("opaque-patient", "assessment-1", "occurrence-1")
    item = EvidenceItem(
        association=association,
        source_key=("synthetic-a", "v1", "label-a"),
        category="explanation",
        state="unsupported",
        value={"unexpected": [1.0]},
    )
    assert item.state == "invalid"
    assert item.value is None
    assert item.reason_code == "invalid"


def test_original_and_returned_nested_values_cannot_change_accepted_record():
    details = {"checks": {"names": ["pair"]}}
    interpretation = {"units": ["synthetic-unit"]}
    supplied_value = {"vector": [0.0, 0.3]}
    association = CollectionAssociation("opaque-patient", "assessment-1", "occurrence-1")
    item = EvidenceItem(
        association=association,
        source_key=("synthetic-a", "v1", "label-a"),
        category="feature_representation",
        state="available",
        value=supplied_value,
        interpretation=interpretation,
    )
    record = _record(details=details, evidence=(item,))
    result = CollectionResult(association, [record])
    before = result.to_dict()
    details["checks"]["names"].append("tampered")
    interpretation["units"].append("tampered")
    supplied_value["vector"].append(999.0)
    returned = result.to_dict()
    returned["records"][0]["provenance"]["details"]["checks"]["names"].append("tampered")
    returned["records"][0]["evidence"][0]["value"]["vector"].append(999.0)
    assert result.to_dict() == before
    with pytest.raises((TypeError, AttributeError, FrozenInstanceError)):
        record.provenance.details["checks"]["names"] += ("tampered",)
    with pytest.raises(FrozenInstanceError):
        record.model_id = "tampered"


def test_nondetachable_optional_evidence_is_invalid_but_required_metadata_fails():
    association = CollectionAssociation("opaque-patient", "assessment-1", "occurrence-1")
    item = EvidenceItem(
        association=association,
        source_key=("synthetic-a", "v1", "label-a"),
        category="explanation",
        state="available",
        value=object(),
    )
    assert item.state == "invalid"
    assert item.value is None
    assert item.reason_code == "non_detachable"
    with pytest.raises(InvalidCollectionRequest):
        _record(details={"unsafe": object()})


def test_nondetachable_interpretation_keeps_optional_failure_isolated():
    association = CollectionAssociation("opaque-patient", "assessment-1", "occurrence-1")
    item = EvidenceItem(
        association=association,
        source_key=("synthetic-a", "v1", "label-a"),
        category="feature_representation",
        state="missing",
        interpretation={"unsafe": object()},
    )
    assert item.state == "invalid"
    assert item.value is None
    assert item.reason_code == "non_detachable"
    assert CollectionResult(association, (_record(evidence=(item,)),)).records[0].primary.value == 0.7


def test_component_values_and_external_inputs_are_detached():
    expected = ["synthetic-a", "synthetic-b"]
    component = ComponentIdentity("synthetic-component", "v3", {"expected": expected})
    contribution = ComponentContribution(
        source_contract_id="synthetic-source",
        source_contract_version="v1",
        external_selector="outputs.a",
        model_id="synthetic-a",
        model_version="v1",
        label_id="label-a",
        registered_output_selector=0,
    )
    expected.append("tampered")
    assert component.to_dict()["metadata"]["expected"] == ["synthetic-a", "synthetic-b"]
    assert contribution.source_key == ("synthetic-a", "v1", "label-a")


def test_foundational_exports_include_values_and_errors_without_future_operations():
    import safira.collection as collection

    for name in (
        "CollectionAssociation", "CollectionResult", "ComponentContribution",
        "ComponentIdentity", "EvidenceItem", "PredictionRecord", "PrimaryOutput",
        "SourceProvenance", "CollectionError", "InvalidCollectionRequest",
    ):
        assert hasattr(collection, name)
    for name in ("PrecomputedCollector", "TrustedSourceIntegration", "precomputed_adapter"):
        assert hasattr(collection, name)


def test_registered_mapping_preserves_probability_and_score_semantics(synthetic_metadata):
    probability = LabelDefinition(**deepcopy(synthetic_metadata["labels"][0]))
    normalized = validate_primary_output(0.8, probability, supplied_class="positive")
    assert normalized.value_kind == "probability"
    assert normalized.predicted_class == "positive"
    with pytest.raises(InvalidPrimaryOutput):
        validate_primary_output(0.8, probability, supplied_class="negative")

    score_definition = deepcopy(synthetic_metadata["labels"][0])
    score_definition["value_kind"] = "continuous_score"
    score_definition["value_source"] = "predict"
    score_definition["value_scale"] = {
        "minimum": -2.0,
        "maximum": 2.0,
        "meaning": "synthetic margin",
        "positive_direction": "increasing",
    }
    score_definition["class_mapping"] = {"positive_when": ">", "boundary": 0.0}
    score = validate_primary_output(-0.2, LabelDefinition(**score_definition))
    assert score.value_kind == "continuous_score"
    assert score.predicted_class == "negative"
    assert score.value == -0.2


def test_unbounded_score_accepts_finite_integer_without_float_conversion(synthetic_metadata):
    score_definition = deepcopy(synthetic_metadata["labels"][0])
    score_definition["value_kind"] = "continuous_score"
    score_definition["value_source"] = "predict"
    score_definition["value_scale"] = {
        "minimum": None,
        "maximum": None,
        "meaning": "synthetic unbounded score",
        "positive_direction": "increasing",
    }
    score_definition["class_mapping"] = {"positive_when": ">", "boundary": 0.0}
    normalized = validate_primary_output(10**1000, LabelDefinition(**score_definition))
    assert normalized.value == 10**1000


def test_registered_outcome_and_meaning_text_are_preserved_exactly(synthetic_metadata):
    definition = deepcopy(synthetic_metadata["labels"][0])
    definition["positive_outcome"] = " positive "
    definition["value_scale"]["meaning"] = " synthetic probability "
    normalized = validate_primary_output(0.8, LabelDefinition(**definition))
    assert normalized.predicted_class == " positive "
    assert normalized.meaning == " synthetic probability "


@pytest.mark.parametrize("bad", [True, "0.7", float("nan"), float("inf"), -0.1, 1.1])
def test_primary_validation_rejects_coercion_nonfinite_and_out_of_range(synthetic_metadata, bad):
    label = LabelDefinition(**deepcopy(synthetic_metadata["labels"][0]))
    with pytest.raises(InvalidPrimaryOutput):
        validate_primary_output(bad, label)


def test_exact_source_key_and_structural_input_validation(synthetic_metadata):
    association = CollectionAssociation("opaque-patient", "assessment-1", "occurrence-1")
    assert validate_source_key(association, "synthetic-a", "v1", "label-a") == (
        "opaque-patient", "assessment-1", "occurrence-1", "synthetic-a", "v1", "label-a"
    )
    with pytest.raises(InvalidCollectionRequest):
        validate_source_key(association, "", "v1", "label-a")
    definition = InputDefinition(**deepcopy(synthetic_metadata["input"]))
    validate_input_structure(
        {"synthetic-feature": [0.4]}, definition, available_modalities=("synthetic",)
    )
    for patient_data, modalities in (
        ({"synthetic-feature": ["wrong"]}, ("synthetic",)),
        ({"synthetic-feature": [0.4, 0.5]}, ("synthetic",)),
        ({"synthetic-feature": [0.4]}, ("other",)),
        ({"synthetic-feature": [0.4]}, None),
    ):
        with pytest.raises(InvalidCollectionRequest):
            validate_input_structure(patient_data, definition, available_modalities=modalities)


def test_input_without_declared_modalities_needs_no_modality_assertion():
    definition = InputDefinition(schema={"synthetic-feature": {"type": "float"}}, modalities=())
    validate_input_structure(
        {"synthetic-feature": 0.4}, definition, available_modalities=None
    )
