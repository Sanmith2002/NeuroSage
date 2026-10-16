"""Internal SQLite foundation for immutable declarative metadata.

The definitions layer must supply a validator; this is not a public arbitrary
JSON store. The validator raises for anything outside its structural schema,
including observations or restricted fields. Full registration semantics and
live bindings belong to later phases. No executable objects are serialized.
"""

from collections.abc import Callable
from copy import deepcopy
import json
import math
from pathlib import Path
import sqlite3
import unicodedata

from safira.registry.exceptions import (
    DuplicateRegistrationError,
    InvalidRegistrationError,
    RegistryStorageError,
    UnknownModelError,
    UnknownVersionError,
)


SCHEMA_VERSION = 1


def _check_key(value: str, field: str) -> None:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise InvalidRegistrationError(
            f"{field} must be a nonblank exact identifier without control characters."
        )


def _check_json(value: object) -> None:
    """Allow only plain JSON values, finite numbers, and string object keys."""
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _check_json(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("Non-string metadata key.")
            _check_json(item)
        return
    raise ValueError("Non-declarative metadata value.")


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


class MetadataStore:
    """File-backed storage primitive with mandatory schema validation.

    ``validate_metadata`` must raise on invalid declarations. It is called on
    insertion and decoding with a detached plain JSON dictionary. Production
    callers must use the registration definitions validator, not a no-op.
    One store owns one connection; use separate instances for separate threads.
    """

    def __init__(
        self,
        storage_path: str | Path,
        *,
        validate_metadata: Callable[[dict[str, object]], None],
    ) -> None:
        if not callable(validate_metadata):
            raise InvalidRegistrationError("A declarative metadata validator is required.")
        self._validate_metadata = validate_metadata
        self._connection: sqlite3.Connection | None = None
        try:
            path = Path(storage_path)
            if str(path) == ":memory:":
                raise InvalidRegistrationError("A persistent catalog file path is required.")
            existed = path.exists()
            if existed and path.stat().st_size == 0:
                raise RegistryStorageError("Existing catalog has no recognized storage schema.")
            connection = sqlite3.connect(path)
            self._connection = connection
            if existed:
                self._check_schema()
            else:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute("""
                        CREATE TABLE registrations (
                            model_id TEXT NOT NULL,
                            model_version TEXT NOT NULL,
                            metadata_json TEXT NOT NULL,
                            PRIMARY KEY (model_id, model_version)
                        ) WITHOUT ROWID
                    """)
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = FULL")
        except (sqlite3.Error, OSError, TypeError, ValueError):
            self.close()
            raise RegistryStorageError(
                "Catalog could not be safely opened or initialized."
            ) from None
        except (RegistryStorageError, InvalidRegistrationError):
            self.close()
            raise

    def _open_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RegistryStorageError("Catalog is closed.")
        return self._connection

    def _check_schema(self) -> None:
        connection = self._open_connection()
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        columns = connection.execute("PRAGMA table_info(registrations)").fetchall()
        shape = [(row[1], row[2], row[3], row[5]) for row in columns]
        expected = [
            ("model_id", "TEXT", 1, 1),
            ("model_version", "TEXT", 1, 2),
            ("metadata_json", "TEXT", 1, 0),
        ]
        if version != SCHEMA_VERSION or shape != expected:
            raise RegistryStorageError("Catalog storage schema is unsupported or invalid.")
        if connection.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
            raise RegistryStorageError("Catalog integrity check failed.")

    def _validate_record(
        self, model_id: str, model_version: str, record: object
    ) -> None:
        _check_json(record)
        if (
            type(record) is not dict
            or record.get("model_id") != model_id
            or record.get("model_version") != model_version
            or type(record.get("metadata_schema_version")) is not int
            or record["metadata_schema_version"] != SCHEMA_VERSION
        ):
            raise ValueError("Invalid metadata identity or serialization version.")
        self._validate_metadata(deepcopy(record))

    def insert(
        self, model_id: str, model_version: str, metadata: dict[str, object]
    ) -> None:
        """Commit one validated snapshot. Existing exact keys always fail."""
        _check_key(model_id, "model_id")
        _check_key(model_version, "model_version")
        connection = self._open_connection()
        try:
            _check_json(metadata)
            payload = json.dumps(
                metadata, sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            )
            payload.encode("utf-8")
            self._validate_record(model_id, model_version, json.loads(payload))
        except Exception:
            raise InvalidRegistrationError(
                "Registration metadata must match the declarative schema and exact key."
            ) from None
        try:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO registrations (model_id, model_version, metadata_json) "
                    "VALUES (?, ?, ?)",
                    (model_id, model_version, payload),
                )
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY:
                raise DuplicateRegistrationError(
                    "The exact model identifier/version is already registered."
                ) from None
            raise RegistryStorageError("Catalog insertion failed a storage constraint.") from None
        except sqlite3.Error:
            raise RegistryStorageError("Catalog insertion could not be committed.") from None

    def get(self, model_id: str, model_version: str) -> dict[str, object]:
        """Read an exact validated snapshot; never substitute another version."""
        _check_key(model_id, "model_id")
        _check_key(model_version, "model_version")
        connection = self._open_connection()
        try:
            row = connection.execute(
                "SELECT metadata_json FROM registrations "
                "WHERE model_id = ? AND model_version = ?",
                (model_id, model_version),
            ).fetchone()
            if row is None:
                model_exists = connection.execute(
                    "SELECT 1 FROM registrations WHERE model_id = ? LIMIT 1", (model_id,)
                ).fetchone()
                if model_exists is None:
                    raise UnknownModelError(
                        "No registration exists for the requested model identifier."
                    )
                raise UnknownVersionError("The requested exact model version is not registered.")
        except sqlite3.Error:
            raise RegistryStorageError("Catalog metadata could not be read.") from None
        try:
            record = json.loads(row[0], object_pairs_hook=_json_object)
            self._validate_record(model_id, model_version, record)
        except Exception:
            raise RegistryStorageError(
                "Stored registration metadata is invalid or unsupported."
            ) from None
        return record

    def close(self) -> None:
        """Release the owned connection; repeated closes are harmless."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "MetadataStore":
        self._open_connection()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
