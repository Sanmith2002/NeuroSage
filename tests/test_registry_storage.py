"""T002/T005: storage primitives, independent of future definition classes."""

from copy import deepcopy
import json
import sqlite3

import pytest

from safira.registry.exceptions import (
    DuplicateRegistrationError,
    InvalidRegistrationError,
    RegistryStorageError,
    UnknownModelError,
    UnknownVersionError,
)
from safira.registry.storage import MetadataStore, SCHEMA_VERSION


@pytest.fixture
def metadata_validator(synthetic_metadata):
    # Only a test codec boundary, not the future production label validator.
    template = deepcopy(synthetic_metadata)

    def check(value, expected):
        if type(value) is not type(expected):
            raise ValueError("Invalid test declaration type.")
        if isinstance(value, dict):
            if value.keys() != expected.keys():
                raise ValueError("Unexpected test declaration field.")
            for key in value:
                check(value[key], expected[key])
        elif isinstance(value, list):
            for item in value:
                check(item, expected[0])

    def validate(record):
        check(record, template)

    return validate


def insert(store, record):
    store.insert(record["model_id"], record["model_version"], record)


def test_schema_initialization_and_canonical_round_trip(
    catalog_path, synthetic_metadata, metadata_validator
):
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        insert(store, synthetic_metadata)
        assert store.get("synthetic-model", "v1") == synthetic_metadata
    with sqlite3.connect(catalog_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        raw = connection.execute("SELECT metadata_json FROM registrations").fetchone()[0]
        assert raw == json.dumps(
            synthetic_metadata, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )


def test_close_reopen_survives_and_detaches_values(
    catalog_path, synthetic_metadata, metadata_validator
):
    expected = deepcopy(synthetic_metadata)
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        insert(store, synthetic_metadata)
        synthetic_metadata["input"]["modalities"].append("changed")
        result = store.get("synthetic-model", "v1")
        result["labels"][0]["label_id"] = "changed"
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as reopened:
        assert reopened.get("synthetic-model", "v1") == expected


def test_duplicate_is_explicit_and_preserves_original(
    catalog_path, synthetic_metadata, metadata_validator
):
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        insert(store, synthetic_metadata)
        changed = deepcopy(synthetic_metadata)
        changed["preprocessing_identity"] = "other"
        for duplicate in (synthetic_metadata, changed):
            with pytest.raises(DuplicateRegistrationError):
                insert(store, duplicate)
        assert store.get("synthetic-model", "v1") == synthetic_metadata


def test_composite_key_and_exact_missing_lookup(
    catalog_path, synthetic_metadata, metadata_validator
):
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        for model_id, version in (("model-a", "v1"), ("model-a", "v2"), ("model-b", "v1")):
            record = deepcopy(synthetic_metadata)
            record.update(model_id=model_id, model_version=version)
            insert(store, record)
            assert store.get(model_id, version) == record
        with pytest.raises(UnknownModelError):
            store.get("absent", "v1")
        with pytest.raises(UnknownVersionError):
            store.get("model-a", "v3")


@pytest.mark.parametrize("bad_file", [b"not a SQLite catalog", b""])
def test_existing_invalid_file_is_not_reinitialized(catalog_path, metadata_validator, bad_file):
    catalog_path.write_bytes(bad_file)
    with pytest.raises(RegistryStorageError):
        MetadataStore(catalog_path, validate_metadata=metadata_validator)
    assert catalog_path.read_bytes() == bad_file


def test_unknown_schema_fails_without_modifying_catalog(catalog_path, metadata_validator):
    with sqlite3.connect(catalog_path) as connection:
        connection.execute("PRAGMA user_version = 999")
        connection.execute("CREATE TABLE unrelated (value TEXT)")
    before = catalog_path.read_bytes()
    with pytest.raises(RegistryStorageError):
        MetadataStore(catalog_path, validate_metadata=metadata_validator)
    assert catalog_path.read_bytes() == before


def test_wrong_table_shape_is_a_storage_error(catalog_path, metadata_validator):
    with sqlite3.connect(catalog_path) as connection:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.execute("CREATE TABLE registrations (model_id TEXT)")
    with pytest.raises(RegistryStorageError):
        MetadataStore(catalog_path, validate_metadata=metadata_validator)


@pytest.mark.parametrize("invalid_value", [b"binary material", object(), float("nan"), float("inf")])
def test_non_declarative_values_never_reach_storage(
    catalog_path, synthetic_metadata, metadata_validator, invalid_value
):
    synthetic_metadata["preprocessing_identity"] = invalid_value
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        with pytest.raises(InvalidRegistrationError):
            insert(store, synthetic_metadata)
        with pytest.raises(UnknownModelError):
            store.get("synthetic-model", "v1")


def test_unknown_payload_rejected_without_echo_or_persistence(
    catalog_path, synthetic_metadata, metadata_validator
):
    marker = "synthetic-restricted-marker"
    synthetic_metadata["patient_data"] = marker
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        with pytest.raises(InvalidRegistrationError) as error:
            insert(store, synthetic_metadata)
    assert marker not in str(error.value)
    assert marker.encode() not in catalog_path.read_bytes()


def test_key_mismatch_cannot_be_persisted(catalog_path, synthetic_metadata, metadata_validator):
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        with pytest.raises(InvalidRegistrationError):
            store.insert("different", "v1", synthetic_metadata)


@pytest.mark.parametrize("raw", ['not JSON', '{"patient_data":"synthetic-marker"}'])
def test_invalid_stored_payload_fails_closed(
    catalog_path, synthetic_metadata, metadata_validator, raw
):
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        insert(store, synthetic_metadata)
        with sqlite3.connect(catalog_path) as connection:
            connection.execute("UPDATE registrations SET metadata_json = ?", (raw,))
        with pytest.raises(RegistryStorageError) as error:
            store.get("synthetic-model", "v1")
        assert "synthetic-marker" not in str(error.value)


def test_non_key_constraint_is_not_a_duplicate_and_transaction_rolls_back(
    catalog_path, synthetic_metadata, metadata_validator
):
    with MetadataStore(catalog_path, validate_metadata=metadata_validator) as store:
        with sqlite3.connect(catalog_path) as connection:
            connection.execute("""
                CREATE TRIGGER reject_insert BEFORE INSERT ON registrations
                BEGIN SELECT RAISE(ABORT, 'synthetic-internal-error'); END
            """)
        with pytest.raises(RegistryStorageError) as error:
            insert(store, synthetic_metadata)
        assert "synthetic-internal-error" not in str(error.value)
        with sqlite3.connect(catalog_path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0
            connection.execute("DROP TRIGGER reject_insert")
        insert(store, synthetic_metadata)
        assert store.get("synthetic-model", "v1") == synthetic_metadata


def test_closed_store_fails_explicitly(catalog_path, metadata_validator):
    store = MetadataStore(catalog_path, validate_metadata=metadata_validator)
    store.close()
    store.close()
    with pytest.raises(RegistryStorageError):
        store.get("synthetic-model", "v1")


def test_validator_is_required_before_creating_a_catalog(catalog_path):
    with pytest.raises(InvalidRegistrationError):
        MetadataStore(catalog_path, validate_metadata=None)
    assert not catalog_path.exists()
