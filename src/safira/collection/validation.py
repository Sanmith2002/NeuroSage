"""Shared structural and primary-output checks against Feature 001 metadata."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite
from typing import Any

from safira.collection.exceptions import ContributorMismatch, InvalidCollectionRequest, InvalidPrimaryOutput
from safira.collection.records import CollectionAssociation, ComponentContribution, PrimaryOutput
from safira.registry.definitions import InputDefinition, LabelDefinition, RegisteredModelVersion


def validate_source_key(
    association: CollectionAssociation,
    model_id: str,
    model_version: str,
    label_id: str,
) -> tuple[str, str, str, str, str, str]:
    """Retain all three opaque associations and exact contributor identity."""

    if not isinstance(association, CollectionAssociation):
        raise InvalidCollectionRequest("record.association")
    for value, field in (
        (model_id, "model_id"),
        (model_version, "model_version"),
        (label_id, "label_id"),
    ):
        if type(value) is not str or not value or value != value.strip():
            raise InvalidCollectionRequest(field)
    return (
        association.patient_ref,
        association.assessment_ref,
        association.occurrence_ref,
        model_id,
        model_version,
        label_id,
    )


def validate_expected_contributors(
    actual: Iterable[tuple[str, str, str]],
    expected: Iterable[tuple[str, str, str]],
    *,
    required: bool = False,
) -> tuple[tuple[str, str, str], ...]:
    """Require a component's explicit expected source-key set to match exactly."""

    try:
        raw_actual = tuple(actual)
        raw_expected = tuple(expected)
        if any(not isinstance(key, (tuple, list)) for key in (*raw_actual, *raw_expected)):
            raise ValueError
        actual_keys = tuple(tuple(key) for key in raw_actual)
        expected_keys = tuple(tuple(key) for key in raw_expected)
        for key in (*actual_keys, *expected_keys):
            if len(key) != 3 or any(type(part) is not str or not part.strip() for part in key):
                raise ValueError
        if len(set(actual_keys)) != len(actual_keys) or len(set(expected_keys)) != len(expected_keys):
            raise ValueError
    except Exception:
        raise ContributorMismatch("component.contribution") from None
    if required and not expected_keys:
        raise ContributorMismatch("component.contribution")
    if expected_keys and set(actual_keys) != set(expected_keys):
        raise ContributorMismatch("component.contribution")
    return expected_keys


def validate_component_contributor_mapping(
    registry: object,
    contributions: Iterable[ComponentContribution],
    candidate_selectors: Iterable[str],
    *,
    contract_key: tuple[str, str],
    expected_contributors: Iterable[tuple[str, str, str]] = (),
) -> dict[str, tuple[ComponentContribution, RegisteredModelVersion, LabelDefinition]]:
    """Resolve each external selector through its exact immutable registration.

    The owner-supplied selector translation is never used to infer model identity.
    Registration metadata remains authoritative for label semantics, preprocessing,
    input schema and adapter declaration; the source candidate's declared primary
    meaning is compared with that label by the ingestion path.
    """

    try:
        selectors = tuple(candidate_selectors)
        entries = tuple(contributions)
        if any(type(selector) is not str or not selector.strip() for selector in selectors):
            raise ValueError
        if len(set(selectors)) != len(selectors):
            raise ValueError
    except Exception:
        raise ContributorMismatch("component.contribution") from None
    by_selector: dict[str, ComponentContribution] = {}
    actual_keys: list[tuple[str, str, str]] = []
    for item in entries:
        if not isinstance(item, ComponentContribution):
            raise ContributorMismatch("component.contribution")
        if (item.source_contract_id, item.source_contract_version) != contract_key:
            raise ContributorMismatch("component.contribution")
        if item.external_selector in by_selector:
            raise ContributorMismatch("component.contribution")
        by_selector[item.external_selector] = item
        actual_keys.append(item.source_key)
    if set(selectors) != set(by_selector):
        raise ContributorMismatch("component.contribution")
    validate_expected_contributors(actual_keys, expected_contributors)

    result: dict[str, tuple[ComponentContribution, RegisteredModelVersion, LabelDefinition]] = {}
    for selector, contribution in by_selector.items():
        try:
            definition = registry.get_metadata(contribution.model_id, contribution.model_version)
        except Exception:
            raise ContributorMismatch("model_version") from None
        if not isinstance(definition, RegisteredModelVersion):
            raise ContributorMismatch("model_version")
        label = next((item for item in definition.labels if item.label_id == contribution.label_id), None)
        if label is None or label.output_selector != contribution.registered_output_selector:
            raise ContributorMismatch("component.contribution")
        expected_source = "predict_probability" if label.value_kind == "probability" else "predict"
        adapter = definition.adapter
        if (label.value_source != expected_source
                or adapter.associated_model_id != definition.model_id
                or adapter.associated_model_version != definition.model_version
                or not definition.classifier_artifact.get("sha256")
                or not definition.preprocessing_identity):
            raise ContributorMismatch("component.contribution")
        # Definitions validate the declared input schema and adapter capabilities
        # on registry load. Touch those exact fields here so the mapping is checked
        # against the full registration rather than a name-only model lookup.
        if not isinstance(definition.input, InputDefinition) or not adapter.capabilities:
            raise ContributorMismatch("component.contribution")
        result[selector] = (contribution, definition, label)
    return result


def validate_primary_output(
    value: object,
    label: LabelDefinition,
    *,
    supplied_class: str | None = None,
    calibration: Mapping[str, object] | None = None,
) -> PrimaryOutput:
    """Apply one registered label's exact numeric domain and class mapping."""

    if not isinstance(label, LabelDefinition):
        raise InvalidPrimaryOutput("primary.value_kind")
    if type(value) not in (int, float):
        raise InvalidPrimaryOutput("primary.value")
    if type(value) is float and not isfinite(value):
        raise InvalidPrimaryOutput("primary.value")
    scale = label.value_scale
    minimum, maximum = scale["minimum"], scale["maximum"]
    if (minimum is not None and value < minimum) or (
        maximum is not None and value > maximum
    ):
        raise InvalidPrimaryOutput("primary.value")
    if label.value_kind == "probability" and not 0 <= value <= 1:
        raise InvalidPrimaryOutput("primary.value")
    mapping = label.class_mapping
    comparator = mapping["positive_when"]
    boundary = mapping["boundary"]
    positive = {
        ">": lambda: value > boundary,
        ">=": lambda: value >= boundary,
        "<": lambda: value < boundary,
        "<=": lambda: value <= boundary,
    }.get(comparator)
    if positive is None:
        raise InvalidPrimaryOutput("primary.class_mapping")
    predicted_class = label.positive_outcome if positive() else label.negative_outcome
    if supplied_class is not None:
        if type(supplied_class) is not str or supplied_class != predicted_class:
            raise InvalidPrimaryOutput("primary.predicted_class")
    try:
        return PrimaryOutput(
            value=value,
            value_kind=label.value_kind,
            scale=scale,
            meaning=scale["meaning"],
            positive_direction=scale["positive_direction"],
            class_mapping=mapping,
            predicted_class=predicted_class,
            calibration=calibration,
        )
    except InvalidCollectionRequest as error:
        raise InvalidPrimaryOutput(error.field) from None


def _matches_type(value: object, declared: str) -> bool:
    if declared in ("float", "number"):
        return type(value) in (int, float) and (
            type(value) is not float or isfinite(value)
        )
    if declared in ("int", "integer"):
        return type(value) is int
    if declared in ("str", "string"):
        return type(value) is str
    if declared in ("bool", "boolean"):
        return type(value) is bool
    if declared in ("mapping", "object"):
        return isinstance(value, Mapping)
    raise InvalidCollectionRequest("input.type")


def _matches_shape_and_type(value: object, shape: tuple[object, ...], declared: str) -> bool:
    if not shape:
        return _matches_type(value, declared)
    if not isinstance(value, (list, tuple)):
        return False
    dimension = shape[0]
    if dimension is not None and len(value) != dimension:
        return False
    return all(_matches_shape_and_type(item, shape[1:], declared) for item in value)


def validate_input_structure(
    patient_data: object,
    definition: InputDefinition,
    *,
    available_modalities: Iterable[str] | None = None,
) -> None:
    """Check declared fields, types, shapes and modality names before inference.

    This checks structure only. It never infers clinical plausibility or eligibility.
    """

    if not isinstance(definition, InputDefinition) or not isinstance(patient_data, Mapping):
        raise InvalidCollectionRequest("input.schema")
    try:
        if set(patient_data) != set(definition.schema):
            raise InvalidCollectionRequest("input.schema")
        for field_name, declaration in definition.schema.items():
            declared_type = declaration["type"]
            shape = tuple(declaration.get("shape", ()))
            if not _matches_shape_and_type(patient_data[field_name], shape, declared_type):
                raise InvalidCollectionRequest("input.shape" if shape else "input.type")
        if available_modalities is None:
            if definition.modalities:
                raise InvalidCollectionRequest("input.modality")
            return
        modalities = tuple(available_modalities)
        if (
            any(type(modality) is not str for modality in modalities)
            or len(set(modalities)) != len(modalities)
            or set(modalities) != set(definition.modalities)
        ):
            raise InvalidCollectionRequest("input.modality")
    except InvalidCollectionRequest:
        raise
    except Exception:
        # Do not expose a source-specific container's exception text or patient values.
        raise InvalidCollectionRequest("input.schema") from None
