"""Immutable, declarative metadata for supervised multi-label registrations.

Only structural input declarations and primary output semantics belong here.
Class boundaries are supplied by the classifier owner; they are not Safira
reliability thresholds or evidence of clinical safety.
"""

from collections.abc import Mapping
from dataclasses import MISSING, dataclass, fields
import math
import re
from types import MappingProxyType
import unicodedata

from safira.adapters import AdapterCapabilities
from safira.registry.exceptions import InvalidRegistrationError, UnsupportedTaskError
from safira.registry.storage import SCHEMA_VERSION


TASK_TYPE = "supervised_multi_label_classification"


def _invalid(field: str) -> None:
    # Field names at call sites are fixed schema paths, never submitted values.
    raise InvalidRegistrationError(f"{field}: invalid or incomplete declaration.")


def _text(value: object, field: str, *, exact: bool = False) -> None:
    if (
        type(value) is not str
        or not value.strip()
        or (exact and value != value.strip())
        or any(unicodedata.category(char) == "Cc" for char in value)
    ):
        _invalid(field)


def _keys(value: object, required: set[str], field: str, optional=()) -> None:
    if not isinstance(value, Mapping):
        _invalid(field)
    if not required <= value.keys() or not value.keys() <= required | set(optional):
        _invalid(field)


def _sha256(value: object, field: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _invalid(field)


def _number(value: object, field: str) -> None:
    if type(value) not in (int, float) or not math.isfinite(value):
        _invalid(field)


def _freeze(value):
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            _invalid("metadata")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    _invalid("metadata")


def _plain(value):
    if isinstance(value, (_Definition, AdapterCapabilities)):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


class _Definition:
    def to_dict(self) -> dict[str, object]:
        """Return a detached JSON-compatible representation."""
        return {field.name: _plain(getattr(self, field.name)) for field in fields(self)}

    @classmethod
    def from_dict(cls, data):
        """Reject unknown fields rather than retaining arbitrary payloads."""
        declared = fields(cls)
        required = {
            field.name for field in declared
            if field.default is MISSING and field.default_factory is MISSING
        }
        optional = {field.name for field in declared} - required
        try:
            _keys(data, required, cls.__name__, optional)
            return cls(**data)
        except InvalidRegistrationError:
            raise
        except (TypeError, ValueError, OverflowError, RecursionError):
            _invalid(cls.__name__)


def _definition(cls, value):
    if isinstance(value, cls):
        value = value.to_dict()
    return cls.from_dict(value)


@dataclass(frozen=True)
class LabelDefinition(_Definition):
    label_id: str
    negative_outcome: str
    positive_outcome: str
    output_selector: int | str
    value_kind: str
    value_source: str
    value_scale: Mapping[str, object]
    class_mapping: Mapping[str, object]

    def __post_init__(self) -> None:
        _text(self.label_id, "labels.label_id", exact=True)
        _text(self.negative_outcome, "labels.negative_outcome")
        _text(self.positive_outcome, "labels.positive_outcome")
        if self.negative_outcome == self.positive_outcome:
            _invalid("labels.outcomes")
        if type(self.output_selector) is int:
            if self.output_selector < 0:
                _invalid("labels.output_selector")
        else:
            _text(self.output_selector, "labels.output_selector", exact=True)
        sources = {"probability": "predict_probability", "continuous_score": "predict"}
        if type(self.value_kind) is not str or self.value_kind not in sources:
            _invalid("labels.value_kind")
        if self.value_source != sources[self.value_kind]:
            _invalid("labels.value_source")
        _keys(
            self.value_scale, {"minimum", "maximum", "meaning", "positive_direction"},
            "labels.value_scale",
        )
        minimum, maximum = self.value_scale["minimum"], self.value_scale["maximum"]
        for bound in (minimum, maximum):
            if bound is not None:
                _number(bound, "labels.value_scale")
        if minimum is not None and maximum is not None and minimum >= maximum:
            _invalid("labels.value_scale")
        if self.value_kind == "probability" and (minimum != 0 or maximum != 1):
            _invalid("labels.value_scale")
        _text(self.value_scale["meaning"], "labels.value_scale.meaning")
        direction = self.value_scale["positive_direction"]
        if direction not in ("increasing", "decreasing"):
            _invalid("labels.value_scale.positive_direction")
        _keys(self.class_mapping, {"positive_when", "boundary"}, "labels.class_mapping")
        comparisons = (">", ">=") if direction == "increasing" else ("<", "<=")
        if self.class_mapping["positive_when"] not in comparisons:
            _invalid("labels.class_mapping.positive_when")
        _number(self.class_mapping["boundary"], "labels.class_mapping.boundary")
        object.__setattr__(self, "value_scale", _freeze(self.value_scale))
        object.__setattr__(self, "class_mapping", _freeze(self.class_mapping))


@dataclass(frozen=True)
class AdapterDeclaration(_Definition):
    adapter_id: str
    adapter_version: str
    implementation_fingerprint: str
    associated_model_id: str
    associated_model_version: str
    capabilities: AdapterCapabilities

    def __post_init__(self) -> None:
        for name in ("adapter_id", "adapter_version", "associated_model_id", "associated_model_version"):
            _text(getattr(self, name), f"adapter.{name}", exact=True)
        _sha256(self.implementation_fingerprint, "adapter.implementation_fingerprint")
        capabilities = self.capabilities
        if isinstance(capabilities, AdapterCapabilities):
            capabilities = capabilities.to_dict()
        expected = {field.name for field in fields(AdapterCapabilities)}
        _keys(capabilities, expected, "adapter.capabilities")
        if any(type(flag) is not bool for flag in capabilities.values()):
            _invalid("adapter.capabilities")
        object.__setattr__(self, "capabilities", AdapterCapabilities(**capabilities))


@dataclass(frozen=True)
class InputDefinition(_Definition):
    schema: Mapping[str, object]
    modalities: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.schema, Mapping) or not self.schema:
            _invalid("input.schema")
        for name, declaration in self.schema.items():
            _text(name, "input.schema.field", exact=True)
            _keys(declaration, {"type"}, "input.schema.declaration", {"shape"})
            _text(declaration["type"], "input.schema.type", exact=True)
            if "shape" in declaration:
                shape = declaration["shape"]
                if not isinstance(shape, (tuple, list)) or any(
                    dimension is not None and (type(dimension) is not int or dimension < 0)
                    for dimension in shape
                ):
                    _invalid("input.schema.shape")
        if not isinstance(self.modalities, (tuple, list)):
            _invalid("input.modalities")
        for modality in self.modalities:
            _text(modality, "input.modalities", exact=True)
        if len(set(self.modalities)) != len(self.modalities):
            _invalid("input.modalities")
        object.__setattr__(self, "schema", _freeze(self.schema))
        object.__setattr__(self, "modalities", tuple(self.modalities))


@dataclass(frozen=True)
class RegisteredModelVersion(_Definition):
    model_id: str
    model_version: str
    task_type: str
    classifier_artifact: Mapping[str, str]
    labels: tuple[LabelDefinition, ...]
    adapter: AdapterDeclaration
    input: InputDefinition
    preprocessing_identity: str | Mapping[str, str]
    metadata_schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text(self.model_id, "model_id", exact=True)
        _text(self.model_version, "model_version", exact=True)
        if self.task_type != TASK_TYPE:
            raise UnsupportedTaskError("Only supervised multi-label classification is supported.")
        if not isinstance(self.labels, (tuple, list)) or len(self.labels) < 2:
            raise UnsupportedTaskError("Supervised multi-label registration requires at least two labels.")
        labels = tuple(_definition(LabelDefinition, label) for label in self.labels)
        if len({label.label_id for label in labels}) != len(labels):
            _invalid("labels.label_id")
        if len({label.output_selector for label in labels}) != len(labels):
            _invalid("labels.output_selector")
        _keys(self.classifier_artifact, {"sha256"}, "classifier_artifact")
        _sha256(self.classifier_artifact["sha256"], "classifier_artifact.sha256")
        adapter = _definition(AdapterDeclaration, self.adapter)
        if (adapter.associated_model_id, adapter.associated_model_version) != (
            self.model_id, self.model_version
        ):
            _invalid("adapter.associated_model_identity")
        inputs = _definition(InputDefinition, self.input)
        preprocessing = self.preprocessing_identity
        if isinstance(preprocessing, Mapping):
            _keys(preprocessing, set(), "preprocessing_identity", {"version", "sha256"})
            if not preprocessing:
                _invalid("preprocessing_identity")
            if "version" in preprocessing:
                _text(preprocessing["version"], "preprocessing_identity.version", exact=True)
            if "sha256" in preprocessing:
                _sha256(preprocessing["sha256"], "preprocessing_identity.sha256")
        else:
            _text(preprocessing, "preprocessing_identity", exact=True)
        if type(self.metadata_schema_version) is not int or self.metadata_schema_version != SCHEMA_VERSION:
            _invalid("metadata_schema_version")
        object.__setattr__(self, "labels", labels)
        object.__setattr__(self, "adapter", adapter)
        object.__setattr__(self, "input", inputs)
        object.__setattr__(self, "classifier_artifact", _freeze(self.classifier_artifact))
        object.__setattr__(self, "preprocessing_identity", _freeze(preprocessing))
