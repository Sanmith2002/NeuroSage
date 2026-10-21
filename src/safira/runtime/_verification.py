"""Exact, atomic admission for the private synthetic runtime path."""

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from typing import Protocol

from safira.runtime._records import SyntheticRuntimeRequest
from safira.runtime._exceptions import RuntimeAdmissionRejected


@dataclass(frozen=True)
class SyntheticFixtureCheck:
    prediction_fingerprint: str
    source_key: tuple[str, str, str]
    state: str
    authority: str
    method: str
    evidence_ref: str


@dataclass(frozen=True)
class RuntimePredictorInventoryCheck:
    reference_digest: str
    source_key: tuple[str, str, str]
    predictor_fingerprints: tuple[str, ...]
    dataset_fingerprint: str
    inventory_digest: str
    state: str
    authority: str
    method: str
    evidence_ref: str


@dataclass(frozen=True)
class RuntimeSignalProtocolCheck:
    protocol_digest: str
    feature_set_digest: str
    reference_digest: str
    source_key: tuple[str, str, str]
    state: str
    authority: str
    method: str
    evidence_ref: str


class RuntimeVerifier(Protocol):
    """Injected host operations for the private synthetic-fixture boundary."""

    def verify_synthetic_fixture(self, prediction) -> SyntheticFixtureCheck: ...
    def verify_prediction(self, prediction): ...
    def verify_original_predictors(self, reference, source_key, predictor_fingerprints,
                                  dataset_fingerprint, inventory_digest) -> RuntimePredictorInventoryCheck: ...
    def verify_signal_protocol(self, protocol, feature_set_digest, reference,
                               source_key) -> RuntimeSignalProtocolCheck: ...
    def verify_artifact(self, payload_digest, scope_key, artifact_version): ...
    def verify_protocol(self, protocol): ...


@dataclass(frozen=True, repr=False)
class VerifiedRuntimeBundle:
    request: SyntheticRuntimeRequest
    scope_key: tuple[str, str, str]
    prediction_fingerprint: str
    training_predictors: tuple[object, ...]
    protocol_parameters: object
    registry: object
    verifier: object

    def __repr__(self):
        return f"VerifiedRuntimeBundle(scope={self.scope_key!r}, state='admitted')"


def _canonical_digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _require(condition, reason="trusted_evidence_rejected"):
    if not condition:
        raise RuntimeAdmissionRejected(reason)


def _call(verifier, name, *args):
    method = getattr(verifier, name, None)
    if not callable(method):
        raise RuntimeAdmissionRejected("trusted_evidence_missing")
    try:
        return method(*args)
    except (LookupError, PermissionError, ValueError, TypeError):
        raise RuntimeAdmissionRejected("trusted_evidence_rejected") from None


def _verify_origin(verifier, artifact):
    from safira.training.artifacts import ArtifactOriginCheck

    try:
        rebuilt = replace(artifact)
    except (TypeError, ValueError):
        raise RuntimeAdmissionRejected("artifact_invalid") from None
    _require(rebuilt == artifact, "artifact_invalid")
    check = _call(verifier, "verify_artifact", artifact.digest,
                  tuple(artifact.scope.source_key), artifact.artifact_version)
    _require(type(check) is ArtifactOriginCheck
             and check.payload_digest == artifact.digest
             and check.scope_key == tuple(artifact.scope.source_key)
             and check.artifact_version == artifact.artifact_version
             and all(type(getattr(check, field)) is str and getattr(check, field).strip()
                     for field in ("authority", "method", "evidence_ref")), "origin_rejected")


def _verify_prediction(verifier, prediction):
    from safira.signals.records import SignalInputCheck
    from safira.signals.validation import prediction_fingerprint

    fingerprint = prediction_fingerprint(prediction)
    check = _call(verifier, "verify_prediction", prediction)
    association = tuple(getattr(prediction.association, field)
                        for field in ("patient_ref", "assessment_ref", "occurrence_ref"))
    _require(type(check) is SignalInputCheck
             and (check.record_fingerprint, check.source_key, check.association,
                  check.provenance_mode, check.state)
             == (fingerprint, tuple(prediction.source_key), association,
                 prediction.provenance.mode, "verified")
             and all(type(getattr(check, field)) is str and getattr(check, field).strip()
                     for field in ("authority", "method", "evidence_ref", "input_scope")),
             "prediction_rejected")
    return fingerprint


def admit_runtime_request(registry, request, verifier):
    """Execute all trust and exact-scope checks before exposing a private token.

    Original labels are deliberately never read. The host receives only the
    original training prediction fingerprints for its independently maintained
    target-free inventory check. Python cannot authenticate a hostile process
    that controls its own injected verifier or introspects private modules.
    """
    from safira.policy.verification import PolicyProtocolCheck
    from safira.signals.validation import prediction_fingerprint

    if type(request) is not SyntheticRuntimeRequest or registry is None or verifier is None:
        raise RuntimeAdmissionRejected("input_invalid")
    scope = request.scope
    source = tuple(scope.source_key)
    _require(tuple(request.prediction.source_key) == source, "scope_incompatible")
    try:
        registration = registry.resolve_usable(source[0], source[1])
    except (LookupError, ValueError, TypeError):
        raise RuntimeAdmissionRejected("registry_incompatible") from None
    metadata = registration.metadata
    _require(metadata.model_id == source[0] and metadata.model_version == source[1]
             and any(label.label_id == source[2] for label in metadata.labels)
             and metadata.classifier_artifact["sha256"] == scope.classifier_artifact_sha256
             and metadata.adapter.adapter_id == scope.adapter_id
             and metadata.adapter.adapter_version == scope.adapter_version
             and metadata.adapter.implementation_fingerprint == scope.adapter_fingerprint
             and metadata.preprocessing_identity == scope.preprocessing_identity,
             "registry_incompatible")

    prediction_fp = _verify_prediction(verifier, request.prediction)
    from safira.runtime._verification import SyntheticFixtureCheck
    fixture_check = _call(verifier, "verify_synthetic_fixture", request.prediction)
    _require(type(fixture_check) is SyntheticFixtureCheck
             and fixture_check.prediction_fingerprint == prediction_fp
             and fixture_check.source_key == source
             and fixture_check.state == "verified_synthetic_fixture"
             and all(type(getattr(fixture_check, field)) is str
                     and getattr(fixture_check, field).strip()
                     for field in ("authority", "method", "evidence_ref")),
             "synthetic_fixture_rejected")

    request_ref = request.original_reference
    artifact_ref = request.estimator.dataset_reference
    _require(request.original_dataset.readiness.state == "ready"
             and request.original_dataset.manifest_reference == request_ref.manifest_reference
             and request.original_signal_set.dataset_reference == request_ref
             and request.original_signal_set.manifest.dataset_reference == request_ref,
             "original_reference_incompatible")
    _require(any(item.to_tuple() == source for item in request.original_signal_protocol.source_keys)
             and any(item.to_tuple() == source
                     for item in request.original_signal_set.manifest.source_keys),
             "scope_incompatible")
    _require(all(artifact_ref[key] == getattr(request_ref, key)
                 for key in ("dataset_id", "manifest_reference", "manifest_digest", "protocol_id",
                             "protocol_version", "builder_version")), "original_reference_incompatible")
    _require(request.calibrator.dataset_reference["manifest_digest"] == request_ref.manifest_digest
             and request.calibrator.dataset_reference["dataset_id"] == request_ref.dataset_id
             and request.policy.original_dataset_reference["manifest_digest"] == request_ref.manifest_digest
             and request.policy.original_dataset_reference["dataset_id"] == request_ref.dataset_id,
             "original_reference_incompatible")

    # Extract only prediction references from the training partition. Neither
    # validation/calibration examples nor any target/group fields are inspected.
    training_predictors = tuple(example.prediction
                                for example in request.original_dataset.development.train
                                if tuple(example.prediction.source_key) == source)
    _require(bool(training_predictors), "original_inventory_incomplete")
    predictor_fingerprints = tuple(sorted(prediction_fingerprint(record)
                                          for record in training_predictors))
    _require(len(predictor_fingerprints) == len(set(predictor_fingerprints)),
             "original_inventory_incomplete")
    for record in training_predictors:
        _verify_prediction(verifier, record)
    inventory = _call(
        verifier, "verify_original_predictors", request_ref, source, predictor_fingerprints,
        artifact_ref["dataset_fingerprint"], artifact_ref["admitted_inventory_digest"],
    )
    _require(type(inventory) is RuntimePredictorInventoryCheck
             and inventory.reference_digest == request_ref.manifest_digest
             and inventory.source_key == source
             and inventory.predictor_fingerprints == predictor_fingerprints
             and inventory.dataset_fingerprint == artifact_ref["dataset_fingerprint"]
             and inventory.inventory_digest == artifact_ref["admitted_inventory_digest"]
             and inventory.state == "verified_target_free_inventory"
             and all(type(getattr(inventory, field)) is str and getattr(inventory, field).strip()
                     for field in ("authority", "method", "evidence_ref")),
             "original_inventory_unverified")

    from safira.training.verification import feature_set_fingerprint
    signal_digest = feature_set_fingerprint(request.original_signal_set)
    signal_ref = request.estimator.signal_run_reference
    feature_methods = tuple(sorted((method.method_id, method.method_version,
                                    _canonical_digest(method.to_dict()["parameters"]))
                                   for method in request.original_signal_set.manifest.method_configs))
    _require(signal_digest == signal_ref["feature_set_fingerprint"]
             and tuple(sorted(state.state_id for state in
                              request.original_signal_set.manifest.fitted_state_references))
             == tuple(sorted(signal_ref["fitted_state_ids"]))
             and feature_methods == tuple(sorted(tuple(item) for item in signal_ref["method_ids"]))
             and tuple(signal_ref["scope_key"]) == source,
             "signal_reference_incompatible")
    protocol_digest = _canonical_digest(request.original_signal_protocol.to_dict())
    signal_check = _call(verifier, "verify_signal_protocol", request.original_signal_protocol,
                          signal_digest, request_ref, source)
    _require(type(signal_check) is RuntimeSignalProtocolCheck
             and signal_check.protocol_digest == protocol_digest
             and signal_check.feature_set_digest == signal_digest
             and signal_check.reference_digest == request_ref.manifest_digest
             and signal_check.source_key == source
             and signal_check.state == "verified"
             and all(type(getattr(signal_check, field)) is str and getattr(signal_check, field).strip()
                     for field in ("authority", "method", "evidence_ref")),
             "signal_protocol_unapproved")

    estimator = request.estimator
    calibrator = request.calibrator
    policy = request.policy
    _require(estimator.scope == scope.to_training_scope()
             and calibrator.scope == estimator.scope
             and calibrator.base_artifact_digest == estimator.digest
             and calibrator.base_artifact_version == estimator.artifact_version
             and calibrator.base_family == estimator.family
             and policy.scope == scope and policy.estimator_digest == estimator.digest
             and policy.calibrator_digest == calibrator.digest
             and policy.protocol_digest == request.policy_protocol.digest
             and policy.independent_evaluation_complete is False
             and policy.protected_test_accessed is False
             and policy.deployable is False and policy.clinical_validity_established is False,
             "artifact_incompatible")
    _verify_origin(verifier, estimator)
    _verify_origin(verifier, calibrator)
    _verify_origin(verifier, policy)
    approval = _call(verifier, "verify_protocol", request.policy_protocol)
    _require(type(approval) is PolicyProtocolCheck
             and approval.protocol_digest == policy.protocol_digest
             and approval.state == "verified" and approval.approved_before_outcomes is True
             and all(type(getattr(approval, field)) is str and getattr(approval, field).strip()
                     for field in ("authority", "method", "evidence_ref")),
             "policy_protocol_unapproved")

    return VerifiedRuntimeBundle(request, source, prediction_fp, training_predictors,
                                 request.original_signal_protocol.method_configs, registry, verifier)
