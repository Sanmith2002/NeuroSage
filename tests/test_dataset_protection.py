from safira.collection import CollectionAssociation, collect_live
from dataclasses import fields
from safira.dataset import (
    DatasetBuilder, IndependenceVerification, LinkageVerification,
    OutcomeVerification, ProtectedArtifactReceipt,
)
from tests.dataset_fixtures import target_and_binding, outcome, linkage, protocol, independence_for


class Verifier:
    def verify_linkage(self,d,refs,p): return LinkageVerification(d.linkage_id,d.linkage_version,d.scope,"verified","a","m","e",d.entries,tuple(refs))
    def verify_outcome(self,o,r,t,b): return OutcomeVerification(o.content_ref,o.source_contract_id,o.source_contract_version,o.patient_ref,o.assessment_ref,o.label_id,o.target_id,o.target_version,"verified","a","m","e",source_namespace=o.source_namespace,source_record_ref=o.source_record_ref)
    def verify_independence(self,r,m,e,p): return IndependenceVerification(r.model_id,r.model_version,r.label_id,e.target_id,e.target_version,"eligible","a","m","e",e.development_source_ref,e.lineage_ref)


class Handoff:
    def __init__(self): self.artifact=None; self.manifest_reference=None
    def accept(self,artifact,protocol,manifest_reference):
        self.artifact=artifact; self.manifest_reference=manifest_reference
        return ProtectedArtifactReceipt("accepted","safe-receipt")


def test_protected_rows_only_reach_custodian_handoff(registered_collection):
    registry,register=registered_collection
    definition,adapter=register(labels=("label-a",),scores=(.2,))
    records=[]
    for patient in ("development-patient","protected-patient"):
        records.extend(collect_live(registry,CollectionAssociation(patient,"assessment-"+patient,"occurrence-"+patient),
            [(definition.model_id,definition.model_version,"label-a")],{"synthetic-feature":[.2]}).records)
    adapter.calls.clear()
    target,binding=target_and_binding(definition.model_id,definition.model_version,"label-a")
    outcomes=[outcome(r.association.patient_ref,r.association.assessment_ref,"label-a","positive",content_ref="private-outcome-"+r.association.patient_ref) for r in records]
    groups={("unknown",r.association.patient_ref):"group-"+r.association.patient_ref for r in records}
    assignments={groups[("unknown",r.association.patient_ref)]:("train" if i==0 else "protected_test") for i,r in enumerate(records)}
    p=protocol(assignments); p=type(p)(**{**p.__dict__,"require_protected_handoff":True})
    handoff=Handoff()
    result=DatasetBuilder(registry,Verifier()).build(records,outcomes,[target],[binding],linkage(groups),p,
        independence_evidence=[independence_for(definition.model_id,definition.model_version,"label-a")],protected_artifact_handoff=handoff)
    assert result.readiness.state=="ready"
    assert len(handoff.artifact.rows)==1
    assert handoff.manifest_reference==result.manifest_reference
    serialized=repr(result.to_dict()); complete=repr(result)
    public_values=[getattr(result,item.name) for item in fields(result)]
    all_public_fields=repr(public_values)
    assert "protected-patient" not in serialized and "protected-patient" not in complete
    assert "protected-patient" not in all_public_fields
    assert "private-outcome-protected-patient" not in serialized and "private-outcome-protected-patient" not in complete
    assert len(result.development.train)==1
    assert result.protected_receipt.receipt_ref==""
    assert adapter.calls==[]


def test_protected_outcomes_do_not_satisfy_development_adequacy(registered_collection):
    registry,register=registered_collection
    definition,_=register(labels=("label-a",),scores=(.2,))
    association=CollectionAssociation("protected-patient","assessment","occurrence")
    record=collect_live(registry,association,[(definition.model_id,definition.model_version,"label-a")],{"synthetic-feature":[.2]}).records[0]
    target,binding=target_and_binding(definition.model_id,definition.model_version,"label-a")
    grouping=linkage({("unknown","protected-patient"):"protected-group"})
    p=protocol({"protected-group":"protected_test"})
    p=type(p)(**{**p.__dict__,"adequacy_criteria":{"minimum_positive_outcomes":1},"require_protected_handoff":True})
    handoff=Handoff()
    result=DatasetBuilder(registry,Verifier()).build([record],[outcome("protected-patient","assessment","label-a","positive")],[target],[binding],grouping,p,
        independence_evidence=[independence_for(definition.model_id,definition.model_version,"label-a")],protected_artifact_handoff=handoff)
    assert result.readiness.state=="INSUFFICIENT_EVIDENCE"
    assert result.readiness.reason_codes==("no_eligible_development_examples","minimum_positive_outcomes_not_met")
    assert len(handoff.artifact.rows)==1
    assert not result.development.train and not result.development.validation and not result.development.calibration
