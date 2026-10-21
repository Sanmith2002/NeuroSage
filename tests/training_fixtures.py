"""Synthetic Feature 005 inputs and independently controlled fixture ledger.

No patient data are used. The opaque group and association values are generated
only for unit tests and are never emitted in ordinary training outcomes.
"""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json

from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.dataset import CorrectnessExample, DatasetBuildResult, DatasetReadiness, PartitionedDataset
from safira.signals import (
    Feature003DatasetReference, FittedStateReference, SignalFeatureRecord, SignalFeatureSet,
    SignalMethodConfig, SignalResult, SignalRowKey, SignalRunManifest, SignalSourceKey,
    SignalDimension, SignalState,
)
from safira.signals.validation import dataset_fingerprint, prediction_fingerprint

from signals_fixtures import SyntheticSignalVerifier


def training_scope(registry, model_id, model_version, label_id):
    from safira.training.records import TrainingScope

    metadata = registry.get_metadata(model_id, model_version)
    return TrainingScope(model_id, model_version, label_id,
                         metadata.classifier_artifact["sha256"],
                         metadata.adapter.adapter_id, metadata.adapter.adapter_version,
                         metadata.adapter.implementation_fingerprint, metadata.preprocessing_identity)


def build_inputs(registry, register, *, model_id="training-model", model_version="v1",
                 labels=("label-a",), partitions=None):
    """Register a synthetic source and create aligned Feature 003/004 partitions."""
    definition, _ = register(model_id=model_id, version=model_version, labels=labels,
                             scores=tuple(0.7 for _ in labels))
    source_keys = tuple(SignalSourceKey(model_id, model_version, label) for label in labels)
    if partitions is None:
        partitions = {"train": (("g1", 1), ("g2", 0)),
                      "validation": (("g3", 1),), "calibration": (("g4", 0),)}

    examples_by_role = {role: [] for role in ("train", "validation", "calibration")}
    features_by_role = {role: [] for role in examples_by_role}
    for role, pairs in partitions.items():
        for index, (group, target) in enumerate(pairs):
            label = labels[index % len(labels)]
            association = CollectionAssociation(f"opaque-{group}", f"assessment-{group}-{index}",
                                                f"occ-{group}-{index}")
            prediction = collect_live(
                registry, association, [LiveRequest(model_id, model_version, label)],
                {"synthetic-feature": [float(index + 1)]},
            ).records[0]
            examples_by_role[role].append(CorrectnessExample(
                prediction, "synthetic-target", "v1", int(target), int(target), group, role,
                "synthetic-outcome-check", "synthetic-independence-check",
            ))
            fingerprint = prediction_fingerprint(prediction)
            row_key = SignalRowKey(sha256(
                f"synthetic-dataset\0synthetic-manifest\0{fingerprint}".encode()
            ).hexdigest())
            feature = SignalResult(
                SignalSourceKey(*prediction.source_key), SignalDimension.DATA_SUFFICIENCY,
                "evidence_coverage", "v1", {"required_evidence": []}, SignalState.AVAILABLE,
                {"coverage": 1.0}, "synthetic evidence profile", ("synthetic-input",),
                {"source": "synthetic-test"},
            )
            features_by_role[role].append(SignalFeatureRecord(
                row_key, SignalSourceKey(*prediction.source_key), (feature,),
            ))

    dataset = DatasetBuildResult(
        PartitionedDataset(*(tuple(examples_by_role[role]) for role in
                              ("train", "validation", "calibration"))),
        DatasetReadiness("ready", scope="synthetic"), (), "synthetic-manifest",
    )
    reference = Feature003DatasetReference(
        "synthetic-dataset", "synthetic-protocol", "v1", "synthetic-manifest", "builder-v1",
        sha256(b"synthetic-manifest-content").hexdigest(),
    )
    method = SignalMethodConfig("evidence_coverage", "v1", {"required_evidence": []})
    fitted = tuple()
    manifest = SignalRunManifest(reference, source_keys, (method,), fitted, run_version="signals-v1")
    signal_set = SignalFeatureSet(reference, tuple(features_by_role["train"]),
                                  tuple(features_by_role["validation"]),
                                  tuple(features_by_role["calibration"]), manifest, {})
    return definition, dataset, signal_set, reference


class SyntheticTrainingLedger:
    """Independent fixture ledger, populated before submitting source objects."""

    integration_id = "synthetic-training-ledger"

    def __init__(self, prediction_ledger):
        self.prediction_ledger = prediction_ledger
        self._accepted = {}
        self.calls = []

    def has_admission(self, dataset, signals):
        return (dataset_fingerprint(dataset), self._feature_fingerprint(signals)) in self._accepted

    @staticmethod
    def _feature_fingerprint(signals):
        return sha256(json.dumps(signals.to_dict(), sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode()).hexdigest()

    def admit(self, dataset, signals, reference, *, admit_predictions=True):
        from safira.training.verification import TrainingInputCheck

        rows = []
        for role, feature_role in (("train", "training"), ("validation", "validation"),
                                   ("calibration", "calibration")):
            examples = getattr(dataset.development, role)
            records = getattr(signals, feature_role)
            for example, feature in zip(examples, records):
                record = example.prediction
                if admit_predictions:
                    self.prediction_ledger.admit(record)
                rows.append((role, prediction_fingerprint(record), tuple(record.source_key),
                             feature.row_key.value, tuple(feature.source_key.to_tuple())))
        self._accepted[dataset_fingerprint(dataset), self._feature_fingerprint(signals)] = (
            dataset, signals, reference, tuple(rows),
        )

    def verify_inputs(self, dataset, signals):
        from safira.training.verification import TrainingInputCheck

        self.calls.append(("inputs", dataset_fingerprint(dataset), self._feature_fingerprint(signals)))
        accepted = self._accepted.get((dataset_fingerprint(dataset), self._feature_fingerprint(signals)))
        if accepted is None:
            raise ValueError("not independently admitted")
        _, _, reference, rows = accepted
        return TrainingInputCheck(
            dataset_fingerprint=dataset_fingerprint(dataset),
            feature_set_fingerprint=self._feature_fingerprint(signals),
            dataset_id=reference.dataset_id, protocol_id=reference.protocol_id,
            protocol_version=reference.protocol_version, manifest_reference=reference.manifest_reference,
            manifest_digest=reference.manifest_digest, builder_version=reference.builder_version,
            feature_run_version=signals.manifest.run_version,
            feature_method_ids=tuple(sorted((
                item.method_id, item.method_version,
                json.dumps(item.to_dict().get("parameters", {}), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False),
            ) for item in signals.manifest.method_configs)),
            fitted_state_ids=tuple(item.state_id for item in signals.manifest.fitted_state_references),
            row_inventory=tuple(sorted(rows, key=repr)), authority=self.integration_id, method="exact fixture ledger lookup",
            evidence_ref="synthetic-ledger-entry",
        )

    def verify_dataset(self, dataset, reference):
        from safira.signals.records import SignalDatasetCheck, SignalDatasetRowCheck
        from safira.signals.validation import _dataset_rows

        rows = _dataset_rows(dataset)
        return SignalDatasetCheck(
            dataset_fingerprint=dataset_fingerprint(dataset), dataset_id=reference.dataset_id,
            protocol_id=reference.protocol_id, protocol_version=reference.protocol_version,
            manifest_reference=reference.manifest_reference, builder_version=reference.builder_version,
            readiness="ready", authority=self.integration_id, method="exact fixture ledger lookup",
            evidence_ref="synthetic-dataset-entry", rows=rows, manifest_digest=reference.manifest_digest,
            authorized_partitions=("train", "validation", "calibration"),
        )

    def verify_prediction(self, record):
        return self.prediction_ledger.verify_prediction(record)
