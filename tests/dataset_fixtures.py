"""Small synthetic-only Feature 003 record helpers."""

from safira.dataset import (
    EvaluationProtocol, OutcomeCandidate, PatientLinkageDeclaration,
    TargetBinding, TargetDefinition, IndependenceEvidence,
)


def target_and_binding(model_id, model_version, label_id):
    target = TargetDefinition("synthetic-outcome", "v1", "positive", "negative")
    binding = TargetBinding(target.target_id, target.target_version, model_id, model_version,
                            label_id, "positive", "negative")
    return target, binding


def outcome(patient, assessment, label, value, content_ref="synthetic-content"):
    return OutcomeCandidate("synthetic", "record-ref", patient, assessment, label,
                            "synthetic-outcome", "v1", value, content_ref=content_ref,
                            source_contract_id="synthetic-outcomes", source_contract_version="v1")


def linkage(entries):
    entries = {(("synthetic-live" if namespace == "unknown" else namespace), patient): group
               for (namespace, patient), group in entries.items()}
    return PatientLinkageDeclaration("synthetic-linkage", "v1", "synthetic-custodian",
                                     "synthetic-scope", "synthetic-evidence", entries)


def protocol(assignments, *, mode="supplied", allocation_order=(), seed="synthetic-seed"):
    return EvaluationProtocol("synthetic-protocol", "v1", "synthetic-outcome", "v1",
                              partition_mode=mode, assignments=assignments, seed=seed,
                              algorithm_version="sha256-cyclic-v1" if mode=="deterministic" else "",
                              allocation_order=allocation_order)


def independence_for(model_id, model_version, label_id):
    return IndependenceEvidence(model_id,model_version,label_id,"synthetic-outcome","v1","synthetic-development","synthetic-lineage")
