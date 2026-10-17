from dataclasses import replace
from safira.collection import CollectionAssociation, EvidenceItem, collect_live
from safira.dataset import DatasetBuilder, IndependenceVerification, LinkageVerification, OutcomeVerification
from tests.dataset_fixtures import target_and_binding, outcome, linkage, protocol, independence_for
from tests.test_dataset_protection import Verifier


def test_protocol_adequacy_counts_only_development_rows_and_groups(registered_collection):
    registry,register=registered_collection
    definition,_=register(labels=("label-a",),scores=(.2,))
    record=collect_live(registry,CollectionAssociation("p","a","o"),[(definition.model_id,definition.model_version,"label-a")],{"synthetic-feature":[.2]}).records[0]
    target,binding=target_and_binding(definition.model_id,definition.model_version,"label-a")
    p=protocol({"g":"train"})
    p=type(p)(**{**p.__dict__,"adequacy_criteria":{"minimum_examples":2,"minimum_patient_groups":2},"permitted_summaries":("row_count",)})
    result=DatasetBuilder(registry,Verifier()).build([record],[outcome("p","a","label-a","positive")],[target],[binding],linkage({("unknown","p"):"g"}),p,
        independence_evidence=[independence_for(definition.model_id,definition.model_version,"label-a")])
    assert result.readiness.state=="INSUFFICIENT_EVIDENCE"
    assert result.readiness.reason_codes==("minimum_examples_not_met","minimum_patient_groups_not_met")
    assert result.summary=={"example_count":1}


def test_label_modality_imbalance_and_missing_protocol_criteria_are_scoped(registered_collection):
    registry,register=registered_collection
    definition,_=register(labels=("label-a",),scores=(.2,))
    association=CollectionAssociation("p","a","o")
    record=collect_live(registry,association,[(definition.model_id,definition.model_version,"label-a")],{"synthetic-feature":[.2]}).records[0]
    availability=EvidenceItem(association,record.source_key,"available_modalities","available",["image"])
    record=replace(record,evidence=record.evidence+(availability,))
    target,binding=target_and_binding(definition.model_id,definition.model_version,"label-a")
    grouping=linkage({("unknown","p"):"g"})
    criteria={"required_labels":["label-b"],"required_modalities":["image","text"],"maximum_outcome_imbalance_ratio":1.5}
    p=protocol({"g":"train"}); p=type(p)(**{**p.__dict__,"adequacy_criteria":criteria})
    result=DatasetBuilder(registry,Verifier()).build([record],[outcome("p","a","label-a","positive")],[target],[binding],grouping,p,
        independence_evidence=[independence_for(definition.model_id,definition.model_version,"label-a")])
    assert result.readiness.state=="INSUFFICIENT_EVIDENCE"
    assert {"required_label_missing","required_modality_missing","outcome_imbalance_not_met"}.issubset(result.readiness.reason_codes)
    assert len(result.development.train)==1


def test_protocol_can_require_explicit_adequacy_criteria(registered_collection):
    registry,register=registered_collection
    definition,_=register(labels=("label-a",),scores=(.2,))
    record=collect_live(registry,CollectionAssociation("p","a","o"),[(definition.model_id,definition.model_version,"label-a")],{"synthetic-feature":[.2]}).records[0]
    target,binding=target_and_binding(definition.model_id,definition.model_version,"label-a")
    p=protocol({"g":"train"}); p=type(p)(**{**p.__dict__,"require_adequacy_criteria":True})
    result=DatasetBuilder(registry,Verifier()).build([record],[outcome("p","a","label-a","positive")],[target],[binding],linkage({("unknown","p"):"g"}),p,
        independence_evidence=[independence_for(definition.model_id,definition.model_version,"label-a")])
    assert result.readiness.state=="NOT_READY"
    assert result.readiness.reason_codes==("adequacy_criteria_required",)
