"""T007/T008: synthetic acceptance coverage for User Story 1 only."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from safira import AdapterCapabilities, ModelAdapter
from safira.registry import (
    AdapterDeclaration,
    InputDefinition,
    LabelDefinition,
    ModelRegistry,
    RegisteredModelVersion,
    UsableRegistration,
)
from safira.registry.exceptions import (
    BindingMismatchError,
    DuplicateRegistrationError,
    IncompatibleAdapterError,
    InvalidRegistrationError,
    UnattachedModelError,
    UnknownModelError,
    UnsupportedTaskError,
)


def definition(metadata):
    return RegisteredModelVersion.from_dict(metadata)


def test_definitions_preserve_all_declared_semantics(synthetic_metadata):
    record = definition(synthetic_metadata)
    assert isinstance(record.adapter, AdapterDeclaration)
    assert isinstance(record.adapter.capabilities, AdapterCapabilities)
    assert isinstance(record.input, InputDefinition)
    assert all(isinstance(label, LabelDefinition) for label in record.labels)
    assert record.to_dict() == synthetic_metadata
    assert record.labels[0].positive_outcome == "positive"
    assert record.labels[0].negative_outcome == "negative"
    assert record.labels[0].value_source == "predict_probability"
    assert not hasattr(record, "reliability_score")
    assert not hasattr(record, "status")


def test_nested_definition_values_are_immutable(synthetic_metadata):
    record = definition(synthetic_metadata)
    with pytest.raises(FrozenInstanceError):
        record.model_version = "changed"
    with pytest.raises(FrozenInstanceError):
        record.labels[0].label_id = "changed"
    with pytest.raises(TypeError):
        record.labels[0].class_mapping["boundary"] = 0.8
    with pytest.raises(TypeError):
        record.labels[0].value_scale["maximum"] = 2.0
    with pytest.raises(TypeError):
        record.input.schema["synthetic-feature"]["shape"][0] = 99
    with pytest.raises(TypeError):
        record.classifier_artifact["sha256"] = "0" * 64
    with pytest.raises(FrozenInstanceError):
        record.adapter.capabilities.prediction_probability = False
    assert isinstance(record.labels, tuple)
    assert isinstance(record.input.modalities, tuple)


def test_original_inputs_and_exported_values_cannot_mutate_definitions(synthetic_metadata):
    synthetic_metadata["preprocessing_identity"] = {"version": "synthetic-transform-v1"}
    expected = deepcopy(synthetic_metadata)
    record = definition(synthetic_metadata)
    synthetic_metadata["labels"][0]["class_mapping"]["boundary"] = 0.9
    synthetic_metadata["input"]["schema"]["synthetic-feature"]["shape"].append(99)
    synthetic_metadata["adapter"]["capabilities"]["explanation"] = True
    synthetic_metadata["input"]["modalities"].append("other")
    synthetic_metadata["preprocessing_identity"]["version"] = "changed"
    exported = record.to_dict()
    exported["labels"].clear()
    exported["input"]["modalities"].clear()
    assert record.to_dict() == expected


@pytest.mark.parametrize("key", ["model_id", "model_version"])
@pytest.mark.parametrize("value", ["", " ", " padded", "padded ", "control\x00"])
def test_definition_requires_exact_nonblank_keys(synthetic_metadata, key, value):
    synthetic_metadata[key] = value
    with pytest.raises(InvalidRegistrationError):
        definition(synthetic_metadata)


@pytest.mark.parametrize("count", [0, 1])
def test_definition_requires_multiple_labels(synthetic_metadata, count):
    synthetic_metadata["labels"] = synthetic_metadata["labels"][:count]
    with pytest.raises(UnsupportedTaskError):
        definition(synthetic_metadata)


def test_definition_requires_unique_label_ids_and_outputs(synthetic_metadata):
    duplicate_id = deepcopy(synthetic_metadata)
    duplicate_id["labels"][1]["label_id"] = duplicate_id["labels"][0]["label_id"]
    duplicate_output = deepcopy(synthetic_metadata)
    duplicate_output["labels"][1]["output_selector"] = 0
    for invalid in (duplicate_id, duplicate_output):
        with pytest.raises(InvalidRegistrationError):
            definition(invalid)


@pytest.mark.parametrize("field", ["positive_outcome", "value_scale", "class_mapping"])
def test_definition_requires_label_outcome_and_continuous_output_semantics(
    synthetic_metadata, field
):
    del synthetic_metadata["labels"][0][field]
    with pytest.raises(InvalidRegistrationError):
        definition(synthetic_metadata)


def test_continuous_non_probability_scores_keep_their_semantics(synthetic_metadata):
    for label in synthetic_metadata["labels"]:
        label.update(
            value_kind="continuous_score",
            value_source="predict",
            value_scale={
                "minimum": None, "maximum": None,
                "meaning": "synthetic raw margin", "positive_direction": "increasing",
            },
            class_mapping={"positive_when": ">", "boundary": 0.0},
        )
    synthetic_metadata["adapter"]["capabilities"]["prediction_probability"] = False
    assert definition(synthetic_metadata).to_dict() == synthetic_metadata


@pytest.mark.parametrize("kind", ["hard_prediction", "binary", "0/1"])
def test_hard_only_output_declaration_is_not_continuous(synthetic_metadata, kind):
    synthetic_metadata["labels"][0]["value_kind"] = kind
    with pytest.raises(InvalidRegistrationError):
        definition(synthetic_metadata)


def test_registration_without_safety_data_or_package_preserves_exact_metadata(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        accepted = registry.register(declared, classifier, adapter, provider)
        retrieved = registry.get_metadata(declared.model_id, declared.model_version)
        assert accepted == retrieved == declared
        assert retrieved.to_dict() == synthetic_metadata
        usable = registry.resolve_usable(declared.model_id, declared.model_version)
        assert isinstance(usable, UsableRegistration)
        assert usable.metadata == declared
        assert usable.classifier is classifier
        assert usable.adapter is adapter
        assert usable.metadata.adapter.capabilities.explanation is False
    assert provider.calls == [(classifier, adapter)]


def test_accepted_metadata_survives_mutations_through_caller_references(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    declared = definition(synthetic_metadata)
    expected = declared.to_dict()
    with ModelRegistry(catalog_path) as registry:
        accepted = registry.register(declared, classifier, adapter, provider)
        synthetic_metadata["input"]["modalities"].append("changed")
        accepted.to_dict()["labels"].clear()
        registry.get_metadata(declared.model_id, declared.model_version).to_dict()[
            "adapter"
        ]["capabilities"]["prediction_probability"] = False
        assert registry.get_metadata(declared.model_id, declared.model_version).to_dict() == expected


def test_registration_lookup_and_attach_never_execute_patient_or_safety_work(
    catalog_path, synthetic_metadata, loaded_pair, monkeypatch
):
    classifier, adapter, provider = loaded_pair
    forbidden = []
    for name in (
        "predict", "predict_probability", "extract_features", "get_repeated_outputs",
        "get_modality_outputs", "get_domain_metadata", "explain", "get_input_metadata",
        "get_available_modalities",
    ):
        spy = Mock(side_effect=AssertionError("Unexpected patient-facing call."))
        monkeypatch.setattr(adapter, name, spy)
        forbidden.append(spy)
    for name in (
        "fit", "train", "calibrate", "extract_safety_signals", "select_policy",
        "assess", "prepare_safety_data", "deploy",
    ):
        spy = Mock(side_effect=AssertionError("Unexpected safety operation."))
        object.__setattr__(classifier, name, spy)
        forbidden.append(spy)
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        registry.register(declared, classifier, adapter, provider)
        registry.get_metadata(declared.model_id, declared.model_version)
        registry.attach(
            declared.model_id, declared.model_version, classifier, adapter, provider,
            definition=declared,
        )
        registry.resolve_usable(declared.model_id, declared.model_version)
    for spy in forbidden:
        spy.assert_not_called()


def test_attach_to_active_unbound_handle_requires_exact_validated_pair(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as owner, ModelRegistry(catalog_path) as other:
        owner.register(declared, classifier, adapter, provider)
        assert other.get_metadata(declared.model_id, declared.model_version) == declared
        with pytest.raises(UnattachedModelError):
            other.resolve_usable(declared.model_id, declared.model_version)
        usable = other.attach(
            declared.model_id, declared.model_version, classifier, adapter, provider,
            definition=declared,
        )
        assert other.resolve_usable(declared.model_id, declared.model_version) == usable
        assert usable.classifier is classifier
        assert len(provider.calls) == 2


def test_failed_active_attachment_does_not_replace_valid_pair(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        registry.register(declared, classifier, adapter, provider)
        changed = deepcopy(synthetic_metadata)
        changed["input"]["modalities"].append("other")
        with pytest.raises(BindingMismatchError):
            registry.attach(
                declared.model_id, declared.model_version, classifier, adapter, provider,
                definition=definition(changed),
            )
        with pytest.raises(IncompatibleAdapterError):
            registry.attach(
                declared.model_id, declared.model_version, object(), adapter, provider,
                definition=declared,
            )
        assert registry.resolve_usable(declared.model_id, declared.model_version).classifier is classifier


def test_registration_checks_identity_before_any_insert(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    synthetic_metadata["classifier_artifact"]["sha256"] = "0" * 64
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        with pytest.raises(BindingMismatchError):
            registry.register(declared, classifier, adapter, provider)
        with pytest.raises(UnknownModelError):
            registry.get_metadata(declared.model_id, declared.model_version)


def test_duplicate_failure_keeps_active_binding(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        registry.register(declared, classifier, adapter, provider)
        with pytest.raises(DuplicateRegistrationError):
            registry.register(declared, classifier, adapter, provider)
        assert registry.resolve_usable(declared.model_id, declared.model_version).adapter is adapter


def test_registration_reuses_existing_predict_for_non_probability_scores(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    adapter._capabilities = AdapterCapabilities()
    synthetic_metadata["adapter"]["capabilities"] = adapter.capabilities.to_dict()
    for label in synthetic_metadata["labels"]:
        label.update(
            value_kind="continuous_score", value_source="predict",
            value_scale={
                "minimum": None, "maximum": None,
                "meaning": "synthetic margin", "positive_direction": "decreasing",
            },
            class_mapping={"positive_when": "<=", "boundary": -0.25},
        )
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        registry.register(declared, classifier, adapter, provider)
        assert registry.get_metadata(declared.model_id, declared.model_version) == declared


def test_probability_declaration_requires_a_concrete_adapter_method(
    catalog_path, synthetic_metadata, loaded_pair
):
    class MissingProbabilityAdapter(ModelAdapter):
        def predict(self, patient_data, label):
            raise AssertionError("Must not predict.")

    classifier, _, provider = loaded_pair
    adapter = MissingProbabilityAdapter(AdapterCapabilities(prediction_probability=True))
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        with pytest.raises(IncompatibleAdapterError, match="predict_probability"):
            registry.register(declared, classifier, adapter, provider)


def test_capability_snapshot_must_match_live_adapter(
    catalog_path, synthetic_metadata, loaded_pair
):
    classifier, adapter, provider = loaded_pair
    adapter._capabilities = AdapterCapabilities()
    declared = definition(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        with pytest.raises(IncompatibleAdapterError):
            registry.register(declared, classifier, adapter, provider)
