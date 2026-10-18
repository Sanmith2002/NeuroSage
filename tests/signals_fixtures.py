"""Synthetic-only Feature 004 fixtures built on the existing Feature 001/002 APIs."""

from __future__ import annotations

from hashlib import sha256
import json

from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.dataset import (
    CorrectnessExample,
    DatasetBuildResult,
    DatasetReadiness,
    PartitionedDataset,
)


class SyntheticSignalVerifier:
    """Independent in-memory admission ledger; never trusts record assertions."""

    integration_id = "synthetic-signal-admission-ledger"

    def __init__(self):
        self._entries = {}
        self.calls = []

    @staticmethod
    def fingerprint(record):
        body = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(body.encode("utf-8")).hexdigest()

    @staticmethod
    def association(record):
        value = record.association
        return value.patient_ref, value.assessment_ref, value.occurrence_ref

    def admit(self, record):
        self._entries[self.fingerprint(record)] = (
            record.source_key, self.association(record), record.provenance.mode,
        )

    def verify_prediction(self, record):
        from safira.signals.records import SignalInputCheck

        fingerprint = self.fingerprint(record)
        expected = (record.source_key, self.association(record), record.provenance.mode)
        matched = self._entries.get(fingerprint) == expected
        self.calls.append(fingerprint)
        return SignalInputCheck(
            record_fingerprint=fingerprint,
            source_key=record.source_key,
            association=self.association(record),
            provenance_mode=record.provenance.mode,
            state="verified" if matched else "rejected",
            authority=self.integration_id,
            method="exact independent synthetic ledger comparison",
            evidence_ref="ledger-entry-" + fingerprint[:12],
            input_scope="synthetic-test-record",
        )


def make_live_record(
    registry,
    register,
    *,
    model_id="signals-model",
    version="v1",
    labels=("label-a",),
    scores=(0.7,),
    value_kinds=None,
    capabilities=None,
    evidence=None,
    interpretations=None,
    modalities=(),
):
    """Register an exact synthetic classifier and collect one synthetic row."""

    kinds = tuple(value_kinds or ("probability",) * len(labels))
    definition, adapter = register(
        model_id=model_id, version=version, labels=tuple(labels), scores=tuple(scores),
        kinds=kinds, capabilities=capabilities, evidence=evidence or {}, modalities=modalities,
    )
    association = CollectionAssociation("opaque-synthetic-patient", "assessment-1", "occurrence-1")
    request = LiveRequest(
        model_id, version, labels[0], tuple(modalities) if modalities else None,
        interpretations or {},
    )
    record = collect_live(
        registry, association, [request], {"synthetic-feature": [0.25]},
    ).records[0]
    return definition, adapter, record


def signal_protocol(source_key, methods, *, prerequisites=None):
    from safira.signals.records import SignalMethodConfig, SignalProtocol, SignalSourceKey

    configs = {
        method_id: SignalMethodConfig(method_id, "v1", parameters)
        for method_id, parameters in methods.items()
    }
    return SignalProtocol(
        "synthetic-signal-protocol", "v1", (SignalSourceKey(*source_key),),
        configs, prerequisites or {},
    )


def make_synthetic_feature003_result(partitions):
    """Build a Feature 003-shaped development result from synthetic predictions.

    `partitions` maps train/validation/calibration to `(prediction, group_ref)` pairs.
    It is a structural fixture only and carries no trusted verification claim.
    """
    examples = {"train": [], "validation": [], "calibration": []}
    for role, rows in partitions.items():
        if role not in examples:
            raise ValueError("synthetic partition role")
        for prediction, group_ref in rows:
            examples[role].append(CorrectnessExample(
                prediction=prediction,
                target_id="synthetic-target",
                target_version="v1",
                outcome=1,
                correctness_target=1,
                patient_group_ref=group_ref,
                partition_role=role,
                verification_ref="synthetic-verification-ref",
                independence_ref="synthetic-independence-ref",
            ))
    development = PartitionedDataset(
        tuple(examples["train"]), tuple(examples["validation"]), tuple(examples["calibration"]),
    )
    return DatasetBuildResult(
        development=development,
        readiness=DatasetReadiness("ready", scope="synthetic-only"),
        exclusions=(),
        manifest_reference="synthetic-manifest-reference",
        summary={"synthetic_rows": sum(len(rows) for rows in examples.values())},
    )
