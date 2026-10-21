"""Independent synthetic ledgers for Feature 006 admission tests."""

from __future__ import annotations

from hashlib import sha256
import json


def canonical_digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False).encode()).hexdigest()


class PredictionAdmissionLedger:
    """Records content before submission; caller assertions do not create entries."""

    def __init__(self, delegate):
        self.delegate = delegate
        self.admitted = set()

    def admit(self, record):
        self.delegate.admit(record)
        self.admitted.add(canonical_digest(record.to_dict()))

    def verify_prediction(self, record):
        if canonical_digest(record.to_dict()) not in self.admitted:
            raise ValueError("no independent admission entry")
        return self.delegate.verify_prediction(record)


class DatasetAdmissionLedger:
    """Independent store of exact dataset and feature-set submissions."""

    def __init__(self):
        self.entries = set()

    def admit(self, dataset_fingerprint, feature_fingerprint, scope):
        self.entries.add((dataset_fingerprint, feature_fingerprint, tuple(scope)))

    def verify(self, dataset_fingerprint, feature_fingerprint, scope):
        key = (dataset_fingerprint, feature_fingerprint, tuple(scope))
        if key not in self.entries:
            raise ValueError("no independent dataset entry")
        return key


class SignalRunLedger:
    """Independent signal-run admission keyed by exact content and dataset scope."""

    def __init__(self):
        self.entries = set()

    def admit(self, signals):
        reference = signals.dataset_reference
        self.entries.add((canonical_digest(signals.to_dict()), reference.dataset_id,
                          reference.manifest_reference, reference.manifest_digest,
                          signals.manifest.run_version))

    def verify(self, signals):
        reference = signals.dataset_reference
        key = (canonical_digest(signals.to_dict()), reference.dataset_id,
               reference.manifest_reference, reference.manifest_digest,
               signals.manifest.run_version)
        if key not in self.entries:
            raise ValueError("no independent signal-run entry")
        return key


class ArtifactOriginLedger:
    """Independent artifact-origin ledger keyed by content and exact scope."""

    def __init__(self):
        self.entries = set()

    def admit(self, digest, scope, version):
        self.entries.add((digest, tuple(scope), version))

    def verify_artifact(self, digest, scope, version):
        key = (digest, tuple(scope), version)
        if key not in self.entries:
            raise ValueError("no independent artifact entry")
        return key
