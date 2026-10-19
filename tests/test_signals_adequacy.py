"""Protocol-scoped, exact-source cohort support from admitted synthetic data."""

import json
from dataclasses import replace

import pytest

from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.dataset import CorrectnessExample
from safira.signals.records import (
    CohortAdequacyCriteria,
    Feature003DatasetReference,
    SignalDatasetCheck,
    SignalDatasetRowCheck,
    SignalMethodConfig,
    SignalProtocol,
    SignalSourceKey,
)
from safira.signals.service import SignalExtractor
from safira.signals.validation import dataset_fingerprint
from signals_fixtures import SyntheticSignalVerifier, make_synthetic_feature003_result


class _DatasetAuthority:
    """Synthetic independent dataset inventory used only by this test module."""

    def __init__(self, record_verifier, reference):
        self.records = record_verifier
        self.reference = reference

    def verify_dataset(self, result, reference):
        rows = []
        for example in result.development.train:
            record = example.prediction
            rows.append(SignalDatasetRowCheck(
                self.records.fingerprint(record), record.source_key,
                (record.association.patient_ref, record.association.assessment_ref,
                 record.association.occurrence_ref), "train",
            ))
        return SignalDatasetCheck(
            dataset_fingerprint(result), self.reference.dataset_id, self.reference.protocol_id,
            self.reference.protocol_version, self.reference.manifest_reference,
            self.reference.builder_version, "ready", "synthetic-independent-ledger",
            "complete-development-inventory", "synthetic-dataset-entry", tuple(rows),
            authorized_partitions=("train", "validation", "calibration"),
        )


def _build_feature_set(registered_collection, targets, criteria):
    registry, register = registered_collection
    verifier = SyntheticSignalVerifier()
    definitions = {}
    for model_id, version in {key[:2] for key in targets}:
        definitions[(model_id, version)] = register(
            model_id=model_id, version=version, labels=("shared-label",), scores=(0.7,),
        )[0]

    examples = []
    for index, (model_id, version, group_ref, correctness_target) in enumerate(targets):
        definition = definitions[(model_id, version)]
        association = CollectionAssociation(
            f"synthetic-patient-{index}", f"assessment-{index}", f"occurrence-{index}",
        )
        record = collect_live(
            registry, association,
            [LiveRequest(model_id, version, "shared-label")],
            {"synthetic-feature": [0.25]},
        ).records[0]
        verifier.admit(record)
        examples.append(CorrectnessExample(
            record, "synthetic-target", "v1", correctness_target, correctness_target,
            group_ref, "train", "synthetic-outcome-check", "synthetic-independence-check",
        ))

    dataset = make_synthetic_feature003_result({"train": ()})
    dataset = replace(dataset, development=type(dataset.development)(tuple(examples), (), ()))
    source_keys = tuple(sorted({SignalSourceKey(*example.prediction.source_key) for example in examples}))
    configs = {"bernoulli_entropy": SignalMethodConfig("bernoulli_entropy", "v1", {"log_base": 2})}
    protocol = SignalProtocol(
        "synthetic-adequacy-protocol", "v1", source_keys, configs, {},
        cohort_adequacy=criteria,
    )
    reference = Feature003DatasetReference(
        "synthetic-adequacy-dataset", protocol.protocol_id, protocol.protocol_version,
        dataset.manifest_reference, "synthetic-builder-v1",
    )
    authority = _DatasetAuthority(verifier, reference)
    return SignalExtractor(registry, protocol, verifier, dataset_verifier=authority).build_feature_set(
        dataset, reference,
    )


def _support(feature_set, source):
    return feature_set.cohort_support[json.dumps(source, separators=(",", ":"))]


def test_adequacy_counts_unique_groups_and_excludes_conflicted_groups_from_class_support(registered_collection):
    targets = [
        ("adequacy", "v1", "group-a", 1),
        ("adequacy", "v1", "group-a", 1),  # repeat visit does not inflate group support
        ("adequacy", "v1", "group-b", 0),
        ("adequacy", "v1", "group-c", 0),
        ("adequacy", "v1", "group-c", 1),  # conservative conflict rule: neither class gets this group
    ]
    source = ("adequacy", "v1", "shared-label")
    criteria = {SignalSourceKey(*source): CohortAdequacyCriteria(3, {0: 1, 1: 1})}
    support = _support(_build_feature_set(registered_collection, targets, criteria), source)
    assert support["state"] == "available"
    assert support["unique_patient_groups"] == 3
    assert support["correctness_class_patient_groups"] == {"0": 1, "1": 1}
    assert support["conflicting_correctness_patient_groups"] == 1


def test_insufficient_unique_groups_returns_nonready_adequacy(registered_collection):
    source = ("small", "v1", "shared-label")
    criteria = {SignalSourceKey(*source): CohortAdequacyCriteria(2)}
    support = _support(_build_feature_set(
        registered_collection, [("small", "v1", "only-group", 1)], criteria,
    ), source)
    assert support["state"] == "insufficient_evidence"
    assert support["unique_patient_groups"] == 1


def test_missing_required_correctness_class_support_is_insufficient(registered_collection):
    source = ("class-support", "v1", "shared-label")
    criteria = {SignalSourceKey(*source): CohortAdequacyCriteria(1, {0: 1, 1: 1})}
    support = _support(_build_feature_set(
        registered_collection, [("class-support", "v1", "group-a", 1)], criteria,
    ), source)
    assert support["state"] == "insufficient_evidence"
    assert support["correctness_class_patient_groups"] == {"0": 0, "1": 1}


def test_class_support_is_not_required_when_protocol_does_not_declare_it(registered_collection):
    source = ("no-class-check", "v1", "shared-label")
    criteria = {SignalSourceKey(*source): CohortAdequacyCriteria(2)}
    support = _support(_build_feature_set(
        registered_collection,
        [("no-class-check", "v1", "group-a", 1), ("no-class-check", "v1", "group-b", 1)],
        criteria,
    ), source)
    assert support["state"] == "available"
    assert "correctness_class_patient_groups" not in support


def test_missing_criteria_is_not_ready_and_never_claims_adequacy(registered_collection):
    source = ("unconfigured", "v1", "shared-label")
    support = _support(_build_feature_set(
        registered_collection, [("unconfigured", "v1", "group-a", 1)], {},
    ), source)
    assert support["state"] == "not_ready"
    assert support["reason_code"] == "adequacy_criteria_missing"


def test_same_label_across_versions_and_models_never_pools_support(registered_collection):
    targets = [
        ("scope-a", "v1", "group-a", 1), ("scope-a", "v1", "group-b", 0),
        ("scope-a", "v2", "group-a", 1), ("scope-b", "v1", "group-a", 1),
    ]
    source_v1 = SignalSourceKey("scope-a", "v1", "shared-label")
    criteria = {
        source_v1: CohortAdequacyCriteria(2, {0: 1, 1: 1}),
        SignalSourceKey("scope-a", "v2", "shared-label"): CohortAdequacyCriteria(2),
        SignalSourceKey("scope-b", "v1", "shared-label"): CohortAdequacyCriteria(2),
    }
    feature_set = _build_feature_set(registered_collection, targets, criteria)
    assert _support(feature_set, source_v1.to_tuple())["state"] == "available"
    assert _support(feature_set, ("scope-a", "v2", "shared-label"))["unique_patient_groups"] == 1
    assert _support(feature_set, ("scope-b", "v1", "shared-label"))["unique_patient_groups"] == 1
    assert _support(feature_set, ("scope-a", "v2", "shared-label"))["state"] == "insufficient_evidence"
    assert _support(feature_set, ("scope-b", "v1", "shared-label"))["state"] == "insufficient_evidence"


def test_adequacy_metadata_is_separate_from_predictors_and_patient_identity(registered_collection):
    source = SignalSourceKey("private-scope", "v1", "shared-label")
    feature_set = _build_feature_set(
        registered_collection, [("private-scope", "v1", "patient-secret", 1)],
        {source: CohortAdequacyCriteria(1, {1: 1})},
    )
    public_text = json.dumps(feature_set.to_dict(), sort_keys=True)
    assert "patient-secret" not in public_text
    assert "correctness_target" not in public_text
    assert '"outcome"' not in public_text
    predictor_text = json.dumps([row.to_dict() for row in feature_set.training], sort_keys=True)
    assert "correctness_class_patient_groups" not in predictor_text
    assert "unique_patient_groups" not in predictor_text


def test_criteria_must_be_exactly_source_scoped_and_positive():
    with pytest.raises(ValueError):
        CohortAdequacyCriteria(0)
    with pytest.raises(ValueError):
        CohortAdequacyCriteria(1, {2: 1})
    with pytest.raises(ValueError):
        CohortAdequacyCriteria(1, {1: 0})

    source = SignalSourceKey("configured", "v1", "label")
    config = {"bernoulli_entropy": SignalMethodConfig("bernoulli_entropy", "v1", {"log_base": 2})}
    with pytest.raises(ValueError):
        SignalProtocol("criteria-scope", "v1", (source,), config, {},
                       cohort_adequacy={SignalSourceKey("other", "v1", "label"):
                                        CohortAdequacyCriteria(1)})

    original = {0: 2}
    criteria = CohortAdequacyCriteria(3, original)
    original[0] = 99
    assert criteria.correctness_class_minimums[0] == 2
    with pytest.raises(TypeError):
        criteria.correctness_class_minimums[0] = 4
