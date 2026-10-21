"""Feature 006 admission checks; host evidence is always independently executed."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from safira.collection.records import PredictionRecord
from safira.dataset.records import DatasetBuildResult
from safira.signals.records import SignalFeatureSet, SignalInputCheck, SignalProtocol
from safira.signals.validation import (
    verify_record_admission, validate_registered_record, verify_dataset_admission,
)
from safira.signals.exceptions import SignalInputError, SignalVerificationError
from safira.dataset.records import CorrectnessExample
from safira.training.records import SafetyEstimatorArtifact, TrainingScope

from safira.calibration.exceptions import (
    CalibrationCompatibilityError, CalibrationVerificationError,
)


@runtime_checkable
class CalibrationInputVerifier(Protocol):
    """Trusted-host evidence resolver. Implementations are injected explicitly."""

    def verify_prediction(self, record: PredictionRecord) -> SignalInputCheck: ...

    def verify_dataset(self, dataset: DatasetBuildResult, reference): ...

    def verify_artifact(self, payload_digest: str, scope_key: tuple[str, str, str],
                        artifact_version: str): ...


def verify_prediction_admission(registry, protocol: SignalProtocol, verifier, record: PredictionRecord):
    """Execute Feature 002 admission and Feature 001 semantic/identity checks.

    No check object, digest, status string, or Boolean supplied instead of a
    verifier is accepted. Errors contain controlled reason codes only.
    """
    if type(record) is not PredictionRecord or type(protocol) is not SignalProtocol:
        raise CalibrationVerificationError("input_invalid")
    try:
        check = verify_record_admission(verifier, record)
    except Exception:
        raise CalibrationVerificationError("verification_rejected") from None
    try:
        validate_registered_record(registry, protocol, record)
    except Exception:
        raise CalibrationCompatibilityError("compatibility_rejected") from None
    return check


def verify_dataset_inputs(registry, protocol: SignalProtocol, verifier,
                          dataset: DatasetBuildResult, reference):
    """Verify the exact ordinary Feature 003 inventory and each embedded prediction."""
    if type(protocol) is not SignalProtocol or type(dataset) is not DatasetBuildResult:
        raise CalibrationVerificationError("input_invalid")
    try:
        check = verify_dataset_admission(verifier, verifier, dataset, reference)
    except Exception:
        raise CalibrationVerificationError("verification_rejected") from None
    authorized = {key.to_tuple() for key in protocol.source_keys}
    try:
        for role in ("train", "validation", "calibration"):
            for example in getattr(dataset.development, role):
                if type(example) is not CorrectnessExample or example.partition_role != role:
                    raise ValueError
                if example.prediction.source_key not in authorized:
                    raise ValueError
                validate_registered_record(registry, protocol, example.prediction)
        return check
    except Exception:
        raise CalibrationCompatibilityError("compatibility_rejected") from None


def verify_signal_alignment(dataset: DatasetBuildResult, signals: SignalFeatureSet, reference,
                            registry=None, scopes=()):
    """Return calibration rows only after exact one-to-one source/role alignment."""
    from hashlib import sha256
    from safira.signals.records import Feature003DatasetReference, SignalFeatureRecord
    from safira.signals.validation import prediction_fingerprint

    if (type(dataset) is not DatasetBuildResult or type(signals) is not SignalFeatureSet
            or type(reference) is not Feature003DatasetReference
            or signals.dataset_reference != reference or signals.manifest.dataset_reference != reference
            or dataset.manifest_reference != reference.manifest_reference):
        raise CalibrationCompatibilityError("compatibility_rejected")
    configs = {item.method_id: item for item in signals.manifest.method_configs}
    if len(configs) != len(signals.manifest.method_configs):
        raise CalibrationCompatibilityError("compatibility_rejected")
    scope_map = {scope.source_key: scope for scope in scopes}
    manifest_sources = {item.to_tuple() for item in signals.manifest.source_keys}
    if scope_map and manifest_sources != set(scope_map):
        raise CalibrationCompatibilityError("compatibility_rejected")
    for state in signals.manifest.fitted_state_references:
        source = state.source_key.to_tuple()
        if (source not in manifest_sources or state.dataset_id != reference.dataset_id
                or state.protocol_id != reference.protocol_id
                or state.protocol_version != reference.protocol_version
                or state.manifest_reference != reference.manifest_reference
                or state.method_id not in configs
                or state.method_version != configs[state.method_id].method_version):
            raise CalibrationCompatibilityError("compatibility_rejected")
        if registry is not None:
            try:
                metadata = registry.get_metadata(source[0], source[1])
            except Exception:
                raise CalibrationCompatibilityError("compatibility_rejected") from None
            expected_preprocessing = (scope_map[source].preprocessing_identity if source in scope_map
                                      else metadata.preprocessing_identity)
            if (state.preprocessing_identity != expected_preprocessing
                    or metadata.preprocessing_identity != expected_preprocessing):
                raise CalibrationCompatibilityError("compatibility_rejected")
    result = {}
    try:
        for role, feature_role in (("train", "training"), ("validation", "validation"),
                                   ("calibration", "calibration")):
            expected = {}
            for example in getattr(dataset.development, role):
                if type(example) is not CorrectnessExample or example.partition_role != role:
                    raise ValueError
                fingerprint = prediction_fingerprint(example.prediction)
                key = sha256(f"{reference.dataset_id}\0{reference.manifest_reference}\0{fingerprint}".encode()).hexdigest()
                if key in expected:
                    raise ValueError
                expected[key] = tuple(example.prediction.source_key)
            actual = {}
            for feature in getattr(signals, feature_role):
                if type(feature) is not SignalFeatureRecord or feature.row_key.value in actual:
                    raise ValueError
                actual[feature.row_key.value] = feature
            if set(actual) != set(expected):
                raise ValueError
            for key, source_key in expected.items():
                feature = actual[key]
                if feature.source_key.to_tuple() != source_key:
                    raise ValueError
                for predictor in feature.predictors:
                    config = configs.get(predictor.method_id)
                    if (predictor.source_key != feature.source_key or config is None
                            or config.method_version != predictor.method_version
                            or dict(config.parameters) != dict(predictor.method_parameters)):
                        raise ValueError
            result[role] = tuple(actual[key] for key in sorted(actual))
        return result["calibration"]
    except Exception:
        raise CalibrationCompatibilityError("compatibility_rejected") from None


def verify_estimator_artifact(registry, artifact: SafetyEstimatorArtifact,
                              scope: TrainingScope, origin_verifier):
    """Check exact Feature 001 compatibility and independently ledgered origin."""
    from safira.training.artifacts import ArtifactCompatibility, validate_artifact, _canonical_digest

    if type(artifact) is not SafetyEstimatorArtifact or type(scope) is not TrainingScope:
        raise CalibrationCompatibilityError("compatibility_rejected")
    if artifact.scope != scope:
        raise CalibrationCompatibilityError("compatibility_rejected")
    try:
        if dict(artifact.feature_schema["scope"]) != scope.to_dict():
            raise ValueError
        metadata = registry.get_metadata(scope.model_id, scope.model_version)
        if (metadata.classifier_artifact["sha256"] != scope.classifier_artifact_sha256
                or metadata.adapter.adapter_id != scope.adapter_id
                or metadata.adapter.adapter_version != scope.adapter_version
                or metadata.adapter.implementation_fingerprint != scope.adapter_fingerprint
                or metadata.preprocessing_identity != scope.preprocessing_identity
                or not any(label.label_id == scope.label_id for label in metadata.labels)):
            raise ValueError
        expected = ArtifactCompatibility(
            scope.source_key, artifact.artifact_version, scope.classifier_artifact_sha256,
            scope.adapter_id, scope.adapter_version, scope.adapter_fingerprint,
            scope.preprocessing_identity, dict(artifact.training_protocol),
            dict(artifact.dataset_reference), dict(artifact.signal_run_reference), artifact.digest,
            _canonical_digest({"value": artifact.to_dict()["feature_schema"]}),
            _canonical_digest({"value": artifact.to_dict()["preprocessing"]}),
        )
        return validate_artifact(artifact.to_dict(), expected, origin_verifier)
    except Exception:
        raise CalibrationVerificationError("verification_rejected") from None


@dataclass(frozen=True)
class _ReadinessResult:
    """Internal pre-fit classification; deliberately carries no artifact or support IDs."""
    status: object | None
    reason_code: str


def _evaluate_scope_readiness(dataset: DatasetBuildResult, signals: SignalFeatureSet,
                              artifact: SafetyEstimatorArtifact, scope: TrainingScope,
                              protocol) -> _ReadinessResult:
    """Classify exact-scope readiness from already admitted/aligned Batch A inputs.

    This private helper is not a trust gate and must not be called to publish a
    trusted result before `verify_bundle` executes the complete shared gate.
    It inspects frozen Feature 005 policy metadata only; no transforms are run.
    """
    from hashlib import sha256
    from safira.calibration.records import CalibrationProtocol, CalibrationStatus
    from safira.signals.base import SignalState

    def result(status, reason):
        return _ReadinessResult(status, reason)

    if (type(protocol) is not CalibrationProtocol or type(dataset) is not DatasetBuildResult
            or type(signals) is not SignalFeatureSet or type(artifact) is not SafetyEstimatorArtifact
            or type(scope) is not TrainingScope):
        return result(CalibrationStatus.INVALID_INPUT, "input_invalid")
    if not protocol.ready:
        return result(CalibrationStatus.NOT_READY, "approval_missing")
    if (scope not in protocol.scopes or artifact.scope != scope
            or signals.dataset_reference.manifest_reference != dataset.manifest_reference):
        return result(CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    method_version = protocol.configuration.get("method_version")
    if method_version is None:
        return result(CalibrationStatus.NOT_READY, "approval_missing")
    if method_version != "logistic_recalibration_v1":
        return result(CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    scope_key = "\0".join(scope.source_key)
    selections = protocol.configuration.get("selected_artifacts_by_scope", {})
    selection = selections.get(scope_key) if hasattr(selections, "get") else None
    if not hasattr(selection, "get") or not {"artifact_version", "family"} <= set(selection):
        return result(CalibrationStatus.NOT_READY, "approval_missing")
    if (selection["artifact_version"] != artifact.artifact_version
            or selection["family"] != artifact.family):
        return result(CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    support = protocol.configuration.get("support_by_scope", {}).get(scope_key)
    if not isinstance(support, dict) and not hasattr(support, "get"):
        return result(CalibrationStatus.NOT_READY, "approval_missing")
    minimum_groups = support.get("minimum_patient_groups")
    class_minimums = support.get("correctness_class_minimums", {})
    if (type(minimum_groups) is not int or minimum_groups < 1
            or not isinstance(class_minimums, dict) and not hasattr(class_minimums, "items")):
        return result(CalibrationStatus.NOT_READY, "approval_missing")
    examples = [example for example in dataset.development.calibration
                if tuple(example.prediction.source_key) == scope.source_key]
    if any(type(example) is not CorrectnessExample or example.partition_role != "calibration"
           or example.correctness_target not in (0, 1)
           or not example.patient_group_ref for example in examples):
        return result(CalibrationStatus.INVALID_INPUT, "input_invalid")
    group_targets = {}
    for example in examples:
        group_targets.setdefault(example.patient_group_ref, set()).add(example.correctness_target)
    class_support = {0: 0, 1: 0}
    for targets in group_targets.values():
        if len(targets) == 1:
            class_support[next(iter(targets))] += 1
    invalid_criteria = any(type(target) is not str or target not in ("0", "1")
                           or type(minimum) is not int or minimum < 0
                           for target, minimum in class_minimums.items())
    if (invalid_criteria or len(group_targets) < minimum_groups
            or class_support[0] < 1 or class_support[1] < 1 or any(
        class_support[int(target)] < minimum for target, minimum in class_minimums.items()
    )):
        return result(CalibrationStatus.INSUFFICIENT_EVIDENCE, "support_insufficient")

    expected_rows = {}
    for example in examples:
        fingerprint = _prediction_fingerprint(example.prediction)
        key = sha256(f"{signals.dataset_reference.dataset_id}\0{signals.dataset_reference.manifest_reference}\0{fingerprint}".encode()).hexdigest()
        expected_rows[key] = example
    row_by_key = {row.row_key.value: row for row in signals.calibration
                  if row.source_key.to_tuple() == scope.source_key}
    specs = {item["method_id"]: item for item in artifact.feature_schema["feature_specs"]}
    prep_medians = artifact.preprocessing.get("medians", {})
    if set(row_by_key) != set(expected_rows):
        return result(CalibrationStatus.INCOMPATIBLE_INPUT, "scope_incompatible")
    for row_key, example in expected_rows.items():
        feature = row_by_key[row_key]
        indexed = {(item.method_id, item.method_version): item for item in feature.predictors}
        for method_id, spec in specs.items():
            if not spec.get("required", False):
                continue
            match = indexed.get((method_id, spec["method_version"]))
            if match is None:
                return result(CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE,
                              "required_evidence_unavailable")
            if match.state is SignalState.INVALID:
                return result(CalibrationStatus.INVALID_INPUT, "input_invalid")
            if match.state is SignalState.NOT_READY:
                return result(CalibrationStatus.NOT_READY, "approval_missing")
            if match.state is not SignalState.AVAILABLE:
                state_allowed = (match.state.value in tuple(spec.get("allowed_nonvalue_states", ()))
                                 and spec.get("state_indicators", False))
                imputation_allowed = (spec.get("kind") == "numeric"
                                      and method_id in prep_medians)
                if not state_allowed and not imputation_allowed:
                    return result(CalibrationStatus.UNAVAILABLE_REQUIRED_EVIDENCE,
                                  "required_evidence_unavailable")
    # None represents an internally eligible scope. Batch A does not introduce
    # a new public successful-calibration status.
    return result(None, "admission_complete")


@dataclass(frozen=True, repr=False)
class _VerifiedCalibrationInputs:
    """Restricted internal capability created only after the complete shared gate."""
    _dataset: DatasetBuildResult
    _signals: SignalFeatureSet
    _artifacts: object
    _protocol: object
    _readiness: object
    _evidence_refs: tuple[str, ...]

    @property
    def readiness(self):
        return self._readiness


def _verify_bundle(registry, dataset: DatasetBuildResult, signals: SignalFeatureSet,
                   artifacts, protocol, verifier) -> _VerifiedCalibrationInputs:
    """Atomically execute Feature 001–005 checks before exposing readiness internally."""
    from safira.calibration.records import CalibrationProtocol
    from safira.signals.records import SignalProtocol

    if (registry is None or type(dataset) is not DatasetBuildResult
            or type(signals) is not SignalFeatureSet or type(protocol) is not CalibrationProtocol
            or not isinstance(artifacts, Mapping)):
        raise CalibrationVerificationError("input_invalid")
    scopes = tuple(protocol.scopes)
    scope_map = {scope.source_key: scope for scope in scopes}
    if len(scope_map) != len(scopes) or set(artifacts) != set(scope_map):
        raise CalibrationVerificationError("inventory_mismatch")
    from safira.signals.records import SignalSourceKey
    if set(signals.manifest.source_keys) != {SignalSourceKey(*key) for key in scope_map}:
        raise CalibrationVerificationError("inventory_mismatch")
    method_configs = {item.method_id: item for item in signals.manifest.method_configs}
    if len(method_configs) != len(signals.manifest.method_configs):
        raise CalibrationVerificationError("inventory_mismatch")
    signal_protocol = SignalProtocol(
        protocol.protocol_id, protocol.version,
        tuple(SignalSourceKey(*key) for key in sorted(scope_map)), method_configs, {},
    )
    dataset_check = verify_dataset_inputs(registry, signal_protocol, verifier, dataset,
                                          signals.dataset_reference)
    aligned = verify_signal_alignment(dataset, signals, signals.dataset_reference, registry, scopes)
    if len(aligned) != len(dataset.development.calibration):
        raise CalibrationVerificationError("inventory_mismatch")
    # A host-ledgered Feature 005 artifact must also name this exact admitted
    # Feature 003/004 input, not merely an artifact of the same model scope.
    from hashlib import sha256
    import json
    from safira.signals.validation import dataset_fingerprint
    from safira.training.verification import feature_set_fingerprint, _inventory, _methods
    expected_dataset_fingerprint = dataset_fingerprint(dataset)
    expected_feature_fingerprint = feature_set_fingerprint(signals)
    method_ids = tuple(sorted((item[0], item[1],
                               sha256(item[2].encode("utf-8")).hexdigest())
                              for item in _methods(signals)))
    state_ids = tuple(sorted(state.state_id for state in signals.manifest.fitted_state_references))
    expected_inventory_digest = sha256(json.dumps(
        _inventory(dataset, signals, signals.dataset_reference), sort_keys=True,
        separators=(",", ":"), default=list).encode()).hexdigest()
    for key, artifact in artifacts.items():
        reference = artifact.dataset_reference
        run = artifact.signal_run_reference
        expected_reference = signals.dataset_reference
        if (reference["dataset_id"] != expected_reference.dataset_id
                or reference["manifest_reference"] != expected_reference.manifest_reference
                or reference["manifest_digest"] != expected_reference.manifest_digest
                or reference["protocol_id"] != expected_reference.protocol_id
                or reference["protocol_version"] != expected_reference.protocol_version
                or reference["builder_version"] != expected_reference.builder_version
                or reference["dataset_fingerprint"] != expected_dataset_fingerprint
                or reference["admitted_inventory_digest"] != expected_inventory_digest
                or run["run_version"] != signals.manifest.run_version
                or run["feature_set_fingerprint"] != expected_feature_fingerprint
                or tuple(tuple(item) for item in run["method_ids"]) != method_ids
                or tuple(run["fitted_state_ids"]) != state_ids
                or tuple(run["scope_key"]) != key):
            raise CalibrationCompatibilityError("compatibility_rejected")
        verify_estimator_artifact(registry, artifact, scope_map[key], verifier)
    readiness = {
        scope.source_key: _evaluate_scope_readiness(dataset, signals, artifacts[scope.source_key],
                                                    scope, protocol)
        for scope in scopes
    }
    refs = tuple(sorted({dataset_check.evidence_ref, *(
        getattr(artifacts[key], "digest", "") for key in artifacts
    )}))
    return _VerifiedCalibrationInputs(dataset, signals, MappingProxyType(dict(artifacts)),
                                      protocol, MappingProxyType(readiness), refs)


def _prediction_fingerprint(record: PredictionRecord) -> str:
    from safira.signals.validation import prediction_fingerprint
    return prediction_fingerprint(record)
