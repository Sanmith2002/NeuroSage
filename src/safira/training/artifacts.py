"""Allowlisted artifact validation and controlled, non-pickle loading."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from types import MappingProxyType

from safira.training.exceptions import TrainingArtifactError
from safira.training.records import SafetyEstimatorArtifact


def _canonical_digest(payload):
    def plain(value):
        if isinstance(value, Mapping):
            return {key: plain(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [plain(item) for item in value]
        return value
    body = plain({key: value for key, value in payload.items() if key != "digest"})
    try:
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                             allow_nan=False).encode("utf-8")
    except Exception:
        raise TrainingArtifactError("artifact_payload_invalid") from None
    return sha256(encoded).hexdigest()


def _immutable(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _immutable(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_immutable(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_immutable(item) for item in value)
    return value


@dataclass(frozen=True)
class ArtifactCompatibility:
    scope_key: tuple[str, str, str]
    artifact_version: str
    classifier_artifact_sha256: str
    adapter_id: str
    adapter_version: str
    adapter_fingerprint: str
    preprocessing_identity: object
    training_protocol: Mapping[str, object]
    dataset_reference: Mapping[str, object]
    signal_run_reference: Mapping[str, object]
    expected_digest: str = ""
    feature_schema_digest: str = ""
    preprocessing_digest: str = ""

    def __post_init__(self):
        object.__setattr__(self, "scope_key", tuple(self.scope_key))
        if len(self.scope_key) != 3 or any(type(x) is not str or not x for x in self.scope_key):
            raise ValueError("artifact_compatibility_scope")
        object.__setattr__(self, "preprocessing_identity", _immutable(self.preprocessing_identity))
        object.__setattr__(self, "training_protocol", _immutable(self.training_protocol))
        object.__setattr__(self, "dataset_reference", _immutable(self.dataset_reference))
        object.__setattr__(self, "signal_run_reference", _immutable(self.signal_run_reference))


@dataclass(frozen=True)
class ArtifactOriginCheck:
    payload_digest: str
    scope_key: tuple[str, str, str]
    artifact_version: str
    authority: str
    method: str
    evidence_ref: str

    def __post_init__(self):
        object.__setattr__(self, "scope_key", tuple(self.scope_key))
        if (len(self.scope_key) != 3 or any(type(item) is not str or not item for item in self.scope_key)
                or any(type(getattr(self, name)) is not str or not getattr(self, name).strip()
                       for name in ("payload_digest", "artifact_version", "authority", "method", "evidence_ref"))):
            raise ValueError("artifact_origin_check")


def _validate_values(artifact):
    schema = artifact.feature_schema
    preprocessing = artifact.preprocessing
    estimator = artifact.estimator_state
    if not isinstance(schema, Mapping) or not isinstance(schema.get("columns"), (tuple, list)):
        raise TrainingArtifactError("artifact_schema_invalid")
    columns = schema["columns"]
    if not columns or any(not isinstance(column, Mapping) or not column.get("name") for column in columns):
        raise TrainingArtifactError("artifact_schema_invalid")
    if not isinstance(preprocessing, Mapping) or not isinstance(preprocessing.get("active_indices"), (tuple, list)):
        raise TrainingArtifactError("artifact_preprocessing_invalid")
    width = len(preprocessing["active_indices"])
    if width < 1 or any(type(index) is not int or index < 0 or index >= len(columns)
                         for index in preprocessing["active_indices"]):
        raise TrainingArtifactError("artifact_preprocessing_invalid")
    if artifact.family == "prevalence_baseline":
        probability = estimator.get("probability")
        if type(probability) not in (int, float) or type(probability) is bool or not math.isfinite(probability) or not 0 <= probability <= 1:
            raise TrainingArtifactError("artifact_estimator_invalid")
    else:
        coefficients = estimator.get("coefficients")
        intercept = estimator.get("intercept")
        classes = estimator.get("classes")
        if (not isinstance(coefficients, (tuple, list)) or len(coefficients) != width
                or any(type(value) not in (int, float) or type(value) is bool or not math.isfinite(value)
                       for value in coefficients)
                or type(intercept) not in (int, float) or type(intercept) is bool or not math.isfinite(intercept)
                or tuple(classes or ()) != (0, 1)):
            raise TrainingArtifactError("artifact_estimator_invalid")


def validate_artifact(payload, expected_compatibility: ArtifactCompatibility, origin_verifier):
    """Validate allowlisted JSON data and independently check its exact origin binding."""
    try:
        if not isinstance(payload, Mapping) or type(expected_compatibility) is not ArtifactCompatibility:
            raise TrainingArtifactError("artifact_payload_invalid")
        artifact = SafetyEstimatorArtifact.from_dict(payload)
        if _canonical_digest(payload) != artifact.digest:
            raise TrainingArtifactError("artifact_digest_invalid")
        _validate_values(artifact)
        scope = artifact.scope
        expected = expected_compatibility
        if (scope.source_key != expected.scope_key or artifact.artifact_version != expected.artifact_version
                or scope.classifier_artifact_sha256 != expected.classifier_artifact_sha256
                or scope.adapter_id != expected.adapter_id or scope.adapter_version != expected.adapter_version
                or scope.adapter_fingerprint != expected.adapter_fingerprint
                or scope.preprocessing_identity != expected.preprocessing_identity
                or dict(artifact.training_protocol) != dict(expected.training_protocol)
                or dict(artifact.dataset_reference) != dict(expected.dataset_reference)
                or dict(artifact.signal_run_reference) != dict(expected.signal_run_reference)
                or _canonical_digest({"value": dict(artifact.feature_schema)}) != expected.feature_schema_digest
                or _canonical_digest({"value": dict(artifact.preprocessing)}) != expected.preprocessing_digest
                or (expected.expected_digest and expected.expected_digest != artifact.digest)):
            raise TrainingArtifactError("artifact_incompatible")
        if not callable(getattr(origin_verifier, "verify_artifact", None)):
            raise TrainingArtifactError("artifact_origin_not_ready")
        check = origin_verifier.verify_artifact(artifact.digest, scope.source_key, artifact.artifact_version)
        if (type(check) is not ArtifactOriginCheck or check.payload_digest != artifact.digest
                or check.scope_key != scope.source_key or check.artifact_version != artifact.artifact_version
                or not all((check.authority, check.method, check.evidence_ref))):
            raise TrainingArtifactError("artifact_origin_rejected")
        return artifact
    except TrainingArtifactError:
        raise
    except Exception:
        raise TrainingArtifactError("artifact_payload_invalid") from None


def _reproduce_probability_for_test(artifact: SafetyEstimatorArtifact, transformed_row):
    """Test-only numerical reproduction; deliberately not exported as inference API."""
    if type(artifact) is not SafetyEstimatorArtifact or artifact.family != "l2_logistic":
        raise TrainingArtifactError("artifact_reproduction_unavailable")
    coefficients = tuple(artifact.estimator_state["coefficients"])
    if len(coefficients) != len(transformed_row):
        raise TrainingArtifactError("artifact_reproduction_shape_invalid")
    score = float(artifact.estimator_state["intercept"]) + sum(
        float(coef) * float(value) for coef, value in zip(coefficients, transformed_row))
    if not math.isfinite(score):
        raise TrainingArtifactError("artifact_reproduction_invalid")
    if score >= 0:
        return 1.0 / (1.0 + math.exp(-score))
    exp_score = math.exp(score)
    return exp_score / (1.0 + exp_score)
