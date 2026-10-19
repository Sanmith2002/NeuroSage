"""Synthetic end-to-end Feature 004 acceptance and leakage checks."""

import json
from dataclasses import replace

from safira.adapters import AdapterCapabilities
from safira.collection import CollectionAssociation, LiveRequest, collect_live
from safira.signals.records import Feature003DatasetReference, SignalMethodConfig, SignalProtocol, SignalSourceKey
from safira.signals.service import SignalExtractor
from safira.signals.validation import dataset_fingerprint

from signals_fixtures import SyntheticSignalVerifier, make_synthetic_feature003_result


def _dataset_authority(record_verifier, reference):
    from safira.signals.records import SignalDatasetCheck, SignalDatasetRowCheck

    class Authority:
        def verify_dataset(self, result, supplied_reference):
            rows = []
            for role in ("train", "validation", "calibration"):
                for example in getattr(result.development, role):
                    record = example.prediction
                    rows.append(SignalDatasetRowCheck(
                        record_verifier.fingerprint(record), record.source_key,
                        (record.association.patient_ref, record.association.assessment_ref,
                         record.association.occurrence_ref), role,
                    ))
            return SignalDatasetCheck(dataset_fingerprint(result), reference.dataset_id,
                reference.protocol_id, reference.protocol_version, reference.manifest_reference,
                reference.builder_version, "ready", "synthetic-independent-authority",
                "full-inventory-check", "synthetic-dataset-ledger", tuple(rows),
                manifest_digest=reference.manifest_digest,
                authorized_partitions=("train", "validation", "calibration"))
    return Authority()


def test_verified_dataset_builds_six_dimension_predictors_without_supervision_or_group_ids(registered_collection):
    registry, register = registered_collection
    caps = AdapterCapabilities(prediction_probability=True, feature_representation=True,
                               domain_metadata=True, explanation=True, modality_outputs=True)
    definition, adapter = register(model_id="acceptance-model", labels=("AD",), scores=(0.8,),
                                   capabilities=caps)
    record_verifier = SyntheticSignalVerifier()

    def record(index, role):
        adapter.evidence = {"feature_representation": [float(index), float(index + 1)],
                            "domain_metadata": {"site-class": "north" if index < 3 else "south"},
                            "modality_outputs": {"sequence": 0.8, "imaging": 0.7},
                            "explanation": {"weight": 0.3}}
        association = CollectionAssociation(f"patient-secret-{index}", f"assessment-{index}", f"occ-{index}")
        interp = {
            "feature_representation": {"meaning": "synthetic vector", "shape": [2],
                "evidence_schema": "repr-v1", "preprocessing_identity": "none"},
            "domain_metadata": {"meaning": "synthetic domain metadata", "evidence_schema": "domain-v1",
                "preprocessing_identity": "none"},
            "modality_outputs": {"meaning": "comparable synthetic probabilities", "modality_ids": ["sequence", "imaging"],
                "output_space": "probability", "target_label": "AD", "target_output": "positive",
                "calibrated": True, "calibration_method": "synthetic-calibration-v1", "timing_scope": "same-assessment"},
            "explanation": {"meaning": "synthetic explanation", "method": "synthetic-shap",
                "target_label": "AD", "target_output": "uncalibrated-score", "output_space": "margin",
                "calibrated": False, "calibration_relation": "explains-uncalibrated-output"},
        }
        result = collect_live(registry, association,
            [LiveRequest(definition.model_id, definition.model_version, "AD",
                         evidence_interpretation=interp)], {"synthetic-feature": [0.25]})
        rec = result.records[0]
        record_verifier.admit(rec)
        return rec, f"opaque-group-{index}", role

    train = [record(i, "train") for i in range(4)]
    # One independently checked precomputed record exercises the other Feature 002 path.
    from safira.collection import SourceProvenance
    live = train[3][0]
    details = {"source_contract_id": "synthetic-contract", "source_contract_version": "v1",
        "integration_id": "synthetic-provenance-authority", "check_method": "exact content binding",
        "independent_evidence_ref": "synthetic-event-ledger", "event_id": "event-3",
        "content_binding_method": "controlled synthetic ledger", "external_selector": "AD-output",
        "content_bound": True, "association_bound": True, "fresh": True, "not_revoked": True,
        "unused": True, "registered_output_selector": 0}
    precomputed = replace(live, provenance=SourceProvenance(
        "precomputed", live.association, live.source_key, "trusted_source_checked", details),
        input_verification="unavailable")
    record_verifier.admit(precomputed)
    train[3] = (precomputed, train[3][1], train[3][2])
    val = [record(5, "validation")]
    cal = [record(6, "calibration")]
    dataset = make_synthetic_feature003_result({
        "train": [(r, g) for r, g, _ in train],
        "validation": [(r, g) for r, g, _ in val],
        "calibration": [(r, g) for r, g, _ in cal],
    })
    reference = Feature003DatasetReference("dataset-acceptance", "protocol-acceptance", "v1",
                                             dataset.manifest_reference, "builder-v1")
    methods = {
        "evidence_coverage": {"required_evidence": ("feature_representation", "domain_metadata", "explanation")},
        "bernoulli_entropy": {"log_base": 2},
        "modality_jsd": {"log_base": 2},
        "explanation_applicability": {},
        "knn_distance": {"k": 1, "metric": "euclidean", "fold_count": 2, "seed": "approved-seed",
            "evidence_schema": "repr-v1", "preprocessing_identity": "none"},
        "domain_familiarity": {"category_field": "site-class", "category_mapping_version": "map-v1",
            "privacy_approval_ref": "approval-v1", "fold_count": 2, "seed": "approved-seed",
            "evidence_schema": "domain-v1", "preprocessing_identity": "none"},
    }
    configs = {name: SignalMethodConfig(name, "v1", params) for name, params in methods.items()}
    protocol = SignalProtocol("protocol-acceptance", "v1", (SignalSourceKey("acceptance-model", "v1", "AD"),),
                              configs, {"data_sufficiency": ("feature_representation",)})
    admission = _dataset_authority(record_verifier, reference)
    extractor = SignalExtractor(registry, protocol, record_verifier, dataset_verifier=admission)
    features = extractor.build_feature_set(dataset, reference)

    assert len(features.training) == 4 and len(features.validation) == 1 and len(features.calibration) == 1
    observed = {result.dimension.value for result in features.training[0].predictors}
    assert {"data_sufficiency", "prediction_uncertainty", "distribution_conformity_ood",
            "modality_agreement", "domain_familiarity", "explanation_reliability"}.issubset(observed)
    serialized = json.dumps(features.to_dict(), sort_keys=True)
    ordinary_surface = serialized + repr(features) + repr(features.manifest)
    assert "patient-secret" not in ordinary_surface
    assert "correctness_target" not in ordinary_surface and '"outcome"' not in ordinary_surface
    assert "opaque-group" not in ordinary_surface and "protected_test" not in ordinary_surface
    assert "north" not in ordinary_surface and "south" not in ordinary_surface
    assert all(not hasattr(row, "correctness_target") for row in features.training)
    assert features.training[0].predictors
    primary = features.training[0].predictors[0].to_dict()["primary_output"]
    assert primary["value_kind"] == "probability" and primary["value"] == 0.8
    assert primary["class_mapping"] == {"positive_when": ">=", "boundary": 0.6}
    assert primary["meaning"] == "synthetic probability"
    primary["class_mapping"]["boundary"] = 0.9
    assert features.training[0].predictors[0].to_dict()["primary_output"]["class_mapping"]["boundary"] == 0.6
    assert any(result.provenance.get("mode") == "precomputed"
               for result in features.training[3].predictors)

    # A too-large k is reported as non-value support insufficiency even if
    # another (unapproved) reference size could have been feasible.
    insufficient_configs = dict(protocol.method_configs)
    insufficient_configs["knn_distance"] = SignalMethodConfig("knn_distance", "v1", {
        **methods["knn_distance"], "k": 9,
    })
    insufficient_protocol = SignalProtocol(protocol.protocol_id, protocol.protocol_version,
        protocol.source_keys, insufficient_configs, protocol.evidence_prerequisites)
    insufficient = SignalExtractor(registry, insufficient_protocol, record_verifier,
        dataset_verifier=admission).build_feature_set(dataset, reference)
    knn_states = [signal.state.value for row in insufficient.training
                  for signal in row.predictors if signal.method_id == "knn_distance"]
    assert knn_states == ["insufficient_evidence"] * 4


def test_standalone_multilabel_and_overlapping_contributors_keep_exact_source_keys(registered_collection):
    registry, register = registered_collection
    from safira.collection import CollectionAssociation, LiveRequest, collect_live
    from safira.adapters import AdapterCapabilities
    verifier = SyntheticSignalVerifier()
    source_records = []
    for model_id, labels in (("multi", ("AD", "PD")), ("independent", ("AD",))):
        definition, _ = register(model_id=model_id, labels=labels,
            capabilities=AdapterCapabilities(prediction_probability=True))
        requests = [LiveRequest(model_id, "v1", label) for label in labels]
        association = CollectionAssociation(f"synthetic-{model_id}", "assessment", "occurrence")
        records = collect_live(registry, association, requests, {"synthetic-feature": [0.25]}).records
        for record in records:
            verifier.admit(record)
            source_records.append(record)
    sources = tuple(SignalSourceKey(*record.source_key) for record in source_records)
    methods = {"bernoulli_entropy": SignalMethodConfig("bernoulli_entropy", "v1", {"log_base": 2})}
    protocol = SignalProtocol("multi-protocol", "1", sources, methods, {})
    extractor = SignalExtractor(registry, protocol, verifier)
    results = [extractor.extract_record(record)[0] for record in source_records]
    assert [result.source_key.to_tuple() for result in results] == [record.source_key for record in source_records]
    assert {result.source_key.label_id for result in results} == {"AD", "PD"}
    assert sum(result.source_key.label_id == "AD" for result in results) == 2
    dataset = make_synthetic_feature003_result({
        "train": [(record, f"group-{index}") for index, record in enumerate(source_records)],
    })
    reference = Feature003DatasetReference("multi-dataset", "multi-protocol", "1",
                                           dataset.manifest_reference, "builder-v1")
    feature_extractor = SignalExtractor(registry, protocol, verifier,
        dataset_verifier=_dataset_authority(verifier, reference))
    feature_set = feature_extractor.build_feature_set(dataset, reference)
    assert len(feature_set.training) == 3
    assert len([row for row in feature_set.training if row.source_key.label_id == "AD"]) == 2
