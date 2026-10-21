"""Internal, protocol-bound Feature 004 predictor encoding and train-only preprocessing.

This module does not admit source records. Callers must first pass the complete
Feature 002/003/004 trust boundary before using these helpers to publish any
cohort claim or fitted candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from types import MappingProxyType

from safira.signals.base import SignalDimension, SignalState
from safira.signals.records import SignalFeatureRecord, SignalResult
from safira.training.records import FeatureKind, FeaturePolicy, FeatureSpec, PreprocessingPolicy, TrainingScope


_NUMERIC_DIMENSIONS = {
    SignalDimension.DATA_SUFFICIENCY,
    SignalDimension.DISTRIBUTION_CONFORMITY,
    SignalDimension.PREDICTION_UNCERTAINTY,
    SignalDimension.MODALITY_AGREEMENT,
}


@dataclass(frozen=True)
class FeatureColumn:
    name: str
    method_id: str
    method_version: str
    meaning: str
    kind: str
    state: str = ""


@dataclass(frozen=True)
class FrozenFeatureSchema:
    scope: TrainingScope
    columns: tuple[FeatureColumn, ...]
    feature_specs: tuple[FeatureSpec, ...]
    omitted_dimensions: object

    def __post_init__(self):
        if type(self.scope) is not TrainingScope:
            raise ValueError("feature_schema")
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "feature_specs", tuple(self.feature_specs))
        object.__setattr__(self, "omitted_dimensions", MappingProxyType(dict(self.omitted_dimensions)))
        if any(reason not in {"no_numeric_v1_method", "unsupported_for_source",
                              "not_applicable_for_scope", "method_not_approved"}
               for reason in self.omitted_dimensions.values()):
            raise ValueError("feature_schema_omission")
        if not self.columns or any(type(column) is not FeatureColumn for column in self.columns):
            raise ValueError("feature_schema")
        expected = []
        for spec in self.feature_specs:
            if type(spec) is not FeatureSpec:
                raise ValueError("feature_schema")
            if spec.kind is FeatureKind.NUMERIC:
                expected.append(FeatureColumn(spec.method_id, spec.method_id, spec.method_version,
                                              spec.meaning, "numeric"))
            else:
                expected.extend((FeatureColumn(f"{spec.method_id}__seen", spec.method_id, spec.method_version,
                                               spec.meaning, "category", "seen"),
                                 FeatureColumn(f"{spec.method_id}__unseen", spec.method_id, spec.method_version,
                                               spec.meaning, "category", "unseen")))
            if spec.state_indicators:
                statuses = (SignalState.AVAILABLE.value,) + tuple(spec.allowed_nonvalue_states)
                expected.extend(FeatureColumn(f"{spec.method_id}__state__{status}", spec.method_id,
                                              spec.method_version, "evidence_state_indicator", "state", status)
                                for status in statuses)
        if tuple(expected) != self.columns:
            raise ValueError("feature_schema_columns")

    def to_dict(self):
        return {"scope": self.scope.to_dict(),
                "columns": [{"name": c.name, "method_id": c.method_id, "method_version": c.method_version,
                             "meaning": c.meaning, "kind": c.kind, "state": c.state} for c in self.columns],
                "feature_specs": [item.to_dict() for item in self.feature_specs],
                "omitted_dimensions": dict(self.omitted_dimensions)}


@dataclass(frozen=True)
class FrozenPreprocessingState:
    schema_digest: str
    medians: object
    means: object
    scales: object
    active_indices: tuple[int, ...]
    omissions: object
    policy: PreprocessingPolicy

    def __post_init__(self):
        if (type(self.schema_digest) is not str or len(self.schema_digest) != 64
                or any(ch not in "0123456789abcdef" for ch in self.schema_digest)):
            raise ValueError("preprocessing_state")
        for name in ("medians", "means", "scales", "omissions"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        object.__setattr__(self, "active_indices", tuple(self.active_indices))
        if (len(set(self.active_indices)) != len(self.active_indices)
                or any(type(index) is not int or index < 0 for index in self.active_indices)):
            raise ValueError("preprocessing_state")
        for values in (self.medians, self.means, self.scales):
            if any(type(value) not in (int, float) or not isfinite(value) for value in values.values()):
                raise ValueError("preprocessing_state")
        if any(value <= 0 for value in self.scales.values()):
            raise ValueError("preprocessing_state")
        if type(self.policy) is not PreprocessingPolicy:
            raise ValueError("preprocessing_state")

    def to_dict(self):
        return {"schema_digest": self.schema_digest, "medians": dict(self.medians),
                "means": dict(self.means), "scales": dict(self.scales),
                "active_indices": list(self.active_indices), "omissions": dict(self.omissions),
                "policy": self.policy.to_dict()}


def _schema_digest(schema: FrozenFeatureSchema) -> str:
    return sha256(json.dumps(schema.to_dict(), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode()).hexdigest()


def _row_parts(row):
    if type(row) is SignalFeatureRecord:
        return row.source_key.to_tuple(), row.predictors
    if not isinstance(row, (tuple, list)) or len(row) != 2:
        raise ValueError("feature_row")
    source, results = row
    if not isinstance(source, (tuple, list)) or len(source) != 3:
        raise ValueError("feature_row")
    return tuple(source), tuple(results)


def _index_results(scope, row, policy):
    source, results = _row_parts(row)
    if source != scope.source_key or any(type(result) is not SignalResult for result in results):
        raise ValueError("feature_scope")
    indexed = {}
    for result in results:
        if result.source_key.to_tuple() != scope.source_key:
            raise ValueError("feature_source")
        key = (result.method_id, result.method_version)
        if key in indexed:
            raise ValueError("feature_duplicate")
        # Explanation provenance is non-predictive by definition and is retained
        # in source records, but never projected into an estimator column.
        if result.dimension is SignalDimension.EXPLANATION_RELIABILITY:
            continue
        if result.dimension.value in policy.omitted_dimensions:
            if result.state is not SignalState.UNSUPPORTED:
                raise ValueError("feature_omission_state_mismatch")
            continue
        if not any((spec.method_id, spec.method_version) == key for spec in policy.features):
            raise ValueError("feature_unapproved")
        indexed[key] = result
    return indexed


def _validate_result(result, spec):
    if result.dimension is not spec.dimension or result.meaning != spec.meaning:
        raise ValueError("feature_semantics")
    if dict(result.method_parameters) != dict(spec.method_parameters):
        raise ValueError("feature_parameters")
    if result.state in (SignalState.INVALID, SignalState.NOT_READY):
        raise ValueError("feature_state")
    if result.state is not SignalState.AVAILABLE and result.state.value not in spec.allowed_nonvalue_states:
        raise ValueError("feature_state")
    if spec.kind is FeatureKind.NUMERIC and result.state is SignalState.AVAILABLE:
        if type(result.value) not in (int, float) or type(result.value) is bool or not isfinite(result.value):
            raise ValueError("feature_numeric")
    if spec.kind is FeatureKind.SEEN_UNSEEN and result.state is SignalState.AVAILABLE:
        if result.value not in ("seen", "unseen"):
            raise ValueError("feature_category")


def _validate_policy(policy):
    if type(policy) is not FeaturePolicy:
        raise ValueError("feature_policy")
    if not policy.features and not policy.omitted_dimensions:
        raise ValueError("feature_policy_empty")
    for spec in policy.features:
        if spec.kind is FeatureKind.NUMERIC and spec.dimension not in _NUMERIC_DIMENSIONS:
            raise ValueError("feature_predictor_kind")


def _build_feature_schema(scope: TrainingScope, policy: FeaturePolicy, training_rows) -> FrozenFeatureSchema:
    """Build an ordered schema from approved policy and training rows only."""
    if type(scope) is not TrainingScope:
        raise ValueError("feature_scope")
    _validate_policy(policy)
    rows = tuple(training_rows)
    if not rows:
        raise ValueError("feature_rows_empty")
    indexed_rows = tuple(_index_results(scope, row, policy) for row in rows)
    columns = []
    retained = []
    omissions = dict(policy.omitted_dimensions)
    for spec in policy.features:
        results = []
        for indexed in indexed_rows:
            result = indexed.get((spec.method_id, spec.method_version))
            if result is None:
                raise ValueError("feature_missing_method")
            _validate_result(result, spec)
            results.append(result)
        if spec.kind is FeatureKind.NUMERIC:
            observed = [r.value for r in results if r.state is SignalState.AVAILABLE]
            if not observed and spec.required:
                raise ValueError("feature_required_all_missing")
            columns.append(FeatureColumn(spec.method_id, spec.method_id, spec.method_version,
                                         spec.meaning, "numeric"))
        else:
            columns.extend((FeatureColumn(f"{spec.method_id}__seen", spec.method_id, spec.method_version,
                                          spec.meaning, "category", "seen"),
                            FeatureColumn(f"{spec.method_id}__unseen", spec.method_id, spec.method_version,
                                          spec.meaning, "category", "unseen")))
        if spec.state_indicators:
            statuses = (SignalState.AVAILABLE.value,) + tuple(spec.allowed_nonvalue_states)
            columns.extend(FeatureColumn(f"{spec.method_id}__state__{status}", spec.method_id,
                                         spec.method_version, "evidence_state_indicator", "state", status)
                           for status in statuses)
        retained.append(spec)
    if not columns:
        raise ValueError("feature_schema_empty")
    return FrozenFeatureSchema(scope, tuple(columns), tuple(retained), omissions)


def build_feature_schema(protocol, scope: TrainingScope, training_rows) -> FrozenFeatureSchema:
    """Resolve the feature allowlist from the exact immutable protocol scope."""
    from safira.training.records import TrainingProtocol
    if type(protocol) is not TrainingProtocol or type(scope) is not TrainingScope or scope not in protocol.scopes:
        raise ValueError("feature_protocol_scope")
    policy = protocol.feature_policies.get(scope.source_key)
    if type(policy) is not FeaturePolicy:
        raise ValueError("feature_policy_not_ready")
    return _build_feature_schema(scope, policy, training_rows)


def encode_rows(schema: FrozenFeatureSchema, rows):
    """Project source signals into raw fixed columns; non-values remain None."""
    if type(schema) is not FrozenFeatureSchema:
        raise ValueError("feature_schema")
    output, states = [], []
    for row in rows:
        indexed = _index_results(schema.scope, row, FeaturePolicy(schema.feature_specs,
                                                                  schema.omitted_dimensions))
        values, row_states = [], []
        for spec in schema.feature_specs:
            result = indexed.get((spec.method_id, spec.method_version))
            if result is None:
                raise ValueError("feature_missing_method")
            _validate_result(result, spec)
            row_states.append(result.state.value)
            if spec.kind is FeatureKind.NUMERIC:
                values.append(float(result.value) if result.state is SignalState.AVAILABLE else None)
            else:
                values.extend((float(result.value == "seen"), float(result.value == "unseen"))
                              if result.state is SignalState.AVAILABLE else (0.0, 0.0))
            if spec.state_indicators:
                statuses = (SignalState.AVAILABLE.value,) + tuple(spec.allowed_nonvalue_states)
                values.extend(float(result.state.value == status) for status in statuses)
        output.append(tuple(values))
        states.append(tuple(row_states))
    return tuple(output), tuple(states)


def fit_preprocessing(protocol, schema: FrozenFeatureSchema, training_rows) -> FrozenPreprocessingState:
    """Fit every learned transform on the exact admitted training rows only."""
    from safira.training.records import TrainingProtocol
    if (type(protocol) is not TrainingProtocol or type(schema) is not FrozenFeatureSchema
            or schema.scope not in protocol.scopes):
        raise ValueError("preprocessing_policy")
    policy = protocol.preprocessing_policies.get(schema.scope.source_key)
    if type(policy) is not PreprocessingPolicy:
        raise ValueError("preprocessing_approval_missing")
    raw, _ = encode_rows(schema, training_rows)
    if not raw:
        raise ValueError("feature_rows_empty")
    medians, means, scales, omissions = {}, {}, {}, {}
    active = list(range(len(schema.columns)))
    for index, column in enumerate(schema.columns):
        vals = [row[index] for row in raw if row[index] is not None]
        if column.kind != "numeric":
            continue
        imputation = policy.numeric_imputation.get(column.method_id)
        scaling = policy.numeric_scaling.get(column.method_id)
        if imputation not in ("median", "none") or scaling not in ("standard", "none"):
            raise ValueError("preprocessing_approval_missing")
        if not vals:
            if column.method_id not in policy.optional_all_missing:
                raise ValueError("preprocessing_all_missing_policy")
            action = policy.optional_all_missing[column.method_id]
            if action == "fail":
                raise ValueError("preprocessing_all_missing")
            associated = [i for i, item in enumerate(schema.columns) if item.method_id == column.method_id]
            active = [i for i in active if i not in associated]
            omissions[column.method_id] = "optional_all_missing_training"
            continue
        if any(value is None for row in raw for value in (row[index],)):
            if imputation != "median":
                raise ValueError("preprocessing_imputation_unapproved")
            medians[column.method_id] = float(sorted(vals)[len(vals) // 2]) if len(vals) % 2 else (
                float(sorted(vals)[len(vals) // 2 - 1] + sorted(vals)[len(vals) // 2]) / 2.0)
        filled = [medians.get(column.method_id, value) if value is None else value
                  for value in (row[index] for row in raw)]
        if scaling == "standard":
            mean = sum(filled) / len(filled)
            variance = sum((value - mean) ** 2 for value in filled) / len(filled)
            scale = variance ** 0.5
            if scale == 0:
                if policy.constant_features == "drop":
                    active.remove(index)
                    omissions[column.method_id] = "constant_training_feature_dropped"
                    continue
                scale = 1.0
            means[column.method_id] = mean
            scales[column.method_id] = scale
        else:
            means[column.method_id] = 0.0
            scales[column.method_id] = 1.0
    return FrozenPreprocessingState(_schema_digest(schema), medians, means, scales,
                                    tuple(active), omissions, policy)


def transform_rows(state: FrozenPreprocessingState, schema: FrozenFeatureSchema, rows):
    """Apply frozen training transforms; never fits or updates from these rows."""
    if type(state) is not FrozenPreprocessingState or type(schema) is not FrozenFeatureSchema:
        raise ValueError("preprocessing_state")
    if state.schema_digest != _schema_digest(schema):
        raise ValueError("preprocessing_schema_mismatch")
    raw, _ = encode_rows(schema, rows)
    transformed = []
    for row in raw:
        values = []
        for index in state.active_indices:
            column = schema.columns[index]
            value = row[index]
            if column.kind == "numeric":
                if value is None:
                    if column.method_id not in state.medians:
                        raise ValueError("preprocessing_missing_value")
                    value = state.medians[column.method_id]
                value = (value - state.means[column.method_id]) / state.scales[column.method_id]
            if type(value) not in (int, float) or not isfinite(value):
                raise ValueError("preprocessing_nonfinite")
            values.append(float(value))
        transformed.append(tuple(values))
    return tuple(transformed)
