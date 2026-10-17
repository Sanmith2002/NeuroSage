import pytest

from safira.dataset import OutcomeVerification, DatasetVerificationFailed
from safira.dataset.verification import validate_outcome_check
from safira.dataset.verification import validate_independence_check
from safira.dataset import IndependenceEvidence, IndependenceVerification
from types import SimpleNamespace
from tests.dataset_fixtures import outcome, target_and_binding


def test_boolean_or_identifier_cannot_substitute_for_scoped_check():
    candidate=outcome("p","a","label-a",1)
    _,binding=target_and_binding("m","v1","label-a")
    with pytest.raises(DatasetVerificationFailed):
        validate_outcome_check(True,candidate,binding)
    check=OutcomeVerification(candidate.content_ref,candidate.source_contract_id,candidate.source_contract_version,
        candidate.patient_ref,candidate.assessment_ref,candidate.label_id,candidate.target_id,candidate.target_version,
        "verified",authority="fixture",method="ledger",evidence_ref="e",source_namespace=candidate.source_namespace,source_record_ref=candidate.source_record_ref)
    validate_outcome_check(check,candidate,binding)
    mismatched=OutcomeVerification("different",candidate.source_contract_id,candidate.source_contract_version,
        candidate.patient_ref,candidate.assessment_ref,candidate.label_id,candidate.target_id,candidate.target_version,
        "verified",authority="fixture",method="ledger",evidence_ref="e",source_namespace=candidate.source_namespace,source_record_ref=candidate.source_record_ref)
    with pytest.raises(DatasetVerificationFailed): validate_outcome_check(mismatched,candidate,binding)


@pytest.mark.parametrize("state",["overlap","unknown","conflict","unverified"])
def test_model_development_overlap_or_unknown_lineage_is_not_independent(state):
    prediction=SimpleNamespace(model_id="m",model_version="v1",label_id="label-a")
    evidence=IndependenceEvidence("m","v1","label-a","t","v1")
    check=IndependenceVerification("m","v1","label-a","t","v1",state)
    with pytest.raises(DatasetVerificationFailed): validate_independence_check(check,prediction,evidence,None)
