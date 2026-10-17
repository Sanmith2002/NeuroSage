from dataclasses import FrozenInstanceError

import pytest

from safira.dataset import (CorrectnessExample, DatasetManifest, DatasetReadiness, EvaluationProtocol,
    InvalidDatasetInput, OutcomeCandidate, PatientLinkageDeclaration, TargetDefinition)


def test_target_coding_is_binary_and_detached():
    coding={"yes":1,"no":0}
    target=TargetDefinition("t","v1","yes","no",outcome_coding=coding)
    coding["yes"]=0
    assert dict(target.outcome_coding)=={"yes":1,"no":0}
    with pytest.raises(TypeError): target.outcome_coding["yes"]=0
    with pytest.raises(InvalidDatasetInput): TargetDefinition("t","v1","yes","no",outcome_coding={"yes":2,"no":0})


def test_protocol_requires_all_roles():
    with pytest.raises(InvalidDatasetInput):
        EvaluationProtocol("p","v1","t","v1",roles=("train",))


def test_manifest_serialization_is_detached_and_stable():
    assignments={"opaque":"train"}
    manifest=DatasetManifest("d","p","v1","1",assignments)
    assignments["opaque"]="protected_test"
    data=manifest.to_dict(); data["assignments"]["opaque"]="validation"
    assert dict(manifest.assignments)=={"opaque":"train"}
    assert manifest.digest


def test_nested_candidate_and_linkage_values_are_detached():
    nested={"source":["value"]}
    candidate=OutcomeCandidate("source","record","patient","assessment","label","target","v1",nested)
    entries={("source","patient"):"group"}
    declaration=PatientLinkageDeclaration("link","v1","custodian","scope","evidence",entries)
    nested["source"].append("changed")
    entries[("source","patient")]= "other"
    assert candidate.outcome_value["source"]==("value",)
    assert declaration.entries[("source","patient")]=="group"


def test_invalid_readiness_partition_and_binary_codes_fail_privately():
    with pytest.raises(InvalidDatasetInput): DatasetReadiness("maybe",("patient-123 secret",))
    with pytest.raises(InvalidDatasetInput): TargetDefinition("t","v1","yes","no",outcome_coding={"yes":1,"no":True})
    with pytest.raises(InvalidDatasetInput): CorrectnessExample(None,"t","v1",2,1,"g","train")
    with pytest.raises(InvalidDatasetInput) as caught: TargetDefinition("patient-raw","v1","yes","no",outcome_coding={"yes":1})
    assert "patient-raw" not in str(caught.value)


def test_recursive_values_reject_cycles_with_safe_error():
    cyclic=[]; cyclic.append(cyclic)
    with pytest.raises(InvalidDatasetInput) as caught:
        OutcomeCandidate("source","record","patient","assessment","label","target","v1",cyclic)
    assert str(caught.value)=="cyclic_value"
