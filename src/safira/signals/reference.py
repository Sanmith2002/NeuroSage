"""Internal Feature 004 reference fitting helpers.

This module is intentionally not re-exported from ``safira.signals``. Inputs are
pure value objects; they are not proof of Feature 003 verification. Public use on
Feature 003 data remains blocked until the row-complete verifier gate in T028.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from math import isfinite, sqrt
from types import MappingProxyType
from typing import Mapping
import unicodedata

from safira.signals.base import SignalState
from safira.signals.exceptions import SignalCompatibilityError, SignalInputError, SignalProtocolError
from safira.signals.records import SignalMethodConfig, SignalSourceKey, _freeze, _plain
from safira.signals.validation import _validate_fitted_reference


_FOLD_ALGORITHM = "sha256_seed_nul_group_mod_v1"


def _text(value, code):
    if (type(value) is not str or not value or value != value.strip()
            or any(unicodedata.category(char) == "Cc" for char in value)):
        raise SignalInputError(code)
    return value


def _finite_vector(values, code="reference_vector_invalid"):
    if not isinstance(values, (tuple, list)) or not values:
        raise SignalInputError(code)
    result = []
    for value in values:
        if type(value) not in (int, float):
            raise SignalInputError(code)
        try:
            converted = float(value)
        except (OverflowError, ValueError):
            raise SignalInputError(code) from None
        if not isfinite(converted):
            raise SignalInputError(code)
        result.append(converted)
    return tuple(result)


@dataclass(frozen=True)
class ReferenceCompatibilityKey:
    """Exact identity/scope that a fitted reference can serve."""

    source_key: SignalSourceKey
    method_id: str
    method_version: str
    parameters: Mapping[str, object]
    evidence_schema: str
    preprocessing_identity: str
    dataset_id: str
    protocol_id: str
    protocol_version: str
    manifest_reference: str
    reference_cohort: str = "training"

    def __post_init__(self):
        if type(self.source_key) is not SignalSourceKey:
            raise SignalInputError("reference_source_invalid")
        for attr in ("method_id", "method_version", "evidence_schema", "preprocessing_identity",
                     "dataset_id", "protocol_id", "protocol_version", "manifest_reference",
                     "reference_cohort"):
            _text(getattr(self, attr), "reference_scope_invalid")
        try:
            object.__setattr__(self, "parameters", _freeze(self.parameters, "reference_parameters"))
        except Exception:
            raise SignalInputError("reference_parameters_invalid") from None

    def to_dict(self):
        return {
            "source_key": self.source_key.to_dict(), "method_id": self.method_id,
            "method_version": self.method_version, "parameters": _plain(self.parameters),
            "evidence_schema": self.evidence_schema,
            "preprocessing_identity": self.preprocessing_identity, "dataset_id": self.dataset_id,
            "protocol_id": self.protocol_id, "protocol_version": self.protocol_version,
            "manifest_reference": self.manifest_reference, "reference_cohort": self.reference_cohort,
        }


@dataclass(frozen=True)
class ReferenceFitConfig:
    compatibility_key: ReferenceCompatibilityKey
    method_config: SignalMethodConfig
    fold_count: int
    seed: str
    fold_algorithm: str = _FOLD_ALGORITHM
    explicit_assignments: Mapping[str, int] | None = field(default=None, repr=False)

    def __post_init__(self):
        if type(self.compatibility_key) is not ReferenceCompatibilityKey:
            raise SignalProtocolError("reference_key_required")
        if type(self.method_config) is not SignalMethodConfig:
            raise SignalProtocolError("method_config_required")
        if type(self.fold_count) is not int or self.fold_count < 2:
            raise SignalProtocolError("fold_count_invalid")
        _text(self.seed, "fold_seed_invalid")
        if self.fold_algorithm != _FOLD_ALGORITHM:
            raise SignalProtocolError("fold_algorithm_unsupported")
        key = self.compatibility_key
        method = self.method_config
        if (key.method_id != method.method_id or key.method_version != method.method_version
                or dict(key.parameters) != dict(method.parameters)):
            raise SignalProtocolError("reference_method_mismatch")
        if self.explicit_assignments is not None:
            if not isinstance(self.explicit_assignments, Mapping):
                raise SignalProtocolError("fold_assignments_invalid")
            copied = dict(self.explicit_assignments)
            if any(type(group) is not str or type(fold) is not int
                   or fold < 0 or fold >= self.fold_count for group, fold in copied.items()):
                raise SignalProtocolError("fold_assignments_invalid")
            object.__setattr__(self, "explicit_assignments", MappingProxyType(copied))
        if method.method_id == "knn_distance":
            params = method.parameters
            if (type(params.get("k")) is not int or params["k"] < 1
                    or params.get("metric") != "euclidean"):
                raise SignalProtocolError("knn_parameters_invalid")
        elif method.method_id == "domain_familiarity":
            params = method.parameters
            required = ("category_field", "category_mapping_version", "privacy_approval_ref")
            if any(type(params.get(name)) is not str or not params[name].strip() for name in required):
                raise SignalProtocolError("domain_parameters_invalid")
        else:
            raise SignalProtocolError("reference_method_unsupported")


@dataclass(frozen=True, repr=False)
class ReferenceObservation:
    """Internal row; patient group and raw evidence are excluded from repr."""

    row_key: str
    source_key: SignalSourceKey
    patient_group_ref: str = field(repr=False)
    evidence_schema: str
    preprocessing_identity: str
    vector: tuple[float, ...] | None = field(default=None, repr=False)
    domain_category: str | None = field(default=None, repr=False)
    evidence_ref: str = field(default="", repr=False)
    partition_role: str = field(default="train", repr=False)

    def __post_init__(self):
        _text(self.row_key, "reference_row_key_invalid")
        _text(self.patient_group_ref, "patient_group_invalid")
        _text(self.evidence_schema, "evidence_schema_invalid")
        _text(self.preprocessing_identity, "preprocessing_invalid")
        if type(self.source_key) is not SignalSourceKey:
            raise SignalInputError("reference_source_invalid")
        if self.evidence_ref:
            _text(self.evidence_ref, "reference_evidence_ref_invalid")
        if self.partition_role != "train":
            raise SignalInputError("reference_partition_invalid")
        if self.vector is not None:
            object.__setattr__(self, "vector", _finite_vector(self.vector))
        if self.domain_category is not None and type(self.domain_category) is not str:
            raise SignalInputError("domain_category_invalid")


@dataclass(frozen=True, repr=False)
class FittedReferenceState:
    """Internal immutable state. Raw representations/categories are never serialized."""

    compatibility_key: ReferenceCompatibilityKey
    method_config: SignalMethodConfig
    status: str
    vectors: tuple[tuple[float, ...], ...] = field(default=(), repr=False)
    vocabulary: frozenset[str] = field(default_factory=frozenset, repr=False)
    evidence_refs: tuple[str, ...] = field(default=(), repr=False)
    fold_algorithm: str = _FOLD_ALGORITHM
    fold_count: int = 0
    seed: str = field(default="", repr=False)
    digest: str = ""

    def __post_init__(self):
        if (type(self.compatibility_key) is not ReferenceCompatibilityKey
                or type(self.method_config) is not SignalMethodConfig
                or self.compatibility_key.method_id != self.method_config.method_id
                or self.compatibility_key.method_version != self.method_config.method_version
                or dict(self.compatibility_key.parameters) != dict(self.method_config.parameters)):
            raise SignalInputError("reference_method_mismatch")
        if self.status not in {state.value for state in SignalState}:
            raise SignalInputError("reference_state_invalid")
        vectors = tuple(_finite_vector(vector) for vector in self.vectors)
        if vectors and any(len(vector) != len(vectors[0]) for vector in vectors):
            raise SignalInputError("reference_dimension_invalid")
        if self.status == SignalState.AVAILABLE.value:
            if (self.method_config.method_id == "knn_distance"
                    and len(vectors) < self.method_config.parameters["k"]):
                raise SignalInputError("reference_support_insufficient")
            if self.method_config.method_id == "domain_familiarity" and not self.vocabulary:
                raise SignalInputError("domain_reference_empty")
        if self.fold_count < 2 or self.fold_algorithm != _FOLD_ALGORITHM:
            raise SignalInputError("reference_fold_provenance_invalid")
        _text(self.seed, "reference_fold_seed_invalid")
        if any(type(category) is not str or not category or category != category.strip()
               or any(unicodedata.category(char) == "Cc" for char in category)
               for category in self.vocabulary):
            raise SignalInputError("domain_vocabulary_invalid")
        object.__setattr__(self, "vectors", vectors)
        object.__setattr__(self, "vocabulary", frozenset(self.vocabulary))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        if not self.digest:
            # Group/row identifiers are excluded so opaque reference renaming has
            # no effect on the final full-training reference fingerprint.
            material = {
                "key": self.compatibility_key.to_dict(), "method": self.method_config.to_dict(),
                "status": self.status,
                "vectors": sorted([list(v) for v in vectors]),
                "vocabulary": sorted(self.vocabulary),
                "evidence_refs": sorted(self.evidence_refs),
                "fold_algorithm": self.fold_algorithm, "fold_count": self.fold_count,
                "seed": self.seed,
            }
            digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            object.__setattr__(self, "digest", digest)

    def __repr__(self):
        return (f"FittedReferenceState(method_id={self.compatibility_key.method_id!r}, "
                f"status={self.status!r}, item_count={len(self.vectors) or len(self.vocabulary)}, "
                f"digest={self.digest[:12]!r})")


@dataclass(frozen=True, repr=False)
class ReferenceValue:
    row_key: str | None
    state: str
    value: float | str | None
    reason_code: str | None = None
    fold_id: int | None = None
    reference_row_keys: tuple[str, ...] = field(default=(), repr=False)
    compatibility_key: ReferenceCompatibilityKey | None = field(default=None, repr=False)
    method_config: SignalMethodConfig | None = field(default=None, repr=False)
    reference_digest: str | None = field(default=None, repr=False)
    evidence_refs: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self):
        if self.state not in {state.value for state in SignalState}:
            raise SignalInputError("reference_result_state_invalid")
        if self.state == SignalState.AVAILABLE.value:
            if (self.value is None or type(self.compatibility_key) is not ReferenceCompatibilityKey
                    or type(self.method_config) is not SignalMethodConfig
                    or not self.reference_digest or not self.evidence_refs):
                raise SignalInputError("reference_result_value_invalid")
            if self.method_config.method_id == "knn_distance":
                if (type(self.value) not in (int, float) or type(self.value) is bool
                        or not isfinite(float(self.value)) or self.value < 0):
                    raise SignalInputError("reference_result_value_invalid")
            elif self.method_config.method_id == "domain_familiarity":
                if self.value not in ("seen", "unseen"):
                    raise SignalInputError("reference_result_value_invalid")
        elif self.value is not None and self.state != SignalState.AVAILABLE.value:
            raise SignalInputError("reference_result_value_invalid")
        if self.row_key is not None:
            _text(self.row_key, "reference_row_key_invalid")
        object.__setattr__(self, "reference_row_keys", tuple(self.reference_row_keys))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        if any(type(key) is not str or not key for key in self.reference_row_keys):
            raise SignalInputError("reference_row_key_invalid")
        if any(type(ref) is not str or not ref for ref in self.evidence_refs):
            raise SignalInputError("reference_evidence_ref_invalid")

    def __repr__(self):
        return (f"ReferenceValue(row_key={self.row_key!r}, state={self.state!r}, "
                f"value={self.value!r}, fold_id={self.fold_id!r})")


def _reference_value(row_key, state, value, reason_code=None, fold_id=None,
                     reference_row_keys=(), fitted_state=None, query_evidence_ref=None):
    evidence_refs = ()
    if fitted_state is not None:
        evidence_refs = tuple(fitted_state.evidence_refs)
    if query_evidence_ref is not None:
        evidence_refs += (_text(query_evidence_ref, "query_evidence_ref_invalid"),)
    evidence_refs = tuple(sorted(set(evidence_refs)))
    if fitted_state is None:
        return ReferenceValue(row_key, state, value, reason_code, fold_id, tuple(reference_row_keys),
                              evidence_refs=evidence_refs)
    return ReferenceValue(
        row_key, state, value, reason_code, fold_id, tuple(reference_row_keys),
        fitted_state.compatibility_key, fitted_state.method_config, fitted_state.digest,
        evidence_refs,
    )


def _assert_reference_compatible(state: FittedReferenceState, expected: ReferenceCompatibilityKey):
    return _validate_fitted_reference(state, expected)


def assign_group_folds(group_refs, *, seed: str, fold_count: int, explicit_assignments=None):
    """Assign whole groups with the documented SHA256(seed || NUL || group) rule."""
    _text(seed, "fold_seed_invalid")
    if type(fold_count) is not int or fold_count < 2:
        raise SignalProtocolError("fold_count_invalid")
    groups = tuple(group_refs)
    if any(type(group) is not str or not group for group in groups):
        raise SignalInputError("patient_group_invalid")
    unique_groups = set(groups)
    if explicit_assignments is not None:
        if not isinstance(explicit_assignments, Mapping):
            raise SignalProtocolError("fold_assignments_invalid")
        copied = dict(explicit_assignments)
        if set(copied) != unique_groups or any(type(fold) is not int or fold < 0 or fold >= fold_count
                                               for fold in copied.values()):
            raise SignalProtocolError("fold_assignments_incomplete")
        return MappingProxyType(copied)
    seed_bytes = seed.encode("utf-8")
    assignments = {}
    for group in unique_groups:
        digest = hashlib.sha256(seed_bytes + b"\0" + group.encode("utf-8")).digest()
        assignments[group] = int.from_bytes(digest, "big", signed=False) % fold_count
    return MappingProxyType(assignments)


def _validate_rows(rows, config, *, require_complete_assignments=True):
    rows = tuple(rows)
    if any(type(row) is not ReferenceObservation for row in rows):
        raise SignalInputError("reference_rows_invalid")
    row_keys = [row.row_key for row in rows]
    if len(row_keys) != len(set(row_keys)):
        raise SignalInputError("reference_row_duplicate")
    key = config.compatibility_key
    for row in rows:
        if not row.evidence_ref:
            raise SignalInputError("reference_evidence_lineage_missing")
        if row.source_key != key.source_key:
            raise SignalCompatibilityError("reference_source_mismatch")
        if row.evidence_schema != key.evidence_schema:
            raise SignalCompatibilityError("reference_schema_mismatch")
        if row.preprocessing_identity != key.preprocessing_identity:
            raise SignalCompatibilityError("reference_preprocessing_mismatch")
    if require_complete_assignments and config.explicit_assignments is not None:
        groups = {row.patient_group_ref for row in rows}
        if set(config.explicit_assignments) != groups:
            raise SignalProtocolError("fold_assignments_incomplete")
    return rows


def _state(config, *, status, vectors=(), vocabulary=(), rows=()):
    return FittedReferenceState(
        config.compatibility_key, config.method_config, status,
        tuple(vectors), frozenset(vocabulary),
        tuple(row.evidence_ref for row in rows), config.fold_algorithm, config.fold_count, config.seed,
    )


def knn_distance(query, reference_vectors, *, k: int, metric: str):
    query_vector = _finite_vector(query, "query_vector_invalid")
    if type(k) is not int or k < 1 or metric != "euclidean":
        raise SignalInputError("knn_parameters_invalid")
    vectors = tuple(_finite_vector(vector, "reference_vector_invalid") for vector in reference_vectors)
    if len(vectors) < k:
        raise SignalInputError("reference_support_insufficient")
    if any(len(vector) != len(query_vector) for vector in vectors):
        raise SignalInputError("reference_dimension_invalid")
    distances = []
    for vector in vectors:
        distance = sqrt(sum((left - right) ** 2 for left, right in zip(query_vector, vector)))
        if not isfinite(distance):
            raise SignalInputError("distance_result_invalid")
        distances.append(distance)
    distances.sort()
    return distances[k - 1]


def fit_knn_reference(rows, config: ReferenceFitConfig, *, _crossfit_reference=False) -> FittedReferenceState:
    if config.method_config.method_id != "knn_distance":
        raise SignalProtocolError("reference_method_mismatch")
    rows = _validate_rows(rows, config, require_complete_assignments=not _crossfit_reference)
    if not rows:
        return _state(config, status=SignalState.INSUFFICIENT_EVIDENCE.value)
    available = tuple(row for row in rows if row.vector is not None)
    if not available:
        return _state(config, status=SignalState.UNAVAILABLE.value)
    vectors = tuple(row.vector for row in available)
    if len(vectors) < config.method_config.parameters["k"]:
        return _state(config, status=SignalState.INSUFFICIENT_EVIDENCE.value, vectors=vectors, rows=available)
    # Check a shared dimension before constructing an applicable state.
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise SignalInputError("reference_dimension_invalid")
    return _state(config, status=SignalState.AVAILABLE.value, vectors=vectors, rows=available)


def apply_knn_reference(state, query, expected_key: ReferenceCompatibilityKey,
                        *, query_evidence_ref: str | None = None) -> ReferenceValue:
    if state is None:
        return _reference_value(None, SignalState.NOT_READY.value, None, "reference_not_ready")
    _assert_reference_compatible(state, expected_key)
    if query_evidence_ref is None:
        return _reference_value(None, SignalState.NOT_READY.value, None, "query_provenance_not_ready",
                                fitted_state=state)
    if state.status != SignalState.AVAILABLE.value:
        return _reference_value(None, state.status, None, f"reference_{state.status}", fitted_state=state,
                                query_evidence_ref=query_evidence_ref)
    try:
        value = knn_distance(query, state.vectors, k=state.method_config.parameters["k"],
                             metric=state.method_config.parameters["metric"])
    except SignalInputError as error:
        code = error.reason_code
        state_code = (SignalState.INSUFFICIENT_EVIDENCE.value if code == "reference_support_insufficient"
                      else SignalState.INVALID.value)
        return _reference_value(None, state_code, None, code, fitted_state=state,
                                query_evidence_ref=query_evidence_ref)
    return _reference_value(None, SignalState.AVAILABLE.value, value, fitted_state=state,
                            query_evidence_ref=query_evidence_ref)


def fit_domain_reference(rows, config: ReferenceFitConfig, *, _crossfit_reference=False) -> FittedReferenceState:
    if config.method_config.method_id != "domain_familiarity":
        raise SignalProtocolError("reference_method_mismatch")
    rows = _validate_rows(rows, config, require_complete_assignments=not _crossfit_reference)
    if not rows:
        return _state(config, status=SignalState.INSUFFICIENT_EVIDENCE.value)
    categories = []
    usable_rows = []
    invalid = False
    for row in rows:
        category = row.domain_category
        if category is None:
            continue
        if (not category or category != category.strip()
                or any(unicodedata.category(char) == "Cc" for char in category)):
            invalid = True
            continue
        categories.append(category)
        usable_rows.append(row)
    if invalid:
        return _state(config, status=SignalState.INVALID.value, rows=usable_rows)
    if not categories:
        return _state(config, status=SignalState.MISSING.value)
    return _state(config, status=SignalState.AVAILABLE.value, vocabulary=categories, rows=usable_rows)


def apply_domain_reference(state, category, expected_key: ReferenceCompatibilityKey,
                           *, query_evidence_ref: str | None = None) -> ReferenceValue:
    if state is None:
        return _reference_value(None, SignalState.NOT_READY.value, None, "reference_not_ready")
    _assert_reference_compatible(state, expected_key)
    if query_evidence_ref is None:
        return _reference_value(None, SignalState.NOT_READY.value, None, "query_provenance_not_ready",
                                fitted_state=state)
    if state.status != SignalState.AVAILABLE.value:
        return _reference_value(None, state.status, None, f"reference_{state.status}", fitted_state=state,
                                query_evidence_ref=query_evidence_ref)
    if category is None:
        return _reference_value(None, SignalState.MISSING.value, None, "domain_evidence_missing", fitted_state=state,
                                query_evidence_ref=query_evidence_ref)
    if (type(category) is not str or not category or category != category.strip()
            or any(unicodedata.category(char) == "Cc" for char in category)):
        return _reference_value(None, SignalState.INVALID.value, None, "domain_category_invalid", fitted_state=state,
                                query_evidence_ref=query_evidence_ref)
    return _reference_value(None, SignalState.AVAILABLE.value,
                             "seen" if category in state.vocabulary else "unseen", fitted_state=state,
                             query_evidence_ref=query_evidence_ref)


def _crossfit(rows, config: ReferenceFitConfig, method):
    rows = _validate_rows(rows, config)
    folds = assign_group_folds(
        (row.patient_group_ref for row in rows), seed=config.seed,
        fold_count=config.fold_count, explicit_assignments=config.explicit_assignments,
    )
    outputs = []
    for row in rows:
        fold = folds[row.patient_group_ref]
        reference_rows = tuple(other for other in rows if folds[other.patient_group_ref] != fold)
        # The set of withheld rows includes every visit/label/contributor record
        # sharing this verified patient-group reference.
        if method == "knn_distance":
            state = fit_knn_reference(reference_rows, config, _crossfit_reference=True) if reference_rows else _state(
                config, status=SignalState.INSUFFICIENT_EVIDENCE.value,
            )
            if row.vector is None:
                outputs.append(_reference_value(row.row_key, SignalState.MISSING.value, None,
                                                "representation_missing", fold,
                                                tuple(ref.row_key for ref in reference_rows), state,
                                                row.evidence_ref))
            elif state.status != SignalState.AVAILABLE.value:
                outputs.append(_reference_value(row.row_key, SignalState.INSUFFICIENT_EVIDENCE.value, None,
                                                "reference_support_insufficient", fold,
                                                tuple(ref.row_key for ref in reference_rows), state,
                                                row.evidence_ref))
            else:
                try:
                    value = knn_distance(row.vector, state.vectors,
                                         k=config.method_config.parameters["k"],
                                         metric=config.method_config.parameters["metric"])
                except SignalInputError:
                    outputs.append(_reference_value(row.row_key, SignalState.INSUFFICIENT_EVIDENCE.value,
                                                    None, "reference_support_insufficient", fold,
                                                    tuple(ref.row_key for ref in reference_rows), state,
                                                    row.evidence_ref))
                else:
                    outputs.append(_reference_value(row.row_key, SignalState.AVAILABLE.value,
                                                    value, None, fold,
                                                    tuple(ref.row_key for ref in reference_rows), state,
                                                    row.evidence_ref))
        else:
            state = fit_domain_reference(reference_rows, config, _crossfit_reference=True) if reference_rows else _state(
                config, status=SignalState.INSUFFICIENT_EVIDENCE.value,
            )
            if state.status != SignalState.AVAILABLE.value:
                failure_state = (SignalState.INVALID.value if state.status == SignalState.INVALID.value
                                 else SignalState.INSUFFICIENT_EVIDENCE.value)
                reason = ("domain_reference_invalid" if failure_state == SignalState.INVALID.value
                          else "domain_reference_insufficient")
                outputs.append(_reference_value(row.row_key, failure_state, None,
                                                reason, fold,
                                                tuple(ref.row_key for ref in reference_rows), state,
                                                row.evidence_ref))
                continue
            scored = apply_domain_reference(state, row.domain_category, config.compatibility_key,
                                            query_evidence_ref=row.evidence_ref)
            outputs.append(_reference_value(row.row_key, scored.state, scored.value,
                                            scored.reason_code, fold,
                                            tuple(ref.row_key for ref in reference_rows), state,
                                            row.evidence_ref))
    return tuple(outputs)


def crossfit_knn(rows, config: ReferenceFitConfig) -> tuple[ReferenceValue, ...]:
    """Internal cross-fit only; never admits or publishes Feature 003 data."""
    if config.method_config.method_id != "knn_distance":
        raise SignalProtocolError("reference_method_mismatch")
    return _crossfit(rows, config, "knn_distance")


def crossfit_domain(rows, config: ReferenceFitConfig) -> tuple[ReferenceValue, ...]:
    """Internal cross-fit only; category values stay in restricted reference state."""
    if config.method_config.method_id != "domain_familiarity":
        raise SignalProtocolError("reference_method_mismatch")
    return _crossfit(rows, config, "domain_familiarity")
