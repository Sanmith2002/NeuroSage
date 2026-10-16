"""T016/T018/T019: invalid declaration and adapter acceptance categories."""

from copy import deepcopy
from dataclasses import fields
import traceback

import pytest

from safira import AdapterCapabilities, ModelAdapter
from safira.registry import (
    IncompatibleAdapterError,
    InvalidRegistrationError,
    ModelRegistry,
    RegisteredModelVersion,
    UnknownModelError,
    UnsupportedTaskError,
)


def _set(record, path, value):
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


@pytest.mark.parametrize("path,value", [
    (("model_id",), None),
    (("model_id",), "\t"),
    (("model_version",), " v1"),
    (("model_version",), "v1\x00"),
    (("labels",), []),
    (("labels", 0, "label_id"), " "),
    (("labels", 1, "label_id"), "label-a"),
    (("labels", 1, "output_selector"), 0),
    (("labels", 0, "output_selector"), True),
    (("labels", 0, "positive_outcome"), ["positive", "severe"]),
    (("labels", 0, "positive_outcome"), "negative"),
    (("labels", 0, "value_kind"), "hard_prediction"),
    (("labels", 0, "value_source"), "predict"),
    (("labels", 0, "value_scale", "meaning"), ""),
    (("labels", 0, "value_scale", "minimum"), True),
    (("labels", 0, "value_scale", "maximum"), 2.0),
    (("labels", 0, "value_scale", "positive_direction"), "ambiguous"),
    (("labels", 0, "class_mapping", "positive_when"), "<"),
    (("labels", 0, "class_mapping", "boundary"), float("nan")),
    (("labels", 0, "class_mapping", "boundary"), float("inf")),
    (("labels", 0, "class_mapping", "boundary"), True),
    (("labels", 0, "third_outcome"), "severe"),
    (("input", "schema", "synthetic-feature", "shape"), [-1]),
    (("input", "modalities"), ["synthetic", "synthetic"]),
    (("adapter", "associated_model_version"), "different"),
])
def test_invalid_declarations_never_create_a_registration(
    catalog_path, synthetic_metadata, loaded_pair, path, value
):
    classifier, adapter, provider = loaded_pair
    invalid = deepcopy(synthetic_metadata)
    _set(invalid, path, value)
    with ModelRegistry(catalog_path) as registry:
        with pytest.raises(InvalidRegistrationError):
            registry.register(
                RegisteredModelVersion.from_dict(invalid), classifier, adapter, provider
            )
        with pytest.raises(UnknownModelError):
            registry.get_metadata("synthetic-model", "v1")


@pytest.mark.parametrize("path", [
    ("model_id",), ("model_version",), ("labels", 0, "positive_outcome"),
    ("labels", 0, "class_mapping"), ("labels", 0, "value_scale", "meaning"),
])
def test_missing_field_error_identifies_the_safe_schema_field(synthetic_metadata, path):
    target = synthetic_metadata
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    with pytest.raises(InvalidRegistrationError, match=path[-1]):
        RegisteredModelVersion.from_dict(synthetic_metadata)


@pytest.mark.parametrize("task", [
    "standalone_binary_classification", "regression", "unsupervised", "reinforcement_learning",
])
def test_unsupported_tasks_have_a_specific_scope_error(synthetic_metadata, task):
    synthetic_metadata["task_type"] = task
    with pytest.raises(UnsupportedTaskError, match="supervised multi-label"):
        RegisteredModelVersion.from_dict(synthetic_metadata)


def test_one_label_binary_classifier_is_explicitly_unsupported(synthetic_metadata):
    synthetic_metadata["labels"] = synthetic_metadata["labels"][:1]
    with pytest.raises(UnsupportedTaskError, match="at least two labels"):
        RegisteredModelVersion.from_dict(synthetic_metadata)


@pytest.mark.parametrize("capability", [field.name for field in fields(AdapterCapabilities)])
@pytest.mark.parametrize("value", [0, 1, "false", None])
def test_each_capability_requires_an_actual_boolean(synthetic_metadata, capability, value):
    synthetic_metadata["adapter"]["capabilities"][capability] = value
    with pytest.raises(InvalidRegistrationError, match="capabilities"):
        RegisteredModelVersion.from_dict(synthetic_metadata)


class _PredictOnlyAdapter(ModelAdapter):
    def predict(self, patient_data, label):
        raise AssertionError("Registration must not predict.")


class _ProbabilityAdapter(_PredictOnlyAdapter):
    def predict_probability(self, patient_data, label):
        raise AssertionError("Registration must not predict probabilities.")


@pytest.mark.parametrize("capability,method", [
    ("prediction_probability", "predict_probability"),
    ("feature_representation", "extract_features"),
    ("repeated_outputs", "get_repeated_outputs"),
    ("modality_outputs", "get_modality_outputs"),
    ("domain_metadata", "get_domain_metadata"),
    ("explanation", "explain"),
    ("input_metadata", "get_input_metadata"),
    ("available_modalities", "get_available_modalities"),
])
def test_claimed_capabilities_require_concrete_methods(
    catalog_path, synthetic_metadata, loaded_pair, capability, method
):
    classifier, _, provider = loaded_pair
    capabilities = AdapterCapabilities(**{"prediction_probability": True, capability: True})
    adapter_type = _PredictOnlyAdapter if capability == "prediction_probability" else _ProbabilityAdapter
    adapter = adapter_type(capabilities)
    synthetic_metadata["adapter"]["capabilities"] = capabilities.to_dict()
    declared = RegisteredModelVersion.from_dict(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        with pytest.raises(IncompatibleAdapterError, match=method):
            registry.register(declared, classifier, adapter, provider)
        with pytest.raises(UnknownModelError):
            registry.get_metadata(declared.model_id, declared.model_version)


@pytest.mark.parametrize("failure", ["not_adapter", "invalid_flag", "shadowed_method"])
def test_incompatible_live_adapter_is_rejected_before_storage(
    catalog_path, synthetic_metadata, loaded_pair, failure
):
    classifier, adapter, provider = loaded_pair
    declared = RegisteredModelVersion.from_dict(synthetic_metadata)
    if failure == "not_adapter":
        adapter = object()
    elif failure == "invalid_flag":
        adapter._capabilities = AdapterCapabilities(prediction_probability=1)
    else:
        adapter.predict_probability = None
    with ModelRegistry(catalog_path) as registry:
        with pytest.raises(IncompatibleAdapterError):
            registry.register(declared, classifier, adapter, provider)
        with pytest.raises(UnknownModelError):
            registry.get_metadata(declared.model_id, declared.model_version)


@pytest.mark.parametrize("attribute", ["capabilities", "predict_probability"])
def test_adapter_inspection_failures_are_typed_and_do_not_echo_payloads(
    catalog_path, synthetic_metadata, loaded_pair, attribute
):
    marker = "synthetic-private-inspection-marker"

    class FailingInspectionAdapter(_ProbabilityAdapter):
        def __getattribute__(self, name):
            if name == attribute:
                raise ValueError(marker)
            return super().__getattribute__(name)

    classifier, _, provider = loaded_pair
    adapter = FailingInspectionAdapter(AdapterCapabilities(prediction_probability=True))
    declared = RegisteredModelVersion.from_dict(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        with pytest.raises(IncompatibleAdapterError) as error:
            registry.register(declared, classifier, adapter, provider)
        assert marker not in "".join(traceback.format_exception(error.value))
        with pytest.raises(UnknownModelError):
            registry.get_metadata(declared.model_id, declared.model_version)
