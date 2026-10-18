import pytest
from types import SimpleNamespace

from safira.dataset import (
    DatasetProtocolError, DatasetVerificationFailed, EvaluationProtocol, LinkageVerification,
    PatientGroupingConflict, PriorAssignmentManifest, PriorHistoryVerification,
)
from safira.dataset.partitioning import assign_groups, check_prior_history, deduplicate, resolve_groups
import safira.dataset.partitioning as partitioning
from tests.dataset_fixtures import linkage, protocol


class Record:
    def __init__(self, namespace, patient, assessment="a", occurrence="o", model="m", version="v1", label="l", score=.5):
        self.provenance=type("P",(),{"details":{"source_namespace":namespace}})()
        self.association=type("A",(),{"patient_ref":patient,"assessment_ref":assessment,"occurrence_ref":occurrence})()
        self.model_id=model; self.model_version=version; self.label_id=label
        self.source_key=(model,version,label)
        self.value=score
    def to_dict(self): return {"key":self.source_key,"association":(self.association.patient_ref,self.association.assessment_ref,self.association.occurrence_ref),"value":self.value}


def test_linkage_requires_exact_namespace_alias_and_groups_related_sources():
    records=(Record("s1","a"),Record("s2","b"))
    declaration=linkage({("s1","a"):"g",("s2","b"):"g"})
    assert set(resolve_groups(records,declaration).values())=={"g"}
    with pytest.raises(PatientGroupingConflict): resolve_groups(records,linkage({("s1","a"):"g"}))


def test_duplicates_are_removed_but_conflicting_copies_fail():
    record=Record("s","p")
    assert len(deduplicate((record,record)))==1
    with pytest.raises(PatientGroupingConflict): deduplicate((record,Record("s","p",score=.9)))
    assert len(deduplicate((record,Record("s","p",assessment="a2",occurrence="o2"))))==2


def test_supplied_and_seeded_allocations_are_group_scoped_and_repeatable():
    supplied=protocol({"g1":"train","g2":"validation"})
    assert assign_groups({"g1","g2"},supplied)=={"g1":"train","g2":"validation"}
    p=EvaluationProtocol("p","v1","t","v1",partition_mode="deterministic",seed="seed-a",
        algorithm_version="hash-v1",allocation_order=("train","validation","calibration","protected_test"))
    groups={f"group-{i}" for i in range(20)}
    first=assign_groups(groups,p)
    assert first==assign_groups(set(reversed(sorted(groups))),p)
    changed=EvaluationProtocol("p","v1","t","v1",partition_mode="deterministic",seed="seed-b",
        algorithm_version="hash-v1",allocation_order=p.allocation_order)
    assert first!=assign_groups(groups,changed)


def test_prior_completeness_flag_or_digest_is_not_verification():
    manifest=PriorAssignmentManifest("m","v1","custodian","source","scope",{"g":"protected_test"},("g",),True)
    class Verifier:
        def verify_prior_history(self,*args):
            return PriorHistoryVerification("m","v1","custodian","source",args[1],"scope","unverifiable",protected_membership=("g",))
    p=EvaluationProtocol("p","v1","t","v1",require_prior_history=True)
    assert check_prior_history(Verifier(),(manifest,),"scope",p) is None
    assert check_prior_history(Verifier(),(),"scope",p) is None
    assert manifest.complete is True


def test_prior_check_must_bind_scope_completeness_and_protected_membership():
    manifest=PriorAssignmentManifest("m","v1","custodian","source","scope",{"g":"protected_test"},("g",),True)
    class Verifier:
        def verify_prior_history(self,prior,requested,protocol):
            return PriorHistoryVerification(prior.manifest_id,prior.content_version,prior.origin,prior.source_id,requested,
                prior.scope,"verified_complete","custodian-history",prior.protected_membership,"authority","method","evidence")
    p=EvaluationProtocol("p","v1","t","v1",require_prior_history=True)
    assert check_prior_history(Verifier(),(manifest,),"scope",p)=={"g"}


def test_verified_protected_membership_must_match_prior_assignment():
    manifest=PriorAssignmentManifest("m","v1","custodian","source","scope",{"g":"train"},("g",),True)
    class Verifier:
        def verify_prior_history(self,prior,requested,protocol):
            return PriorHistoryVerification(prior.manifest_id,prior.content_version,prior.origin,prior.source_id,requested,
                prior.scope,"verified_complete","custodian-history",prior.protected_membership,"authority","method","evidence")
    p=EvaluationProtocol("p","v1","t","v1",require_prior_history=True)
    assert check_prior_history(Verifier(),(manifest,),"scope",p) is None


def test_all_four_roles_are_explicit_at_patient_group_level():
    allocation={"g1":"train","g2":"validation","g3":"calibration","g4":"protected_test"}
    records=(Record("s1","a"),Record("s2","b"),Record("s1","a",assessment="a2",occurrence="o2"),
             Record("s3","c"),Record("s4","d"))
    declaration=linkage({("s1","a"):"g1",("s2","b"):"g1",("s3","c"):"g2",("s4","d"):"g3"})
    resolved=resolve_groups(records,declaration)
    assert resolved[("s1","a")]==resolved[("s2","b")]
    result=assign_groups(set(allocation),protocol(allocation))
    assert result==allocation
    assert result[resolved[("s1","a")]]=="train"


def test_seeded_assignment_uses_one_hash_per_group_and_does_not_search(monkeypatch):
    real_hash=partitioning.sha256
    calls=[]
    def counted(value):
        calls.append(value)
        return real_hash(value)
    monkeypatch.setattr(partitioning,"sha256",counted)
    p=EvaluationProtocol("p","v1","t","v1",partition_mode="deterministic",seed="approved-seed",
        algorithm_version="hash-v1",allocation_order=("train","validation","calibration","protected_test"))
    groups={"g-a","g-b","g-c","g-d"}
    result=assign_groups(groups,p)
    assert len(calls)==len(groups)
    assert set(result)==groups
    assert all(value.startswith(b"approved-seed\0") for value in calls)


def test_unsupported_hard_constraints_fail_without_trying_other_assignments(monkeypatch):
    calls=[]
    monkeypatch.setattr(partitioning,"sha256",lambda value: calls.append(value))
    p=EvaluationProtocol("p","v1","t","v1",partition_mode="deterministic",seed="approved-seed",
        algorithm_version="hash-v1",allocation_order=("train","validation","calibration","protected_test"),
        hard_constraints={"invented_rule":"required"})
    with pytest.raises(DatasetProtocolError): assign_groups({"g"},p)
    assert calls==[]


@pytest.mark.parametrize("change",["manifest_id","content_version","origin","source_id","declared_scope","state","coverage","membership"])
def test_prior_verification_must_bind_every_protection_dimension(change):
    manifest=PriorAssignmentManifest("m","v1","custodian","source","scope",{"g":"protected_test"},("g",),True)
    class Verifier:
        def verify_prior_history(self,prior,requested,protocol):
            values=dict(manifest_id=prior.manifest_id,content_version=prior.content_version,origin=prior.origin,
                source_id=prior.source_id,requested_scope=requested,declared_scope=prior.scope,state="verified_complete",
                completeness_evidence_ref="custodian-history",protected_membership=prior.protected_membership)
            key="protected_membership" if change=="membership" else change
            if key in values: values[key]=("other",) if key=="protected_membership" else "wrong-value"
            if change=="coverage": values["completeness_evidence_ref"]=""
            return PriorHistoryVerification(**values)
    p=EvaluationProtocol("p","v1","t","v1",require_prior_history=True)
    assert check_prior_history(Verifier(),(manifest,),"scope",p) is None


@pytest.mark.parametrize("state",["partial","unavailable","stale","conflict","unverifiable"])
def test_noncomplete_prior_states_never_support_cross_version_claim(state):
    manifest=PriorAssignmentManifest("m","v1","custodian","source","scope",{"g":"protected_test"},("g",),True)
    class Verifier:
        def verify_prior_history(self,prior,requested,protocol):
            return PriorHistoryVerification(prior.manifest_id,prior.content_version,prior.origin,prior.source_id,requested,
                prior.scope,state,"",prior.protected_membership)
    p=EvaluationProtocol("p","v1","t","v1",require_prior_history=True)
    assert check_prior_history(Verifier(),(manifest,),"scope",p) is None


def test_linkage_result_must_match_declaration_scope():
    from safira.dataset import LinkageVerification
    from safira.dataset.verification import validate_linkage_check
    declaration=linkage({("s","p"):"g"})
    with pytest.raises(DatasetVerificationFailed):
        validate_linkage_check(LinkageVerification(declaration.linkage_id,declaration.linkage_version,"other","verified"),declaration,(("s","p"),))


def test_linkage_verification_binds_exact_alias_map_and_candidate_scope():
    from safira.dataset import LinkageVerification
    from safira.dataset.verification import validate_linkage_check
    declaration=linkage({("s","p"):"group-a"})
    valid=LinkageVerification(declaration.linkage_id,declaration.linkage_version,declaration.scope,"verified","authority","method","evidence",declaration.entries,(("s","p"),))
    validate_linkage_check(valid,declaration,(("s","p"),))
    wrong=LinkageVerification(declaration.linkage_id,declaration.linkage_version,declaration.scope,"verified","authority","method","evidence",{("s","p"):"group-b"},(("s","p"),))
    with pytest.raises(DatasetVerificationFailed): validate_linkage_check(wrong,declaration,(("s","p"),))

