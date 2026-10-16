"""T017/T019/T020: typed failures, privacy, and preservation of accepted state."""

import json
import sqlite3
import traceback

import pytest

from safira import AdapterCapabilities
from safira.registry import (
    BindingMismatchError,
    DuplicateRegistrationError,
    IncompatibleAdapterError,
    InvalidRegistrationError,
    ModelRegistry,
    RegisteredModelVersion,
    RegistryStorageError,
    UnattachedModelError,
    UnknownModelError,
    UnknownVersionError,
)


@pytest.fixture
def accepted(catalog_path, synthetic_metadata, loaded_pair):
    classifier, adapter, provider = loaded_pair
    declared = RegisteredModelVersion.from_dict(synthetic_metadata)
    with ModelRegistry(catalog_path) as registry:
        registry.register(declared, classifier, adapter, provider)
        yield registry, declared, classifier, adapter, provider


@pytest.mark.parametrize("key,error_type", [
    (("absent", "v1"), UnknownModelError),
    (("synthetic-model", "absent"), UnknownVersionError),
    (("synthetic-model", "latest"), UnknownVersionError),
    (("synthetic-model", " v1"), InvalidRegistrationError),
])
def test_lookup_failures_never_return_substitutes_or_change_state(accepted, key, error_type):
    registry, declared, _, _, _ = accepted
    prior = registry.resolve_usable(declared.model_id, declared.model_version)
    for operation in (registry.get_metadata, registry.resolve_usable):
        with pytest.raises(error_type):
            operation(*key)
    assert registry.resolve_usable(declared.model_id, declared.model_version) is prior


def test_duplicate_and_missing_identity_preserve_the_valid_binding(accepted):
    registry, declared, classifier, adapter, provider = accepted
    prior = registry.resolve_usable(declared.model_id, declared.model_version)
    with pytest.raises(DuplicateRegistrationError):
        registry.register(declared, classifier, adapter, provider)
    with pytest.raises(IncompatibleAdapterError):
        registry.attach(
            declared.model_id, declared.model_version, classifier, adapter, None,
            definition=declared,
        )
    assert registry.resolve_usable(declared.model_id, declared.model_version) is prior


def test_live_capability_mismatch_has_the_binding_error_category(accepted):
    registry, declared, classifier, adapter, provider = accepted
    prior = registry.resolve_usable(declared.model_id, declared.model_version)
    previous_capabilities = adapter.capabilities
    adapter._capabilities = AdapterCapabilities()
    try:
        with pytest.raises(BindingMismatchError):
            registry.attach(
                declared.model_id, declared.model_version, classifier, adapter, provider,
                definition=declared,
            )
        with pytest.raises(BindingMismatchError):
            registry.resolve_usable(declared.model_id, declared.model_version)
    finally:
        adapter._capabilities = previous_capabilities
    assert registry.resolve_usable(declared.model_id, declared.model_version) is prior


def test_unattached_record_remains_inspectable_but_not_usable(accepted, catalog_path):
    _, declared, classifier, adapter, _ = accepted
    with ModelRegistry(catalog_path) as other:
        assert other.get_metadata(declared.model_id, declared.model_version) == declared
        with pytest.raises(UnattachedModelError):
            other.resolve_usable(declared.model_id, declared.model_version)
        with pytest.raises(IncompatibleAdapterError):
            other.attach(
                declared.model_id, declared.model_version, classifier, adapter, None,
                definition=declared,
            )
        with pytest.raises(UnattachedModelError):
            other.resolve_usable(declared.model_id, declared.model_version)


@pytest.mark.parametrize("path", [
    (), ("input",), ("input", "schema", "synthetic-feature"), ("labels", 0),
    ("adapter",), ("preprocessing_identity",),
])
def test_restricted_payload_fields_are_rejected_without_echo_or_persistence(
    accepted, catalog_path, path, caplog
):
    registry, declared, classifier, adapter, provider = accepted
    prior = registry.resolve_usable(declared.model_id, declared.model_version)
    invalid = declared.to_dict()
    if path == ("preprocessing_identity",):
        invalid["preprocessing_identity"] = {"version": "synthetic-v1"}
    target = invalid
    for key in path:
        target = target[key]
    marker = "synthetic-private-payload-marker"
    target["patient_data"] = {"patient_id": marker, "observation": 42}
    with pytest.raises(InvalidRegistrationError) as error:
        registry.register(
            RegisteredModelVersion.from_dict(invalid), classifier, adapter, provider
        )
    assert marker not in "".join(traceback.format_exception(error.value))
    assert marker not in caplog.text
    assert marker.encode() not in catalog_path.read_bytes()
    assert registry.resolve_usable(declared.model_id, declared.model_version) is prior


@pytest.mark.parametrize("damage", [
    "missing_labels", "non_boolean", "wrong_identity", "unknown_version",
    "unsupported_task", "restricted_field", "non_finite", "duplicate_json_keys", "blob",
])
def test_semantically_invalid_rows_fail_closed_including_cached_usable_access(
    accepted, catalog_path, damage
):
    registry, declared, _, _, _ = accepted
    key = (declared.model_id, declared.model_version)
    prior = registry.resolve_usable(*key)
    invalid = declared.to_dict()
    if damage == "missing_labels":
        del invalid["labels"]
    elif damage == "non_boolean":
        invalid["adapter"]["capabilities"]["explanation"] = 0
    elif damage == "wrong_identity":
        invalid["model_id"] = "different-model"
    elif damage == "unknown_version":
        invalid["metadata_schema_version"] = 999
    elif damage == "unsupported_task":
        invalid["task_type"] = "regression"
    elif damage == "restricted_field":
        invalid["patient_data"] = "synthetic-restricted-row-marker"
    elif damage == "non_finite":
        invalid["labels"][0]["class_mapping"]["boundary"] = float("nan")
    raw = json.dumps(invalid)
    if damage == "duplicate_json_keys":
        raw = raw[:-1] + ', "model_id":"synthetic-model"}'
    elif damage == "blob":
        raw = raw.encode()
    with sqlite3.connect(catalog_path) as connection:
        connection.execute("UPDATE registrations SET metadata_json = ?", (raw,))
    for operation in (registry.get_metadata, registry.resolve_usable):
        with pytest.raises(RegistryStorageError) as error:
            operation(*key)
        assert "synthetic-restricted-row-marker" not in str(error.value)
    # Detection must not silently repair or rewrite invalid stored content.
    with sqlite3.connect(catalog_path) as connection:
        assert connection.execute("SELECT metadata_json FROM registrations").fetchone()[0] == raw
        connection.execute(
            "UPDATE registrations SET metadata_json = ?", (json.dumps(declared.to_dict()),)
        )
    assert registry.resolve_usable(*key) is prior


@pytest.mark.parametrize("damage", ["corrupt", "unknown_schema"])
def test_invalid_catalog_is_a_storage_failure_and_never_replaced(catalog_path, damage):
    if damage == "corrupt":
        catalog_path.write_bytes(b"synthetic corrupt catalog")
    else:
        with sqlite3.connect(catalog_path) as connection:
            connection.execute("PRAGMA user_version = 999")
    before = catalog_path.read_bytes()
    with pytest.raises(RegistryStorageError):
        ModelRegistry(catalog_path)
    assert catalog_path.read_bytes() == before


def test_failed_commit_does_not_publish_binding_or_damage_prior_records(accepted, catalog_path):
    registry, declared, classifier, adapter, provider = accepted
    prior = registry.resolve_usable(declared.model_id, declared.model_version)
    changed = declared.to_dict()
    changed["model_version"] = "v2"
    changed["adapter"]["associated_model_version"] = "v2"
    candidate = RegisteredModelVersion.from_dict(changed)
    with sqlite3.connect(catalog_path) as connection:
        connection.execute("""
            CREATE TRIGGER fail_commit BEFORE INSERT ON registrations
            BEGIN SELECT RAISE(ABORT, 'synthetic-private-storage-marker'); END
        """)
    with pytest.raises(RegistryStorageError) as error:
        registry.register(candidate, classifier, adapter, provider)
    assert "synthetic-private-storage-marker" not in "".join(traceback.format_exception(error.value))
    with pytest.raises(UnknownVersionError):
        registry.resolve_usable(candidate.model_id, candidate.model_version)
    assert registry.resolve_usable(declared.model_id, declared.model_version) is prior
    with sqlite3.connect(catalog_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 1
        connection.execute("DROP TRIGGER fail_commit")
    registry.register(candidate, classifier, adapter, provider)
    assert registry.get_metadata(candidate.model_id, candidate.model_version) == candidate
