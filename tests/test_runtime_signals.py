from dataclasses import replace

import pytest

from runtime_fixtures import build_runtime_fixture
from safira.runtime._verification import admit_runtime_request
from safira.runtime._signals import derive_runtime_signal_record, reconstruct_runtime_references


def test_single_record_signals_preserve_feature004_method_and_availability(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    record, reference_states = derive_runtime_signal_record(admitted)
    assert tuple(record.source_key.to_tuple()) == fixture.expected["scope"]
    assert len(record.predictors) == len(fixture.request.original_signal_protocol.method_configs)
    assert record.predictors[0].method_id == "bernoulli_entropy"
    assert record.predictors[0].state.value == "available"
    assert reference_states == {}


def test_reference_reconstruction_is_original_training_only_and_digest_bound(
        registered_collection, monkeypatch):
    from safira.dataset.records import CorrectnessExample

    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    monkeypatch.setattr(CorrectnessExample, "correctness_target",
                        property(lambda _self: pytest.fail("reference read correctness target")),
                        raising=False)
    monkeypatch.setattr(CorrectnessExample, "outcome",
                        property(lambda _self: pytest.fail("reference read ground truth")), raising=False)
    assert reconstruct_runtime_references(admitted) == {}


def test_caller_signal_rows_cannot_replace_private_record_derivation(registered_collection):
    fixture = build_runtime_fixture(registered_collection)
    admitted = admit_runtime_request(fixture.registry, fixture.request, fixture.verifier)
    with pytest.raises(TypeError):
        derive_runtime_signal_record(admitted, signal_rows=())


def _reference_only_admission(fixture, *, method_id="knn_distance"):
    from dataclasses import replace
    from types import SimpleNamespace
    from safira.collection.records import EvidenceItem, SourceProvenance
    from safira.dataset.records import DatasetBuildResult, PartitionedDataset
    from safira.signals import SignalExtractor
    from safira.signals.records import SignalMethodConfig, SignalProtocol
    from safira.signals.validation import dataset_fingerprint

    request = fixture.request
    source = request.scope.source_key
    examples = []
    for index, example in enumerate(request.original_dataset.development.train):
        record = example.prediction
        if method_id == "knn_distance":
            category = "feature_representation"
            value = [float(index), float(index + 1)]
            params = {"k": 1, "metric": "euclidean", "fold_count": 2, "seed": "test-seed",
                      "evidence_schema": "synthetic-vector-v1", "preprocessing_identity": "none"}
            interpretation = {"meaning": "synthetic vector", "shape": [2],
                              "evidence_schema": "synthetic-vector-v1",
                              "preprocessing_identity": "none"}
        else:
            category = "domain_metadata"
            value = {"site": f"site-{index % 2}"}
            params = {"category_field": "site", "category_mapping_version": "v1",
                      "privacy_approval_ref": "synthetic-test-approval", "fold_count": 2,
                      "seed": "test-seed", "evidence_schema": "synthetic-domain-v1",
                      "preprocessing_identity": "none"}
            interpretation = {"meaning": "synthetic domain", "evidence_schema": "synthetic-domain-v1",
                              "preprocessing_identity": "none"}
        evidence = EvidenceItem(record.association, source, category, "available", value=value,
                                interpretation=interpretation)
        selector = fixture.registry.get_metadata(source[0], source[1]).labels[0].output_selector
        provenance = SourceProvenance("precomputed", record.association, source,
            "trusted_source_checked", {
                "source_contract_id": "synthetic-contract", "source_contract_version": "v1",
                "integration_id": "test-ledger", "check_method": "synthetic-fixture-binding",
                "independent_evidence_ref": "synthetic-evidence", "event_id": f"runtime-{index}",
                "content_binding_method": "sha256-test-binding", "external_selector": source[2],
                "content_bound": True, "association_bound": True, "fresh": True,
                "not_revoked": True, "unused": True, "registered_output_selector": selector,
            })
        examples.append(replace(example, prediction=replace(record, evidence=(evidence,),
                                                               provenance=provenance,
                                                               input_verification="unavailable")))
    dataset = DatasetBuildResult(
        PartitionedDataset(tuple(examples), request.original_dataset.development.validation,
                           request.original_dataset.development.calibration),
        request.original_dataset.readiness, request.original_dataset.exclusions,
        request.original_dataset.manifest_reference,
    )
    method = SignalMethodConfig(method_id, "v1", params)
    protocol = SignalProtocol(request.original_reference.protocol_id,
        request.original_reference.protocol_version, request.original_signal_protocol.source_keys,
        {method_id: method}, {})
    fixture.verifier.base.admit_dataset(dataset, request.original_reference)
    for example in dataset.development.train:
        fixture.verifier.prediction_ledger.admit(example.prediction)
    signals = SignalExtractor(fixture.registry, protocol, fixture.verifier,
        dataset_verifier=fixture.verifier).build_feature_set(dataset, request.original_reference)
    return SimpleNamespace(scope_key=source, request=SimpleNamespace(
        original_dataset=dataset, original_reference=request.original_reference,
        original_signal_protocol=protocol, original_signal_set=signals,
    ))


@pytest.mark.parametrize("method_id", ["knn_distance", "domain_familiarity"])
def test_training_reference_reconstruction_matches_exact_feature004_state_without_targets(
        registered_collection, monkeypatch, method_id):
    from safira.dataset.records import CorrectnessExample

    fixture = build_runtime_fixture(registered_collection)
    admitted = _reference_only_admission(fixture, method_id=method_id)
    monkeypatch.setattr(CorrectnessExample, "correctness_target",
                        property(lambda _self: pytest.fail("reference read correctness target")),
                        raising=False)
    monkeypatch.setattr(CorrectnessExample, "outcome",
                        property(lambda _self: pytest.fail("reference read ground truth")), raising=False)
    states = reconstruct_runtime_references(admitted)
    assert set(states) == {(admitted.scope_key, method_id)}


def test_mismatched_fitted_reference_digest_is_rejected(registered_collection):
    from dataclasses import replace
    from types import SimpleNamespace
    from safira.runtime._exceptions import RuntimeAdmissionRejected

    fixture = build_runtime_fixture(registered_collection)
    admitted = _reference_only_admission(fixture, method_id="knn_distance")
    signal_set = admitted.request.original_signal_set
    original_state = signal_set.manifest.fitted_state_references[0]
    altered_state = replace(original_state, state_id="f" * 64)
    altered_manifest = replace(signal_set.manifest, fitted_state_references=(altered_state,))
    altered_set = replace(signal_set, manifest=altered_manifest)
    admitted.request.original_signal_set = altered_set
    with pytest.raises(RuntimeAdmissionRejected, match="signal_reference_incompatible"):
        reconstruct_runtime_references(admitted)


@pytest.mark.parametrize("evidence_state", ["available", "missing", "unavailable", "unsupported"])
def test_explanation_applicability_preserves_actual_available_and_unavailable_states(
        registered_collection, evidence_state):
    from dataclasses import replace
    from safira.adapters import AdapterCapabilities
    from safira.collection import CollectionAssociation, LiveRequest, collect_live
    from safira.collection.records import EvidenceItem
    from safira.signals import SignalExtractor
    from safira.signals.records import SignalMethodConfig, SignalProtocol, SignalSourceKey
    from signals_fixtures import SyntheticSignalVerifier

    registry, register = registered_collection
    interpretation = {
        "meaning": "synthetic explanation metadata only", "method": "fixture",
        "target_label": "label-a", "target_output": "positive", "output_space": "probability",
        "calibrated": False,
    }
    evidence = ({"explanation": {"feature": 1.0}}
                if evidence_state == "available" else {})
    _, adapter = register(model_id="explanation-model", capabilities=AdapterCapabilities(
        prediction_probability=True, explanation=True), evidence=evidence)
    source = ("explanation-model", "v1", "label-a")
    verifier = SyntheticSignalVerifier()
    record = collect_live(registry, CollectionAssociation("explain-patient", "explain-assessment",
        "explain-occurrence"), [LiveRequest(*source, evidence_interpretation={
            "explanation": interpretation})], {"synthetic-feature": [1.0]}).records[0]
    if evidence_state in ("unavailable", "unsupported"):
        item = EvidenceItem(record.association, source, "explanation", evidence_state,
                            reason_code=evidence_state)
        record = replace(record, evidence=(item,))
    verifier.admit(record)
    method = SignalMethodConfig("explanation_applicability", "v1", {})
    protocol = SignalProtocol("explain-protocol", "v1", (SignalSourceKey(*source),),
                              {method.method_id: method}, {})
    result = SignalExtractor(registry, protocol, verifier).extract_record(record)[0]
    expected = {"available": "available", "missing": "missing",
                "unavailable": "unavailable", "unsupported": "unsupported"}[evidence_state]
    assert result.state.value == expected
    if expected == "available":
        assert result.value["applicability"] == "metadata_only"
        assert result.value["method"] == "fixture"
    else:
        assert result.value is None

