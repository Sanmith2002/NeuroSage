"""Immutable supplemental values for Feature 003.

The records deliberately carry opaque references only. They do not verify the
truth of any source; verifier results are accepted only from injected code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any
from math import isfinite

from .exceptions import InvalidDatasetInput


def _freeze(v: Any, ancestors: frozenset[int] = frozenset()) -> Any:
    try:
        if v is None or type(v) in (str, bool, int): return v
        if type(v) is float:
            if not isfinite(v): raise InvalidDatasetInput("invalid_number")
            return v
        if isinstance(v, (Mapping,tuple,list)):
            if id(v) in ancestors: raise InvalidDatasetInput("cyclic_value")
            ancestors=ancestors|{id(v)}
            if isinstance(v, Mapping):
                if any(type(k) is not str and not (isinstance(k, tuple) and all(type(part) is str for part in k)) for k in v):
                    raise InvalidDatasetInput("invalid_mapping")
                return MappingProxyType({k:_freeze(x,ancestors) for k,x in v.items()})
            return tuple(_freeze(x,ancestors) for x in v)
        raise InvalidDatasetInput("invalid_value")
    except InvalidDatasetInput:
        raise
    except Exception:
        raise InvalidDatasetInput("invalid_value") from None


def _thaw(v: Any) -> Any:
    if isinstance(v, Mapping):
        return {k: _thaw(x) for k, x in v.items()}
    if isinstance(v, tuple):
        return [_thaw(x) for x in v]
    return v


def _text(v: str, field_name: str) -> None:
    if type(v) is not str or not v.strip() or v != v.strip():
        raise InvalidDatasetInput(field_name)


@dataclass(frozen=True)
class TargetDefinition:
    target_id: str
    target_version: str
    positive_meaning: str
    negative_meaning: str
    population_scope: str = ""
    observation_window: str = ""
    outcome_coding: Mapping[str, int] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        for x in (self.target_id, self.target_version, self.positive_meaning, self.negative_meaning): _text(x, "target")
        coding = dict(self.outcome_coding) or {self.positive_meaning: 1, self.negative_meaning: 0}
        if len(coding) != 2 or set(coding.values()) != {0, 1} or any(type(x) is not int for x in coding.values()):
            raise InvalidDatasetInput("target_coding")
        object.__setattr__(self, "outcome_coding", _freeze(coding)); object.__setattr__(self, "provenance", _freeze(self.provenance))


@dataclass(frozen=True)
class TargetBinding:
    target_id: str
    target_version: str
    model_id: str
    model_version: str
    label_id: str
    target_positive_to_label_class: str
    target_negative_to_label_class: str
    scope_compatibility: str = ""
    def __post_init__(self):
        for x in (self.target_id,self.target_version,self.model_id,self.model_version,self.label_id,self.target_positive_to_label_class,self.target_negative_to_label_class): _text(x,"binding")
        if self.target_positive_to_label_class == self.target_negative_to_label_class: raise InvalidDatasetInput("binding_classes")
    @property
    def source_key(self): return self.model_id,self.model_version,self.label_id


@dataclass(frozen=True)
class OutcomeCandidate:
    source_namespace: str
    source_record_ref: str
    patient_ref: str
    assessment_ref: str
    label_id: str
    target_id: str
    target_version: str
    outcome_value: Any
    observed_at: str = ""
    source_contract_id: str = ""
    source_contract_version: str = ""
    content_ref: str = ""
    def __post_init__(self):
        for name in ("source_namespace","source_record_ref","patient_ref","assessment_ref","label_id","target_id","target_version"):
            _text(getattr(self,name),name)
        object.__setattr__(self,"outcome_value",_freeze(self.outcome_value))


@dataclass(frozen=True)
class OutcomeVerification:
    content_ref: str
    source_contract_id: str
    source_contract_version: str
    patient_ref: str
    assessment_ref: str
    label_id: str
    target_id: str
    target_version: str
    state: str
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""
    checked_at: str = ""
    reason_code: str = ""
    source_namespace: str = ""
    source_record_ref: str = ""


@dataclass(frozen=True)
class IndependenceEvidence:
    model_id: str
    model_version: str
    label_id: str
    target_id: str
    target_version: str
    development_source_ref: str = ""
    lineage_ref: str = ""
    def __post_init__(self):
        for name in ("model_id","model_version","label_id","target_id","target_version"):_text(getattr(self,name),name)


@dataclass(frozen=True)
class IndependenceVerification:
    model_id: str
    model_version: str
    label_id: str
    target_id: str
    target_version: str
    state: str
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""
    development_source_ref: str = ""
    lineage_ref: str = ""


@dataclass(frozen=True)
class PredictionAdmissionVerification:
    """Trusted check that one exact Feature 002 record was admitted by its source."""

    record_fingerprint: str
    source_key: tuple[str, str, str]
    association: Any
    provenance_mode: str
    state: str
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""

    def __post_init__(self):
        _text(self.record_fingerprint, "prediction_admission_fingerprint")
        if not isinstance(self.source_key, (tuple, list)) or len(self.source_key) != 3:
            raise InvalidDatasetInput("prediction_admission_scope")
        object.__setattr__(self, "source_key", tuple(self.source_key))


@dataclass(frozen=True)
class EvidenceTimingDeclaration:
    source_key: tuple[str,str,str]
    occurrence_ref: str
    category: str
    available_at: str
    state: str
    source_ref: str = ""
    def __post_init__(self):
        if not isinstance(self.source_key,(tuple,list)) or len(self.source_key)!=3: raise InvalidDatasetInput("timing_scope")
        object.__setattr__(self,"source_key",tuple(self.source_key))
        for name in ("occurrence_ref","category","available_at","state"):_text(getattr(self,name),name)
        if self.state not in ("verified","unavailable","conflict"): raise InvalidDatasetInput("timing_state")


@dataclass(frozen=True)
class TimingVerification:
    source_key: tuple[str,str,str]
    occurrence_ref: str
    category: str
    available_at: str
    state: str
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""


@dataclass(frozen=True)
class TransformationDeclaration:
    transform_id: str
    transform_version: str
    source_key: tuple[str,str,str]
    preprocessing_identity: str
    fitted_on_groups: tuple[str,...] = ()
    evidence_ref: str = ""
    def __post_init__(self):
        for name in ("transform_id","transform_version","preprocessing_identity"):_text(getattr(self,name),name)
        object.__setattr__(self,"source_key",tuple(self.source_key)); object.__setattr__(self,"fitted_on_groups",tuple(self.fitted_on_groups))


@dataclass(frozen=True)
class TransformationVerification:
    transform_id: str
    transform_version: str
    source_key: tuple[str,str,str]
    state: str
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""


@dataclass(frozen=True)
class PatientLinkageDeclaration:
    linkage_id: str
    linkage_version: str
    source_id: str
    scope: str
    evidence_ref: str
    entries: Mapping[tuple[str,str],str]
    def __post_init__(self):
        for name in ("linkage_id","linkage_version","source_id","scope","evidence_ref"):_text(getattr(self,name),name)
        normalized = {}
        for key, group in self.entries.items():
            if not isinstance(key,(tuple,list)) or len(key)!=2: raise InvalidDatasetInput("linkage_entry")
            if any(type(x) is not str or not x for x in key) or type(group) is not str or not group: raise InvalidDatasetInput("linkage_entry")
            normalized[tuple(key)] = group
        object.__setattr__(self,"entries",_freeze(normalized))


@dataclass(frozen=True)
class LinkageVerification:
    linkage_id: str
    linkage_version: str
    scope: str
    state: str
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""
    checked_entries: Mapping[tuple[str,str],str] = field(default_factory=dict)
    checked_aliases: tuple[tuple[str,str],...] = ()
    def __post_init__(self):
        object.__setattr__(self,"checked_entries",_freeze(self.checked_entries))
        object.__setattr__(self,"checked_aliases",tuple(tuple(alias) for alias in self.checked_aliases))


@dataclass(frozen=True)
class PriorAssignmentManifest:
    manifest_id: str
    content_version: str
    origin: str
    source_id: str
    scope: str
    assignments: Mapping[str,str]
    protected_membership: tuple[str,...] = ()
    complete: bool = False
    def __post_init__(self):
        for name in ("manifest_id","content_version","origin","source_id","scope"):_text(getattr(self,name),name)
        if any(role not in ("train","validation","calibration","protected_test") for role in self.assignments.values()): raise InvalidDatasetInput("prior_assignment")
        object.__setattr__(self,"assignments",_freeze(self.assignments)); object.__setattr__(self,"protected_membership",tuple(self.protected_membership))


@dataclass(frozen=True)
class PriorHistoryVerification:
    manifest_id: str
    content_version: str
    origin: str
    source_id: str
    requested_scope: str
    declared_scope: str
    state: str
    completeness_evidence_ref: str = ""
    protected_membership: tuple[str,...] = ()
    authority: str = ""
    method: str = ""
    evidence_ref: str = ""

    def __post_init__(self):
        for name in ("manifest_id", "content_version", "origin", "source_id", "requested_scope", "declared_scope", "state"):
            _text(getattr(self, name), "prior_history_" + name)
        membership = tuple(self.protected_membership)
        if any(type(group) is not str or not group for group in membership):
            raise InvalidDatasetInput("prior_history_membership")
        object.__setattr__(self, "protected_membership", membership)


@dataclass(frozen=True)
class EvaluationProtocol:
    protocol_id: str
    protocol_version: str
    target_id: str
    target_version: str
    partition_mode: str = "supplied"
    roles: tuple[str,...] = ("train","validation","calibration","protected_test")
    assignments: Mapping[str,str] = field(default_factory=dict)
    seed: str = ""
    algorithm_version: str = ""
    allocation_order: tuple[str,...] = ()
    allowed_strata: tuple[str,...] = ()
    hard_constraints: Mapping[str,Any] = field(default_factory=dict)
    require_prior_history: bool = False
    require_protected_handoff: bool = False
    required_timing_categories: tuple[str,...] = ()
    require_transform_declarations: bool = False
    require_adequacy_criteria: bool = False
    adequacy_criteria: Mapping[str,Any] = field(default_factory=dict)
    adequacy_by_source: Mapping[tuple[str, str, str], Mapping[str, Any]] = field(default_factory=dict)
    permitted_summaries: tuple[str,...] = ("row_count","group_count")
    def __post_init__(self):
        if self.partition_mode not in ("supplied","deterministic"): raise InvalidDatasetInput("partition_mode")
        if len(self.roles)!=4 or set(self.roles) != {"train","validation","calibration","protected_test"}: raise InvalidDatasetInput("partition_roles")
        allowed_criteria={"minimum_examples","minimum_patient_groups","minimum_positive_outcomes","minimum_negative_outcomes","minimum_incorrect_predictions","minimum_correct_predictions","minimum_examples_per_label","minimum_positive_outcomes_per_label","minimum_negative_outcomes_per_label","minimum_correct_predictions_per_label","minimum_incorrect_predictions_per_label","minimum_groups_per_label","required_labels","required_modalities","maximum_outcome_imbalance_ratio"}
        if set(self.adequacy_criteria)-allowed_criteria: raise InvalidDatasetInput("adequacy_criteria")
        for key,value in self.adequacy_criteria.items():
            if key in ("required_labels","required_modalities"):
                if not isinstance(value,(tuple,list)) or any(type(item) is not str or not item for item in value): raise InvalidDatasetInput("adequacy_criteria")
            elif key=="maximum_outcome_imbalance_ratio":
                if type(value) not in (int,float) or value<1 or not isfinite(value): raise InvalidDatasetInput("adequacy_criteria")
            elif type(value) is not int or value<0: raise InvalidDatasetInput("adequacy_criteria")
        scoped_allowed = allowed_criteria - {"required_labels", "required_modalities"}
        for scope, scoped in self.adequacy_by_source.items():
            if not isinstance(scope, (tuple, list)) or len(scope) != 3 or any(type(x) is not str or not x for x in scope):
                raise InvalidDatasetInput("adequacy_scope")
            if not isinstance(scoped, Mapping) or set(scoped) - scoped_allowed:
                raise InvalidDatasetInput("adequacy_scope")
            for key,value in scoped.items():
                if key == "maximum_outcome_imbalance_ratio":
                    if type(value) not in (int,float) or value < 1 or not isfinite(value):
                        raise InvalidDatasetInput("adequacy_scope")
                elif type(value) is not int or value < 0:
                    raise InvalidDatasetInput("adequacy_scope")
        object.__setattr__(self,"assignments",_freeze(self.assignments)); object.__setattr__(self,"hard_constraints",_freeze(self.hard_constraints)); object.__setattr__(self,"adequacy_criteria",_freeze(self.adequacy_criteria)); object.__setattr__(self,"adequacy_by_source",_freeze(self.adequacy_by_source))
        for name in ("roles","allocation_order","allowed_strata","permitted_summaries","required_timing_categories"):
            object.__setattr__(self,name,tuple(getattr(self,name)))


@dataclass(frozen=True)
class CorrectnessExample:
    prediction: Any
    target_id: str
    target_version: str
    outcome: int
    correctness_target: int
    patient_group_ref: str
    partition_role: str = ""
    verification_ref: str = ""
    independence_ref: str = ""
    def __post_init__(self):
        if type(self.outcome) is not int or self.outcome not in (0,1) or type(self.correctness_target) is not int or self.correctness_target not in (0,1): raise InvalidDatasetInput("binary_target")
        if self.partition_role not in ("","train","validation","calibration","protected_test"): raise InvalidDatasetInput("partition_role")
    def to_dict(self):
        return {"prediction":self.prediction.to_dict(),"target_id":self.target_id,"target_version":self.target_version,"outcome":self.outcome,"correctness_target":self.correctness_target,"patient_group_ref":self.patient_group_ref,"partition_role":self.partition_role,"verification_ref":self.verification_ref,"independence_ref":self.independence_ref}


@dataclass(frozen=True)
class ExclusionRecord:
    source_ref: str
    reason_code: str
    stage: str
    def __post_init__(self):
        for name in ("source_ref","reason_code","stage"):_text(getattr(self,name),name)


@dataclass(frozen=True)
class DatasetReadiness:
    state: str
    reason_codes: tuple[str,...] = ()
    scope: str = ""
    def __post_init__(self):
        if self.state not in ("ready","NOT_READY","INSUFFICIENT_EVIDENCE"): raise InvalidDatasetInput("readiness_state")
        object.__setattr__(self,"reason_codes",tuple(self.reason_codes))


@dataclass(frozen=True)
class PartitionedDataset:
    train: tuple[CorrectnessExample,...] = ()
    validation: tuple[CorrectnessExample,...] = ()
    calibration: tuple[CorrectnessExample,...] = ()
    def __post_init__(self):
        for name in ("train","validation","calibration"): object.__setattr__(self,name,tuple(getattr(self,name)))
    def to_dict(self): return {"train":[x.to_dict() for x in self.train],"validation":[x.to_dict() for x in self.validation],"calibration":[x.to_dict() for x in self.calibration]}


@dataclass(frozen=True)
class ProtectedTestArtifact:
    rows: tuple[CorrectnessExample,...]
    def __post_init__(self): object.__setattr__(self,"rows",tuple(self.rows))


@dataclass(frozen=True)
class ProtectedArtifactReceipt:
    status: str
    receipt_ref: str = ""
    def __post_init__(self):
        if self.status not in ("accepted","unavailable","rejected"): raise InvalidDatasetInput("receipt_status")


@dataclass(frozen=True)
class DatasetManifestReceipt:
    status: str
    receipt_ref: str = ""
    def __post_init__(self):
        if self.status not in ("accepted", "unavailable", "rejected"):
            raise InvalidDatasetInput("manifest_receipt_status")
        if self.status == "accepted":
            _text(self.receipt_ref, "manifest_receipt_ref")


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    protocol_id: str
    protocol_version: str
    builder_version: str
    assignments: Mapping[str,str]
    source_refs: tuple[str,...] = ()
    exclusions: tuple[ExclusionRecord,...] = ()
    metadata: Mapping[str,Any] = field(default_factory=dict)
    digest: str = ""
    def __post_init__(self):
        for name in ("dataset_id","protocol_id","protocol_version","builder_version"):_text(getattr(self,name),name)
        if any(role not in ("train","validation","calibration","protected_test") for role in self.assignments.values()): raise InvalidDatasetInput("manifest_assignment")
        object.__setattr__(self,"assignments",_freeze(self.assignments)); object.__setattr__(self,"metadata",_freeze(self.metadata))
        object.__setattr__(self,"source_refs",tuple(sorted(self.source_refs)))
        object.__setattr__(self,"exclusions",tuple(sorted(self.exclusions,key=lambda x:(x.source_ref,x.reason_code,x.stage))))
        body={"dataset_id":self.dataset_id,"protocol_id":self.protocol_id,"protocol_version":self.protocol_version,"builder_version":self.builder_version,"assignments":_thaw(self.assignments),"source_refs":list(self.source_refs),"exclusions":[{"source_ref":x.source_ref,"reason_code":x.reason_code,"stage":x.stage} for x in self.exclusions],"metadata":_thaw(self.metadata)}
        object.__setattr__(self,"digest",self.digest or sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest())
    def to_dict(self): return {"dataset_id":self.dataset_id,"protocol_id":self.protocol_id,"protocol_version":self.protocol_version,"builder_version":self.builder_version,"assignments":_thaw(self.assignments),"source_refs":list(self.source_refs),"metadata":_thaw(self.metadata),"digest":self.digest}


@dataclass(frozen=True)
class DatasetBuildResult:
    development: PartitionedDataset
    readiness: DatasetReadiness
    exclusions: tuple[ExclusionRecord,...]
    manifest_reference: str
    protected_receipt: ProtectedArtifactReceipt | None = None
    summary: Mapping[str,int] = field(default_factory=dict)
    manifest_receipt: DatasetManifestReceipt | None = None
    def __post_init__(self):
        _text(self.manifest_reference,"manifest_reference")
        object.__setattr__(self,"exclusions",tuple(self.exclusions))
        object.__setattr__(self,"summary",_freeze(self.summary))
    def to_dict(self): return {"development":self.development.to_dict(),"readiness":{"state":self.readiness.state,"reason_codes":list(self.readiness.reason_codes),"scope":self.readiness.scope},"exclusions":[{"source_ref":x.source_ref,"reason_code":x.reason_code,"stage":x.stage} for x in self.exclusions],"manifest_ref":self.manifest_reference,"protected_receipt":None if self.protected_receipt is None else {"status":self.protected_receipt.status,"receipt_ref":self.protected_receipt.receipt_ref},"manifest_receipt":None if self.manifest_receipt is None else {"status":self.manifest_receipt.status,"receipt_ref":self.manifest_receipt.receipt_ref},"summary":_thaw(self.summary)}
