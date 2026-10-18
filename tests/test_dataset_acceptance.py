from dataclasses import replace

from safira.collection import CollectionAssociation, EvidenceItem, collect_live
from safira.dataset import (
    DatasetBuilder, IndependenceVerification, LinkageVerification,
    OutcomeVerification,
)
from tests.dataset_fixtures import target_and_binding, outcome, linkage, protocol, independence_for
from collection_fixtures import SyntheticSourceContract, SyntheticTrustedVerifier
from safira.collection import ComponentContribution, PrecomputedCollector, TrustedSourceIntegration
from safira import AdapterCapabilities, ModelAdapter, SafetyAssessment, SafetyContext


class Verifier:
    def verify_prediction_admission(self, prediction):
        from safira.dataset import PredictionAdmissionVerification
        from safira.dataset.verification import prediction_fingerprint
        return PredictionAdmissionVerification(prediction_fingerprint(prediction),prediction.source_key,
            prediction.association,prediction.provenance.mode,"verified","synthetic ledger","exact fixture lookup","admission-check")
    def verify_linkage(self, declaration, candidate_patient_refs, protocol):
        return LinkageVerification(declaration.linkage_id,declaration.linkage_version,declaration.scope,"verified","fixture","ledger","link-check",declaration.entries,tuple(candidate_patient_refs))
    def verify_outcome(self, outcome, prediction, target, binding):
        return OutcomeVerification(outcome.content_ref,outcome.source_contract_id,outcome.source_contract_version,
            outcome.patient_ref,outcome.assessment_ref,outcome.label_id,outcome.target_id,outcome.target_version,
            "verified","fixture","ledger","outcome-check",source_namespace=outcome.source_namespace,source_record_ref=outcome.source_record_ref)
    def verify_independence(self, prediction, metadata, evidence, protocol):
        return IndependenceVerification(prediction.model_id,prediction.model_version,prediction.label_id,
            evidence.target_id,evidence.target_version,"eligible","fixture","ledger","independence-check",evidence.development_source_ref,evidence.lineage_ref)


def test_live_records_join_by_exact_registered_class_without_reinference(registered_collection):
    registry, register=registered_collection
    definition,adapter=register(labels=("label-a",),scores=(.2,))
    association=CollectionAssociation("opaque-patient","assessment","occurrence")
    record=collect_live(registry,association,[(definition.model_id,definition.model_version,"label-a")],{"synthetic-feature":[.3]}).records[0]
    states=("available","unsupported","missing","unavailable","invalid")
    evidence=tuple(EvidenceItem(association,record.source_key,"synthetic-"+state,state,
        value={"synthetic":1} if state=="available" else None) for state in states)
    record=replace(record,evidence=evidence)
    adapter.calls.clear()
    target,binding=target_and_binding(definition.model_id,definition.model_version,"label-a")
    declaration=linkage({("unknown","opaque-patient"):"opaque-group"})
    result=DatasetBuilder(registry,Verifier()).build(
        [record],[outcome("opaque-patient","assessment","label-a","positive")],[target],[binding],declaration,
        protocol({"opaque-group":"train"}),
        independence_evidence=[independence_for(definition.model_id,definition.model_version,"label-a")])
    assert result.readiness.state=="ready"
    assert result.development.train[0].correctness_target==0
    assert tuple(item.state for item in result.development.train[0].prediction.evidence)==states
    assert adapter.calls==[]
    assert registry.get_metadata(definition.model_id,definition.model_version)==definition
    assert isinstance(adapter,ModelAdapter)
    assert isinstance(adapter.capabilities,AdapterCapabilities)
    assert SafetyContext.__module__.startswith("safira.context")
    assert SafetyAssessment.__module__.startswith("safira.models")
    assert "protected_test" not in repr(result.to_dict())


def test_multilabel_and_independent_overlapping_contributors_remain_distinct(registered_collection):
    registry,register=registered_collection
    first,adapter_a=register(labels=("label-a","label-b"),scores=(.8,.2),model_id="model-a")
    second,adapter_b=register(labels=("label-a",),scores=(.2,),model_id="model-b")
    association=CollectionAssociation("patient","assessment","occurrence")
    records=[]
    for definition,labels in ((first,("label-a","label-b")),(second,("label-a",))):
        records.extend(collect_live(registry,association,[(definition.model_id,definition.model_version,label) for label in labels],{"synthetic-feature":[.4]}).records)
    adapter_a.calls.clear(); adapter_b.calls.clear()
    targets=[]; bindings=[]; independent=[]
    for definition,labels in ((first,("label-a","label-b")),(second,("label-a",))):
        for label in labels:
            target,binding=target_and_binding(definition.model_id,definition.model_version,label)
            if not targets: targets.append(target)
            bindings.append(binding); independent.append(independence_for(definition.model_id,definition.model_version,label))
    declaration=linkage({("unknown","patient"):"group"})
    result=DatasetBuilder(registry,Verifier()).build(records,[outcome("patient","assessment","label-a","positive"),outcome("patient","assessment","label-b","negative")],targets,bindings,declaration,
        protocol({"group":"train"}),independence_evidence=independent)
    assert len(result.development.train)==3
    same_label=[row.prediction.source_key for row in result.development.train if row.prediction.label_id=="label-a"]
    assert set(same_label)=={("model-a","v1","label-a"),("model-b","v1","label-a")}
    assert result.development.train[0].prediction.evidence
    assert adapter_a.calls==[] and adapter_b.calls==[]


def test_trusted_precomputed_feature002_record_is_consumed_without_prediction(registered_collection):
    import json
    registry,register=registered_collection
    definition,adapter=register(model_id="precomputed-model",scores=(.8,))
    contract=SyntheticSourceContract("flat","v1","flat"); verifier=SyntheticTrustedVerifier()
    integration=TrustedSourceIntegration(contract,verifier)
    collector=PrecomputedCollector(registry,[integration])
    association=CollectionAssociation("p","a","o")
    contribution=ComponentContribution("flat","v1","external-a","precomputed-model","v1","label-a",0)
    raw=json.dumps({"schema":"v1","selector":"external-a","value":.8,"event":"evt"})
    verifier.add("evt",raw,contract.parse(raw).outputs[0],contribution,association)
    record=collector.ingest(association,("flat","v1"),raw,[contribution]).records[0]
    adapter.calls.clear()
    target,binding=target_and_binding("precomputed-model","v1","label-a")
    result=DatasetBuilder(registry,Verifier()).build([record],[outcome("p","a","label-a","positive")],[target],[binding],
        linkage({("flat","p"):"g"}),protocol({"g":"train"}),independence_evidence=[independence_for("precomputed-model","v1","label-a")])
    assert result.readiness.state=="ready"
    assert result.development.train[0].correctness_target==1
    assert adapter.calls==[]
