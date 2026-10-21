"""Synthetic proof that Feature 004 reference states reproduce from training only."""

from dataclasses import replace
from hashlib import sha256

import pytest

from policy_fixtures import PolicyTestLedger
from safira import AdapterCapabilities
from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.dataset.records import (CorrectnessExample, DatasetBuildResult, DatasetReadiness,
                                    PartitionedDataset)
from safira.policy.exceptions import PolicyVerificationError
from safira.policy.references import reconstruct_original_references
from safira.signals import Feature003DatasetReference, SignalExtractor
from safira.signals.records import SignalMethodConfig, SignalProtocol, SignalSourceKey
from signals_fixtures import SyntheticSignalVerifier


def _case(registered_collection):
    registry, register = registered_collection
    _, adapter = register(capabilities=AdapterCapabilities(prediction_probability=True, domain_metadata=True),
        evidence={"domain_metadata": {"site": "site-a"}}, model_id="reference-model")
    source = ("reference-model", "v1", "label-a")
    admission = SyntheticSignalVerifier()
    host = PolicyTestLedger(admission)
    examples = {"train": [], "validation": [], "calibration": []}
    for role, count in (("train", 4), ("validation", 1)):
        for index in range(count):
            adapter.evidence["domain_metadata"] = {"site": "site-a" if index % 2 == 0 else "site-b"}
            group = f"{role}-group-{index}"
            association = CollectionAssociation(group, f"{role}-assessment-{index}", f"{role}-occ-{index}")
            record = collect_live(registry, association,
                [LiveRequest(*source, evidence_interpretation={
                    "domain_metadata": {"meaning": "synthetic site category",
                        "evidence_schema": "site-schema-v1", "preprocessing_identity": "none"}})],
                {"synthetic-feature": [float(index)]}).records[0]
            examples[role].append(CorrectnessExample(record, "target", "v1", 1, 1,
                group, role, "synthetic-ground-truth", "synthetic-lineage"))
    dataset = DatasetBuildResult(PartitionedDataset(tuple(examples["train"]),
        tuple(examples["validation"]), ()), DatasetReadiness("ready", scope="synthetic"), (), "manifest-ref")
    reference = Feature003DatasetReference("reference-data", "reference-protocol", "v1",
        "manifest-ref", "builder-v1", sha256(b"reference-manifest").hexdigest())
    host.admit_dataset(dataset, reference)
    method = SignalMethodConfig("domain_familiarity", "v1", {
        "category_field": "site", "category_mapping_version": "sites-v1",
        "privacy_approval_ref": "synthetic-privacy-approval", "fold_count": 2,
        "seed": "fixed-synthetic-seed", "evidence_schema": "site-schema-v1",
        "preprocessing_identity": "none"})
    protocol = SignalProtocol(reference.protocol_id, reference.protocol_version,
        (SignalSourceKey(*source),), {method.method_id: method}, {})
    features = SignalExtractor(registry, protocol, host, dataset_verifier=host).build_feature_set(dataset, reference)
    return dataset, reference, protocol, features


def test_frozen_feature004_domain_reference_reconstructs_from_original_training_only(registered_collection):
    dataset, reference, protocol, features = _case(registered_collection)
    states = reconstruct_original_references(dataset, reference, protocol, features)
    state = states[(('reference-model', 'v1', 'label-a'), 'domain_familiarity')]
    assert state.compatibility_key.dataset_id == reference.dataset_id
    assert state.vocabulary == frozenset({"site-a", "site-b"})
    assert state.digest == features.manifest.fitted_state_references[0].state_id


def test_changed_frozen_reference_digest_is_rejected(registered_collection):
    dataset, reference, protocol, features = _case(registered_collection)
    frozen = features.manifest.fitted_state_references[0]
    changed_frozen = replace(frozen, state_id="0" * 64)
    manifest = replace(features.manifest, fitted_state_references=(changed_frozen,))
    with pytest.raises(PolicyVerificationError, match="reference_reproduction_failed"):
        reconstruct_original_references(dataset, reference, protocol, replace(features, manifest=manifest))


def test_policy_signal_row_applies_original_reference_and_uses_new_row_identity(registered_collection):
    from safira.policy.signals import build_policy_signal_rows
    from safira.signals.validation import prediction_fingerprint

    registry, register = registered_collection
    _, adapter = register(capabilities=AdapterCapabilities(prediction_probability=True, domain_metadata=True),
        evidence={"domain_metadata": {"site": "site-a"}}, model_id="policy-reference-model")
    source = ("policy-reference-model", "v1", "label-a")
    admission = SyntheticSignalVerifier()
    host = PolicyTestLedger(admission)
    method = SignalMethodConfig("domain_familiarity", "v1", {
        "category_field": "site", "category_mapping_version": "sites-v1",
        "privacy_approval_ref": "synthetic-privacy-approval", "fold_count": 2,
        "seed": "fixed-synthetic-seed", "evidence_schema": "site-schema-v1",
        "preprocessing_identity": "none"})
    original_rows = []
    for index, category in enumerate(("site-a", "site-b", "site-a", "site-b")):
        adapter.evidence["domain_metadata"] = {"site": category}
        group = f"original-{index}"
        association = CollectionAssociation(group, f"original-assessment-{index}", f"original-occ-{index}")
        prediction = collect_live(registry, association, [LiveRequest(*source,
            evidence_interpretation={"domain_metadata": {"meaning": "site category",
                "evidence_schema": "site-schema-v1", "preprocessing_identity": "none"}})],
            {"synthetic-feature": [float(index)]}).records[0]
        original_rows.append(CorrectnessExample(prediction, "target", "v1", 1, 1, group, "train", "gt", "ind"))
    original = DatasetBuildResult(PartitionedDataset(tuple(original_rows), (), ()),
        DatasetReadiness("ready", scope="synthetic"), (), "original-manifest")
    original_ref = Feature003DatasetReference("original-policy-ref", "original-protocol", "v1",
        "original-manifest", "builder-v1", sha256(b"original-manifest").hexdigest())
    host.admit_dataset(original, original_ref)
    original_protocol = SignalProtocol("original-protocol", "v1", (SignalSourceKey(*source),),
        {method.method_id: method}, {})
    feature_set = SignalExtractor(registry, original_protocol, host,
        dataset_verifier=host).build_feature_set(original, original_ref)
    fitted = reconstruct_original_references(original, original_ref, original_protocol, feature_set)

    policy_examples = []
    policy_predictions = []
    for index, category in enumerate(("site-a", "site-c")):
        adapter.evidence["domain_metadata"] = {"site": category}
        group = f"policy-group-{index}"
        association = CollectionAssociation(group, f"policy-assessment-{index}", f"policy-occurrence-{index}")
        prediction = collect_live(registry, association, [LiveRequest(*source,
            evidence_interpretation={"domain_metadata": {"meaning": "site category",
                "evidence_schema": "site-schema-v1", "preprocessing_identity": "none"}})],
            {"synthetic-feature": [float(index)]}).records[0]
        policy_predictions.append(prediction)
        policy_examples.append(CorrectnessExample(prediction, "target", "v1", 1, 1, group,
            "validation", "gt", "ind"))
    policy_dataset = DatasetBuildResult(PartitionedDataset((), tuple(policy_examples), ()),
        DatasetReadiness("ready", scope="synthetic"), (), "policy-manifest")
    policy_ref = Feature003DatasetReference("policy-data-ref", "policy-protocol", "v1",
        "policy-manifest", "builder-v1", sha256(b"policy-manifest").hexdigest())
    host.admit_dataset(policy_dataset, policy_ref)
    policy_protocol = SignalProtocol("policy-protocol", "v1", (SignalSourceKey(*source),),
        {method.method_id: method}, {})
    extractor = SignalExtractor(registry, policy_protocol, host, dataset_verifier=host)
    rows = build_policy_signal_rows(policy_dataset, policy_ref, policy_protocol, extractor, fitted, host)
    assert len(rows) == 2
    assert rows[0].predictors[0].value == "seen"
    assert rows[1].predictors[0].value == "unseen"
    assert fitted[(source, "domain_familiarity")].vocabulary == frozenset({"site-a", "site-b"})
    assert rows[0].row_key.value != feature_set.training[0].row_key.value
    assert rows[0].predictors[0].provenance["query_evidence_ref"] == sha256(
        f"{prediction_fingerprint(policy_predictions[0])}\0domain_metadata".encode()).hexdigest()
