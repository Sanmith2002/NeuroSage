"""Controlled synthetic fixtures for Feature 008 runtime tests.

The builders delegate frozen artifacts to the existing Feature 003–007 test
factories. No fixture marks an ordinary observation synthetic via a caller flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace


@dataclass
class RuntimeFixture:
    request: object
    registry: object
    verifier: object
    expected: dict
    calls: list


class SyntheticRuntimeVerifier:
    """Test-only host ledger with explicit synthetic and target-free checks."""

    def __init__(self, base, reference, source_key, predictor_fingerprints,
                 dataset_fingerprint, inventory_digest, signal_protocol,
                 feature_set_digest, policy_protocol):
        self.base = base
        self.reference = reference
        self.source_key = tuple(source_key)
        self.predictor_fingerprints = tuple(predictor_fingerprints)
        self.dataset_fingerprint = dataset_fingerprint
        self.inventory_digest = inventory_digest
        self.signal_protocol = signal_protocol
        self.feature_set_digest = feature_set_digest
        self.policy_protocol = policy_protocol
        self.synthetic = set()
        self.synthetic_calls = 0
        self.predictor_calls = 0
        self.artifact_calls = 0
        self.allow_synthetic = True
        self.tamper_predictors = False
        self.deny_artifact = None
        self.deny_policy_protocol = False

    @property
    def prediction_ledger(self):
        return self.base.prediction_ledger

    @property
    def origin(self):
        return self.base.origin

    @origin.setter
    def origin(self, value):
        self.base.origin = value

    def admit_synthetic(self, prediction):
        from safira.signals.validation import prediction_fingerprint
        self.synthetic.add(prediction_fingerprint(prediction))

    def verify_synthetic_fixture(self, prediction):
        from safira.runtime._verification import SyntheticFixtureCheck
        from safira.signals.validation import prediction_fingerprint
        self.synthetic_calls += 1
        fingerprint = prediction_fingerprint(prediction)
        if not self.allow_synthetic or fingerprint not in self.synthetic:
            return SyntheticFixtureCheck(fingerprint, tuple(prediction.source_key), "rejected",
                                         "test-ledger", "exact fixture lookup", "rejected")
        return SyntheticFixtureCheck(fingerprint, tuple(prediction.source_key),
                                     "verified_synthetic_fixture", "test-ledger",
                                     "exact fixture lookup", "synthetic-entry")

    def verify_original_predictors(self, reference, source_key, predictor_fingerprints,
                                   dataset_fp, inventory_digest):
        from safira.runtime._verification import RuntimePredictorInventoryCheck
        self.predictor_calls += 1
        values = tuple(predictor_fingerprints)
        if self.tamper_predictors:
            values = values + ("0" * 64,)
        valid = (reference == self.reference and tuple(source_key) == self.source_key
                 and tuple(predictor_fingerprints) == self.predictor_fingerprints
                 and dataset_fp == self.dataset_fingerprint
                 and inventory_digest == self.inventory_digest)
        return RuntimePredictorInventoryCheck(
            reference.manifest_digest, tuple(source_key), values, dataset_fp,
            inventory_digest, "verified_target_free_inventory" if valid else "rejected",
            "test-ledger", "target-free original predictor lookup", "predictor-entry",
        )

    def verify_signal_protocol(self, protocol, feature_set_digest, reference, source_key):
        from safira.runtime._verification import RuntimeSignalProtocolCheck
        import json
        from hashlib import sha256
        digest = sha256(json.dumps(protocol.to_dict(), sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False).encode()).hexdigest()
        valid = (protocol == self.signal_protocol and feature_set_digest == self.feature_set_digest
                 and reference == self.reference and tuple(source_key) == self.source_key)
        return RuntimeSignalProtocolCheck(digest, feature_set_digest, reference.manifest_digest,
            tuple(source_key), "verified" if valid else "rejected", "test-ledger",
            "exact protocol and manifest lookup", "signal-protocol-entry")

    def verify_prediction(self, record):
        return self.base.verify_prediction(record)

    def verify_dataset(self, dataset, reference):
        return self.base.verify_dataset(dataset, reference)

    def verify_protocol(self, protocol):
        from safira.policy.verification import PolicyProtocolCheck
        if self.deny_policy_protocol:
            return PolicyProtocolCheck(protocol.digest, "rejected", False,
                                       "test-ledger", "denied", "denied")
        return self.base.verify_protocol(protocol)

    def verify_artifact(self, payload_digest, scope_key, artifact_version):
        self.artifact_calls += 1
        if payload_digest == self.deny_artifact:
            raise ValueError("not admitted")
        return self.base.verify_artifact(payload_digest, scope_key, artifact_version)


def build_runtime_fixture(registered_collection, *, force_logistic=False):
    """Build one end-to-end, test-ledger-backed synthetic Feature 008 request."""
    from safira.collection import CollectionAssociation, LiveRequest, collect_live
    from safira.policy.service import PolicySelectionService
    from safira.signals import SignalExtractor
    from safira.signals.records import SignalSourceKey
    from policy_fixtures import make_end_to_end_case
    from safira.runtime._records import SyntheticRuntimeRequest

    service, verifier, protocol, policy_data, original, signal_protocol, estimators, calibrators = (
        make_end_to_end_case(registered_collection, force_logistic=force_logistic)
    )
    # Test-only operating-point candidates ensure the synthetic suite exercises
    # both sides of a valid frozen policy without changing runtime methodology.
    protocol = replace(protocol, candidate_cutoffs=(0.25, 0.75))
    verifier.admit_protocol(protocol)
    registry = service._registry
    scopes = {scope.source_key: scope for scope in protocol.scopes}
    scope = scopes[sorted(scopes)[0]]
    estimator = estimators[scope.source_key]
    calibrator = calibrators[scope.source_key]
    policy_service = PolicySelectionService(registry, protocol, verifier)
    policy_outcomes = policy_service.select(
        policy_dataset=policy_data,
        original_training_dataset=original,
        original_signal_protocol=signal_protocol,
        estimator_artifacts=estimators,
        calibrator_artifacts=calibrators,
    )
    policy = next(item.artifact for item in policy_outcomes if item.artifact is not None)
    verifier.origin.admit_artifact(policy)

    original_reference = signal_protocol
    from safira.signals.records import Feature003DatasetReference
    dataset_reference = Feature003DatasetReference(
        estimator.dataset_reference["dataset_id"],
        estimator.dataset_reference["protocol_id"],
        estimator.dataset_reference["protocol_version"],
        estimator.dataset_reference["manifest_reference"],
        estimator.dataset_reference["builder_version"],
        estimator.dataset_reference["manifest_digest"],
    )
    original_signals = SignalExtractor(
        registry, signal_protocol, verifier, dataset_verifier=verifier
    ).build_feature_set(original, dataset_reference)

    source = scope.source_key
    adapter = registry.resolve_usable(*source[:2]).adapter
    adapter.classifier.scores[source[2]] = 0.73
    prediction = collect_live(
        registry,
        CollectionAssociation("synthetic-query-patient", "synthetic-query-assessment",
                              "synthetic-query-occurrence"),
        [LiveRequest(*source)],
        {"synthetic-feature": [12.0]},
    ).records[0]
    verifier.prediction_ledger.admit(prediction)

    from safira.signals.validation import prediction_fingerprint
    from safira.training.verification import feature_set_fingerprint
    target_free_verifier = SyntheticRuntimeVerifier(
        verifier, dataset_reference, source,
        tuple(sorted(prediction_fingerprint(item.prediction)
                     for item in original.development.train
                     if tuple(item.prediction.source_key) == source)),
        estimator.dataset_reference["dataset_fingerprint"],
        estimator.dataset_reference["admitted_inventory_digest"],
        signal_protocol, feature_set_fingerprint(original_signals), protocol,
    )
    target_free_verifier.admit_synthetic(prediction)

    request = SyntheticRuntimeRequest(
        prediction=prediction,
        scope=scope,
        original_dataset=original,
        original_reference=dataset_reference,
        original_signal_protocol=signal_protocol,
        original_signal_set=original_signals,
        estimator=estimator,
        calibrator=calibrator,
        policy_protocol=protocol,
        policy=policy,
    )
    return RuntimeFixture(
        request=request,
        registry=registry,
        verifier=target_free_verifier,
        expected={"scope": source, "estimator": estimator, "calibrator": calibrator,
                  "policy": policy, "signal_protocol": signal_protocol,
                  "original_dataset": original},
        calls=[],
    )

