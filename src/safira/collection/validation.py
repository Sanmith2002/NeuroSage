"""Shared structural and primary-output checks against Feature 001 metadata."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import isfinite
from typing import Any

from safira.collection.exceptions import InvalidCollectionRequest, InvalidPrimaryOutput
from safira.collection.records import CollectionAssociation, PrimaryOutput
from safira.registry.definitions import InputDefinition, LabelDefinition


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
