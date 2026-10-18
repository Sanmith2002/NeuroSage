"""Focused regression tests for the Feature 003 manual-audit findings."""

from dataclasses import replace

import pytest

from safira.collection import CollectionAssociation, SourceProvenance, collect_live
from safira.dataset import DatasetBuilder, EvaluationProtocol, PriorHistoryVerification
from tests.dataset_fixtures import (
    independence_for, linkage, outcome, target_and_binding,
)
from tests.test_dataset_acceptance import Verifier
from safira.dataset.exceptions import PatientGroupingConflict
from safira.dataset.partitioning import resolve_groups


class AdmissionLedger(Verifier):
    """Synthetic trusted authority; admitted digests are kept out of records."""

    def __init__(self, admitted=()):
        self.admitted = set(admitted)

    def verify_prediction_admission(self, prediction):
        from safira.dataset import PredictionAdmissionVerification
        from safira.dataset.verification import prediction_fingerprint

        digest = prediction_fingerprint(prediction)
        state = "verified" if digest in self.admitted else "rejected"
        return PredictionAdmissionVerification(
            digest, prediction.source_key, prediction.association, prediction.provenance.mode,
            state, "synthetic-ledger", "exact-record-ledger-lookup", "synthetic-admission-ref",
        )


class ManifestCustodian:
    def __init__(self):
        self.manifests = []

    def accept(self, manifest, protocol, manifest_reference):
        from safira.dataset import DatasetManifestReceipt

        self.manifests.append((manifest, protocol.protocol_id, manifest_reference))
        return DatasetManifestReceipt("accepted", "synthetic-custodian-receipt")


def _prediction(registry, definition, patient="patient-a", score_input=None):
    association = CollectionAssociation(patient, f"assessment-{patient}", f"occurrence-{patient}")
    result = collect_live(
        registry, association,
        [(definition.model_id, definition.model_version, "label-a")],
        {"synthetic-feature": [0.25] if score_input is None else score_input},
    )
    return result.records[0]


def _setup(registry, register, model_id="model-a", patient="patient-a", score=None):
    definition, adapter = register(labels=("label-a",), scores=(0.8,), model_id=model_id)
    prediction = _prediction(registry, definition, patient)
    target, binding = target_and_binding(definition.model_id, definition.model_version, "label-a")
    protocol = EvaluationProtocol(
        "synthetic-protocol", "v1", target.target_id, target.target_version,
        assignments={f"group-{patient}": "train"},
    )
    return definition, adapter, prediction, target, binding, protocol


def _build(registry, verifier, manifest_handoff, prediction, target, bindings, protocol,
           *, outcomes=None, source_namespaces=None, group_attributes=None,
           hard_constraints=None, adequacy_criteria=None):
    if hard_constraints is not None or adequacy_criteria is not None:
        protocol = replace(
            protocol,
            hard_constraints=hard_constraints if hard_constraints is not None else protocol.hard_constraints,
            adequacy_criteria=adequacy_criteria if adequacy_criteria is not None else protocol.adequacy_criteria,
        )
    return DatasetBuilder(registry, verifier).build(
        [prediction], outcomes or [outcome(prediction.association.patient_ref,
                                            prediction.association.assessment_ref,
                                            prediction.label_id, "positive")],
        [target], bindings, linkage({("synthetic-live", prediction.association.patient_ref):
                                    f"group-{prediction.association.patient_ref}"}), protocol,
        independence_evidence=[independence_for(*prediction.source_key)],
        source_namespaces=source_namespaces,
        group_attributes=group_attributes,
        manifest_handoff=manifest_handoff,
    )


def test_f1_forged_source_provenance_is_not_prediction_admission(registered_collection):
    registry, register = registered_collection
    definition, _, genuine, target, binding, protocol = _setup(registry, register)
    forged = replace(genuine, provenance=SourceProvenance(
        "live", genuine.association, genuine.source_key, "verified_live_binding",
        {"classifier_sha256": "asserted", "adapter_id": "asserted", "adapter_version": "asserted",
         "adapter_fingerprint": "asserted", "identity_scope": "asserted", "output_selector": "asserted",
         "source_namespace": "synthetic-live"},
    ))
    from safira.dataset.verification import prediction_fingerprint
    verifier = AdmissionLedger({prediction_fingerprint(genuine)})
    from safira.dataset.verification import prediction_fingerprint
    result = _build(registry, verifier, ManifestCustodian(), forged, target, [binding], protocol,
                    source_namespaces={prediction_fingerprint(forged): "synthetic-live"})
    assert result.readiness.state != "ready"
    assert not result.development.train


def test_f2_manifest_is_sent_only_to_custodian_handoff(registered_collection):
    registry, register = registered_collection
    definition, _, prediction, target, binding, protocol = _setup(registry, register)
    from safira.dataset.verification import prediction_fingerprint
    custodian = ManifestCustodian()
    result = _build(registry, AdmissionLedger({prediction_fingerprint(prediction)}), custodian,
                    prediction, target, [binding], protocol,
                    source_namespaces={prediction_fingerprint(prediction): "synthetic-live"})
    assert result.readiness.state == "ready"
    assert len(custodian.manifests) == 1
    manifest = custodian.manifests[0][0]
    assert manifest.assignments == protocol.assignments
    assert manifest.digest == result.manifest_reference.removeprefix("manifest:")
    assert "assignments" not in result.to_dict()
    assert "synthetic-linkage" not in repr(result)
    assert "synthetic-linkage" not in repr(result.to_dict())


def test_f3_per_label_adequacy_is_checked_per_exact_contributor(registered_collection):
    registry, register = registered_collection
    first, _, p1, target, b1, protocol = _setup(registry, register, "model-a", "patient-a")
    second, _, p2, _, b2, _ = _setup(registry, register, "model-b", "patient-b")
    protocol = EvaluationProtocol(
        protocol.protocol_id, protocol.protocol_version, target.target_id, target.target_version,
        assignments={"group-patient-a": "train", "group-patient-b": "train"},
        adequacy_criteria={"minimum_examples_per_label": 2, "minimum_groups_per_label": 2,
                           "minimum_correct_predictions_per_label": 2},
    )
    verifier = AdmissionLedger()
    from safira.dataset.verification import prediction_fingerprint
    verifier.admitted = {prediction_fingerprint(p1), prediction_fingerprint(p2)}
    custodian = ManifestCustodian()
    result = DatasetBuilder(registry, verifier).build(
        [p1, p2], [outcome("patient-a", "assessment-patient-a", "label-a", "positive"),
                    outcome("patient-b", "assessment-patient-b", "label-a", "positive")],
        [target], [b1, b2], linkage({("synthetic-live", "patient-a"): "group-patient-a",
                                    ("synthetic-live", "patient-b"): "group-patient-b"}), protocol,
        independence_evidence=[independence_for(*p1.source_key), independence_for(*p2.source_key)],
        source_namespaces={prediction_fingerprint(p1): "synthetic-live", prediction_fingerprint(p2): "synthetic-live"},
        manifest_handoff=custodian,
    )
    assert result.readiness.state == "INSUFFICIENT_EVIDENCE"
    assert "minimum_examples_per_label_not_met" in result.readiness.reason_codes


def test_f4_supplied_site_constraints_are_enforced_and_unknown_constraints_rejected(registered_collection):
    registry, register = registered_collection
    definition, _, prediction, target, binding, _ = _setup(registry, register)
    protocol = EvaluationProtocol(
        "synthetic-protocol", "v1", target.target_id, target.target_version,
        assignments={"group-patient-a": "train"},
        hard_constraints={"site_isolation": "same_partition"},
    )
    from safira.dataset.verification import prediction_fingerprint
    verifier = AdmissionLedger({prediction_fingerprint(prediction)})
    result = DatasetBuilder(registry, verifier).build(
        [prediction], [outcome("patient-a", "assessment-patient-a", "label-a", "positive")],
        [target], [binding], linkage({("synthetic-live", "patient-a"): "group-patient-a"}), protocol,
        independence_evidence=[independence_for(*prediction.source_key)],
        source_namespaces={prediction_fingerprint(prediction): "synthetic-live"},
        group_attributes={"group-patient-a": {"site": "site-a", "stratum": "stratum-a"}},
        manifest_handoff=ManifestCustodian(),
    )
    assert result.readiness.state == "ready"
    unsupported = replace(protocol, hard_constraints={"invented_rule": True})
    rejected = DatasetBuilder(registry, verifier).build(
        [prediction], [outcome("patient-a", "assessment-patient-a", "label-a", "positive")],
        [target], [binding], linkage({("synthetic-live", "patient-a"): "group-patient-a"}), unsupported,
        independence_evidence=[independence_for(*prediction.source_key)],
        source_namespaces={prediction.source_key: "synthetic-live"}, manifest_handoff=ManifestCustodian(),
    )
    assert rejected.readiness.state == "NOT_READY"
    assert "unsupported_partition_constraint" in rejected.readiness.reason_codes


def test_f4_supplied_site_time_and_strata_constraints_are_checked():
    from safira.dataset import DatasetProtocolError
    from safira.dataset.partitioning import assign_groups

    groups = {"g1", "g2"}
    supplied = EvaluationProtocol(
        "p", "v1", "t", "v1", assignments={"g1": "train", "g2": "validation"},
        hard_constraints={"site_isolation": "same_partition"},
    )
    attrs = {"g1": {"site": "site-a"}, "g2": {"site": "site-a"}}
    with pytest.raises(DatasetProtocolError, match="partition_constraints_infeasible"):
        assign_groups(groups, supplied, attrs)

    time_protocol = EvaluationProtocol(
        "p", "v1", "t", "v1", partition_mode="deterministic", seed="approved",
        algorithm_version="hash-v1", allocation_order=("train", "validation", "calibration", "protected_test"),
        hard_constraints={"time_windows": {
            "train": {"start": "2020-01-01T00:00:00+00:00", "end": "2021-01-01T00:00:00+00:00"},
            "validation": {"start": "2021-01-01T00:00:00+00:00", "end": "2022-01-01T00:00:00+00:00"},
        }},
    )
    allocated = assign_groups({"g1", "g2"}, time_protocol, {
        "g1": {"time": "2020-06-01T00:00:00+00:00"},
        "g2": {"time": "2021-06-01T00:00:00+00:00"},
    })
    assert allocated == {"g1": "train", "g2": "validation"}

    strata_protocol = EvaluationProtocol("p", "v1", "t", "v1", assignments={"g1": "train"},
                                         allowed_strata=("eligible",))
    with pytest.raises(DatasetProtocolError, match="partition_constraints_infeasible"):
        assign_groups({"g1"}, strata_protocol, {"g1": {"stratum": "unapproved"}})


def test_f4_deterministic_site_isolation_allocates_once_per_site(monkeypatch):
    import safira.dataset.partitioning as partitioning
    from safira.dataset import DatasetProtocolError

    real_hash = partitioning.sha256
    calls = []
    def counted(value):
        calls.append(value)
        return real_hash(value)
    monkeypatch.setattr(partitioning, "sha256", counted)
    protocol = EvaluationProtocol(
        "p", "v1", "t", "v1", partition_mode="deterministic", seed="approved",
        algorithm_version="hash-v1", allocation_order=("train", "validation", "calibration", "protected_test"),
        hard_constraints={"site_isolation": "same_partition"},
    )
    allocated = partitioning.assign_groups({"g1", "g2", "g3"}, protocol, {
        "g1": {"site": "site-a"}, "g2": {"site": "site-a"}, "g3": {"site": "site-b"},
    })
    assert allocated["g1"] == allocated["g2"]
    assert len(calls) == 2
    assert all(value.startswith(b"approved\0site\0") for value in calls)


def test_f5_live_record_requires_explicit_source_namespace(registered_collection):
    registry, register = registered_collection
    definition, _, prediction, target, binding, protocol = _setup(registry, register)
    from safira.dataset.verification import prediction_fingerprint
    verifier = AdmissionLedger({prediction_fingerprint(prediction)})
    unknown_declaration = __import__("safira.dataset", fromlist=["PatientLinkageDeclaration"]).PatientLinkageDeclaration(
        "synthetic-linkage", "v1", "custodian", "scope", "evidence", {("unknown", "patient-a"): "group-patient-a"})
    with pytest.raises(PatientGroupingConflict):
        resolve_groups([prediction], unknown_declaration)
    missing = DatasetBuilder(registry, verifier).build(
        [prediction], [outcome("patient-a", "assessment-patient-a", "label-a", "positive")],
        [target], [binding], __import__("safira.dataset", fromlist=["PatientLinkageDeclaration"]).PatientLinkageDeclaration(
            "synthetic-linkage", "v1", "custodian", "scope", "evidence", {("unknown", "patient-a"): "group-patient-a"}), protocol,
        independence_evidence=[independence_for(*prediction.source_key)], manifest_handoff=ManifestCustodian(),
    )
    assert missing.readiness.state == "NOT_READY"
    assert "source_namespace_required" in missing.readiness.reason_codes
    accepted = _build(registry, verifier, ManifestCustodian(), prediction, target, [binding], protocol,
                      source_namespaces={prediction_fingerprint(prediction): "synthetic-live"})
    assert accepted.readiness.state == "ready"


def test_f6_prior_history_verification_detaches_membership_input():
    membership = ["opaque-group"]
    check = PriorHistoryVerification(
        "manifest", "v1", "custodian", "source", "scope", "scope", "verified_complete",
        "coverage-ref", membership, "authority", "method", "evidence-ref",
    )
    membership[0] = "changed"
    assert check.protected_membership == ("opaque-group",)
