"""Trusted admission and exact Feature 003/004 alignment for Feature 005."""

from __future__ import annotations

from hashlib import sha256
import json
from dataclasses import dataclass, field
from typing import Protocol

from safira.dataset.records import CorrectnessExample, DatasetBuildResult
from safira.signals.exceptions import SignalInputError, SignalVerificationError
from safira.signals.records import (
    Feature003DatasetReference, SignalFeatureSet, SignalProtocol, SignalRowKey, SignalSourceKey,
)
from safira.signals.validation import (
    dataset_fingerprint, prediction_fingerprint, validate_registered_record,
    verify_dataset_admission,
)

from safira.training.exceptions import TrainingCompatibilityError, TrainingInputError, TrainingVerificationError
from safira.training.records import TrainingInputCheck, TrainingScope


class TrainingInputVerifier(Protocol):
    """Trusted-host integration that looks up independently maintained evidence."""

    def verify_inputs(self, dataset: DatasetBuildResult, signals: SignalFeatureSet) -> TrainingInputCheck: ...

    def verify_dataset(self, dataset: DatasetBuildResult, reference: Feature003DatasetReference): ...

    def verify_prediction(self, record): ...


def _digest(value) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except Exception:
        raise TrainingInputError("input_not_canonical") from None
    return sha256(encoded).hexdigest()


def feature_set_fingerprint(signals: SignalFeatureSet) -> str:
    try:
        return _digest(signals.to_dict())
    except Exception:
        raise TrainingInputError("feature_set_not_canonical") from None


def _methods(signals):
    return tuple(sorted((item.method_id, item.method_version,
                         json.dumps(item.to_dict().get("parameters", {}), sort_keys=True,
                                    separators=(",", ":"), ensure_ascii=False))
                        for item in signals.manifest.method_configs))


def _inventory(dataset, signals, reference):
    role_names = (("train", "training"), ("validation", "validation"), ("calibration", "calibration"))
    inventory = []
    for role, feature_role in role_names:
        examples = getattr(dataset.development, role)
        feature_rows = getattr(signals, feature_role)
        by_key = {}
        for feature in feature_rows:
            key = feature.row_key.value
            if key in by_key:
                raise TrainingVerificationError("feature_row_duplicate")
            by_key[key] = feature
        expected_keys = set()
        for example in examples:
            if type(example) is not CorrectnessExample:
                raise TrainingInputError("correctness_example_invalid")
            if example.partition_role != role:
                raise TrainingInputError("partition_role_mismatch")
            record = example.prediction
            fingerprint = prediction_fingerprint(record)
            expected_key = sha256(
                f"{reference.dataset_id}\0{reference.manifest_reference}\0{fingerprint}".encode("utf-8")
            ).hexdigest()
            if expected_key in expected_keys:
                raise TrainingVerificationError("dataset_row_duplicate")
            expected_keys.add(expected_key)
            feature = by_key.get(expected_key)
            if feature is None:
                raise TrainingVerificationError("feature_row_missing")
            source = tuple(record.source_key)
            if feature.source_key.to_tuple() != source:
                raise TrainingVerificationError("feature_source_mismatch")
            for predictor in feature.predictors:
                if predictor.source_key.to_tuple() != source:
                    raise TrainingVerificationError("predictor_source_mismatch")
            inventory.append((role, fingerprint, source, expected_key, feature.source_key.to_tuple()))
        if set(by_key) != expected_keys:
            raise TrainingVerificationError("feature_row_inventory_mismatch")
    return tuple(sorted(inventory, key=repr))


def _check_registry_compatibility(registry, signals, reference, scopes):
    scopes_by_source = {scope.source_key: scope for scope in scopes}
    source_keys = tuple(SignalSourceKey(*source) for source in sorted(scopes_by_source))
    if any(source.to_tuple() not in scopes_by_source for source in signals.manifest.source_keys):
        raise TrainingCompatibilityError("source_outside_training_protocol")
    configs = {config.method_id: config for config in signals.manifest.method_configs}
    if len(configs) != len(signals.manifest.method_configs):
        raise TrainingCompatibilityError("signal_method_duplicate")
    try:
        signal_protocol = SignalProtocol(
            reference.protocol_id, reference.protocol_version, source_keys, configs, {},
        )
    except Exception:
        raise TrainingCompatibilityError("signal_protocol_incompatible") from None
    for source, scope in scopes_by_source.items():
        try:
            metadata = registry.get_metadata(source[0], source[1])
        except Exception:
            raise TrainingCompatibilityError("registration_not_found") from None
        if not any(label.label_id == source[2] for label in metadata.labels):
            raise TrainingCompatibilityError("registered_prediction_incompatible")
        if (metadata.classifier_artifact.get("sha256") != scope.classifier_artifact_sha256
                or metadata.adapter.adapter_id != scope.adapter_id
                or metadata.adapter.adapter_version != scope.adapter_version
                or metadata.adapter.implementation_fingerprint != scope.adapter_fingerprint
                or metadata.preprocessing_identity != scope.preprocessing_identity):
            raise TrainingCompatibilityError("registered_scope_identity_mismatch")
    for role in ("train", "validation", "calibration"):
        for feature in getattr(signals, "training" if role == "train" else role):
            for predictor in feature.predictors:
                config = configs.get(predictor.method_id)
                if (config is None or config.method_version != predictor.method_version
                        or dict(config.parameters) != dict(predictor.method_parameters)):
                    raise TrainingCompatibilityError("signal_method_mismatch")
    # Feature 004 state references are exact-scope and dataset-bound, not transferable.
    for state in signals.manifest.fitted_state_references:
        if (state.source_key.to_tuple() not in scopes_by_source
                or state.dataset_id != reference.dataset_id
                or state.protocol_id != reference.protocol_id
                or state.protocol_version != reference.protocol_version
                or state.manifest_reference != reference.manifest_reference):
            raise TrainingCompatibilityError("fitted_reference_mismatch")
        try:
            registered = registry.get_metadata(state.source_key.model_id, state.source_key.model_version)
        except Exception:
            raise TrainingCompatibilityError("fitted_reference_registration_missing") from None
        if state.preprocessing_identity != registered.preprocessing_identity:
            raise TrainingCompatibilityError("fitted_reference_preprocessing_mismatch")
    return signal_protocol


def _verify_training_inputs(registry, dataset, signals, reference, verifier, *, scopes):
    """Run independent Feature 003/002 checks and compare all evidence to actual inputs.

    The injected verifier is a trusted-host boundary. A check object or digest is
    only comparison evidence: Feature 004's executed dataset and per-prediction
    checks are run independently before this function returns.
    """
    try:
        if registry is None or type(dataset) is not DatasetBuildResult or type(signals) is not SignalFeatureSet:
            raise TrainingInputError("training_input_type_invalid")
        if type(reference) is not Feature003DatasetReference:
            raise TrainingInputError("dataset_reference_invalid")
        if not reference.manifest_digest:
            raise TrainingVerificationError("manifest_digest_unverified")
        if (signals.dataset_reference != reference or signals.manifest.dataset_reference != reference
                or dataset.manifest_reference != reference.manifest_reference):
            raise TrainingVerificationError("dataset_feature_scope_mismatch")
        if dataset.readiness.state != "ready":
            raise TrainingVerificationError("dataset_not_ready")
        if not callable(getattr(verifier, "verify_inputs", None)):
            raise TrainingVerificationError("trusted_verifier_required")
        scope_values = tuple(scopes)
        if not scope_values or any(type(scope) is not TrainingScope for scope in scope_values):
            raise TrainingInputError("source_scope_invalid")
        actual_scopes = {scope.source_key for scope in scope_values}
        scopes_by_source = {scope.source_key: scope for scope in scope_values}
        if len(actual_scopes) != len(scope_values):
            raise TrainingInputError("source_scope_invalid")
        check = verifier.verify_inputs(dataset, signals)
        if type(check) is not TrainingInputCheck:
            raise TrainingVerificationError("input_check_invalid")
        actual_dataset_fingerprint = dataset_fingerprint(dataset)
        actual_feature_fingerprint = feature_set_fingerprint(signals)
        actual_inventory = _inventory(dataset, signals, reference)
        actual_methods = _methods(signals)
        actual_states = tuple(sorted(state.state_id for state in signals.manifest.fitted_state_references))
        expected = (
            actual_dataset_fingerprint, actual_feature_fingerprint,
            reference.dataset_id, reference.protocol_id, reference.protocol_version,
            reference.manifest_reference, reference.manifest_digest, reference.builder_version,
            signals.manifest.run_version, actual_methods, actual_states, actual_inventory,
        )
        supplied = (
            check.dataset_fingerprint, check.feature_set_fingerprint,
            check.dataset_id, check.protocol_id, check.protocol_version,
            check.manifest_reference, check.manifest_digest, check.builder_version,
            check.feature_run_version, check.feature_method_ids, check.fitted_state_ids,
            check.row_inventory,
        )
        if supplied != expected or not all((check.authority, check.method, check.evidence_ref)):
            raise TrainingVerificationError("input_evidence_mismatch")
        # Execute Feature 003 full-inventory and per-record Feature 002 admission checks.
        dataset_check = verify_dataset_admission(verifier, verifier, dataset, reference)
        if (dataset_check.manifest_digest != reference.manifest_digest
                or dataset_check.rows is None):
            raise TrainingVerificationError("dataset_manifest_mismatch")
        signal_protocol = _check_registry_compatibility(registry, signals, reference, scope_values)
        for role in ("train", "validation", "calibration"):
            for example in getattr(dataset.development, role):
                source = tuple(example.prediction.source_key)
                if source not in actual_scopes:
                    raise TrainingCompatibilityError("source_outside_training_protocol")
                if source not in scopes_by_source:
                    raise TrainingCompatibilityError("registered_scope_identity_mismatch")
                try:
                    validate_registered_record(registry, signal_protocol, example.prediction)
                except SignalInputError:
                    raise TrainingCompatibilityError("registered_prediction_incompatible") from None
        return _VerifiedTrainingInputs(check, dataset_check, actual_inventory)
    except (TrainingInputError, TrainingVerificationError, TrainingCompatibilityError):
        raise
    except SignalVerificationError:
        raise TrainingVerificationError("source_admission_rejected") from None
    except SignalInputError:
        raise TrainingInputError("source_record_invalid") from None
    except Exception:
        # Never propagate values, identifiers, exception text or raw records.
        raise TrainingVerificationError("input_verification_failed") from None


@dataclass(frozen=True, repr=False)
class _VerifiedTrainingInputs:
    """Internal-only capability returned after complete admission and alignment."""

    _input_check: TrainingInputCheck = field(repr=False)
    _dataset_check: object = field(repr=False)
    _row_inventory: tuple[tuple[object, ...], ...] = field(repr=False)
