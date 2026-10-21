"""Immutable, privacy-conscious records for the Feature 007 cohort workflow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
import math
from types import MappingProxyType

from safira.training.records import TrainingScope


def _freeze(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("protocol_value")
        return value
    if isinstance(value, Mapping):
        copied = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("protocol_value")
            copied[key] = _freeze(item)
        return MappingProxyType(copied)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    raise ValueError("protocol_value")


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _text(value, field_name):
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(field_name)
    return value


def canonical_digest(value) -> str:
    return sha256(json.dumps(_plain(value), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class PolicyScope:
    """Exact primary-classifier label scope, including Feature 001 identity."""

    model_id: str
    model_version: str
    label_id: str
    classifier_artifact_sha256: str
    adapter_id: str
    adapter_version: str
    adapter_fingerprint: str
    preprocessing_identity: object

    def __post_init__(self):
        for name in ("model_id", "model_version", "label_id", "adapter_id", "adapter_version"):
            _text(getattr(self, name), name)
        for name in ("classifier_artifact_sha256", "adapter_fingerprint"):
            value = getattr(self, name)
            if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(name)
        object.__setattr__(self, "preprocessing_identity", _freeze(self.preprocessing_identity))

    @property
    def source_key(self):
        return self.model_id, self.model_version, self.label_id

    def to_training_scope(self):
        return TrainingScope(self.model_id, self.model_version, self.label_id,
                             self.classifier_artifact_sha256, self.adapter_id,
                             self.adapter_version, self.adapter_fingerprint,
                             self.preprocessing_identity)

    @classmethod
    def from_training_scope(cls, scope):
        return cls(scope.model_id, scope.model_version, scope.label_id,
                   scope.classifier_artifact_sha256, scope.adapter_id,
                   scope.adapter_version, scope.adapter_fingerprint,
                   scope.preprocessing_identity)

    def to_dict(self):
        return {"model_id": self.model_id, "model_version": self.model_version,
                "label_id": self.label_id,
                "classifier_artifact_sha256": self.classifier_artifact_sha256,
                "adapter_id": self.adapter_id, "adapter_version": self.adapter_version,
                "adapter_fingerprint": self.adapter_fingerprint,
                "preprocessing_identity": _plain(self.preprocessing_identity)}


@dataclass(frozen=True)
class PolicyEvidenceReference:
    dataset_id: str
    protocol_id: str
    protocol_version: str
    manifest_reference: str
    builder_version: str
    manifest_digest: str
    partition: str = "validation"

    def __post_init__(self):
        for name in ("dataset_id", "protocol_id", "protocol_version", "manifest_reference",
                     "builder_version", "manifest_digest"):
            _text(getattr(self, name), name)
        if (self.partition != "validation" or len(self.manifest_digest) != 64
                or any(c not in "0123456789abcdef" for c in self.manifest_digest)):
            raise ValueError("policy_evidence_reference")

    def to_feature003_reference(self):
        from safira.signals.records import Feature003DatasetReference
        return Feature003DatasetReference(self.dataset_id, self.protocol_id,
                                          self.protocol_version, self.manifest_reference,
                                          self.builder_version, self.manifest_digest)

    def to_dict(self):
        return {"dataset_id": self.dataset_id, "protocol_id": self.protocol_id,
                "protocol_version": self.protocol_version,
                "manifest_reference": self.manifest_reference,
                "builder_version": self.builder_version,
                "manifest_digest": self.manifest_digest, "partition": self.partition}


@dataclass(frozen=True)
class PolicySelectionProtocol:
    """All research-critical selection settings must be supplied before outcome access."""

    protocol_id: str
    version: str
    scopes: tuple[PolicyScope, ...]
    policy_evidence: PolicyEvidenceReference
    target_bindings: Mapping[str, tuple[str, str]]
    risk_ceiling: float
    candidate_cutoffs: tuple[float, ...]
    minimum_eligible_patients: int
    minimum_selected_patients: int
    correctness_support: Mapping[int, int]
    comparison: str
    tie_rule: str
    index_rule: str
    approved: bool
    approval_reference: str
    disclose_support: bool = False

    def __post_init__(self):
        _text(self.protocol_id, "protocol_id")
        _text(self.version, "protocol_version")
        scopes = tuple(self.scopes)
        if not scopes or any(type(scope) is not PolicyScope for scope in scopes):
            raise ValueError("protocol_scopes")
        if len({scope.source_key for scope in scopes}) != len(scopes):
            raise ValueError("protocol_scopes")
        if type(self.policy_evidence) is not PolicyEvidenceReference:
            raise ValueError("protocol_evidence")
        bindings = {}
        for scope in scopes:
            key = "\0".join(scope.source_key)
            value = self.target_bindings.get(key) if isinstance(self.target_bindings, Mapping) else None
            if (not isinstance(value, (tuple, list)) or len(value) != 2
                    or any(type(item) is not str or not item.strip() for item in value)):
                raise ValueError("protocol_target_binding")
            bindings[key] = tuple(value)
        if set(self.target_bindings) != set(bindings):
            raise ValueError("protocol_target_binding")
        if type(self.risk_ceiling) not in (int, float) or not math.isfinite(self.risk_ceiling) or not 0 <= self.risk_ceiling <= 1:
            raise ValueError("protocol_risk_ceiling")
        cutoffs = tuple(self.candidate_cutoffs)
        if not cutoffs or any(type(item) not in (int, float) or not math.isfinite(item) or not 0 <= item <= 1 for item in cutoffs):
            raise ValueError("protocol_cutoffs")
        if len(set(cutoffs)) != len(cutoffs):
            raise ValueError("protocol_cutoffs")
        if (type(self.minimum_eligible_patients) is not int or self.minimum_eligible_patients < 1
                or type(self.minimum_selected_patients) is not int or self.minimum_selected_patients < 1):
            raise ValueError("protocol_support")
        support = dict(self.correctness_support)
        if any(type(key) is not int or key not in (0, 1) or type(value) is not int or value < 0
               for key, value in support.items()):
            raise ValueError("protocol_support")
        if self.comparison not in (">=", ">") or self.tie_rule not in ("lowest_cutoff", "highest_cutoff"):
            raise ValueError("protocol_cutoff_rule")
        if self.index_rule != "lexicographic_assessment_ref_v1":
            raise ValueError("protocol_index_rule")
        if self.approved is not True:
            raise ValueError("protocol_not_approved")
        _text(self.approval_reference, "protocol_approval")
        if type(self.disclose_support) is not bool:
            raise ValueError("protocol_disclosure")
        object.__setattr__(self, "scopes", scopes)
        object.__setattr__(self, "candidate_cutoffs", cutoffs)
        object.__setattr__(self, "target_bindings", MappingProxyType(bindings))
        object.__setattr__(self, "correctness_support", MappingProxyType(support))

    def to_dict(self):
        return {"protocol_id": self.protocol_id, "version": self.version,
                "scopes": [scope.to_dict() for scope in self.scopes],
                "policy_evidence": self.policy_evidence.to_dict(),
                "target_bindings": {key: list(value) for key, value in self.target_bindings.items()},
                "risk_ceiling": self.risk_ceiling,
                "candidate_cutoffs": list(self.candidate_cutoffs),
                "minimum_eligible_patients": self.minimum_eligible_patients,
                "minimum_selected_patients": self.minimum_selected_patients,
                "correctness_support": {str(k): v for k, v in self.correctness_support.items()},
                "comparison": self.comparison, "tie_rule": self.tie_rule,
                "index_rule": self.index_rule, "approval_reference": self.approval_reference,
                "disclose_support": self.disclose_support}

    @property
    def digest(self):
        return canonical_digest(self.to_dict())


class PolicyStatus(str, Enum):
    SELECTED_UNEVALUATED = "SELECTED_UNEVALUATED"
    NOT_READY = "NOT_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INVALID_INPUT = "INVALID_INPUT"
    INCOMPATIBLE_INPUT = "INCOMPATIBLE_INPUT"
    NO_FEASIBLE_CUTOFF = "NO_FEASIBLE_CUTOFF"


@dataclass(frozen=True)
class PolicySelectionSummary:
    cutoff: float
    empirical_risk: float
    coverage: float
    selected_patient_count: int
    eligible_patient_count: int
    risk_defined: bool = True

    def __post_init__(self):
        for name in ("cutoff", "empirical_risk", "coverage"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("selection_summary")
            if not 0 <= value <= 1:
                raise ValueError("selection_summary")
        if (type(self.selected_patient_count) is not int or type(self.eligible_patient_count) is not int
                or self.selected_patient_count < 1 or self.eligible_patient_count < self.selected_patient_count
                or self.risk_defined is not True
                or not math.isclose(self.coverage,
                    self.selected_patient_count / self.eligible_patient_count,
                    rel_tol=0.0, abs_tol=1e-12)):
            raise ValueError("selection_summary")

    def to_dict(self):
        return {"cutoff": self.cutoff, "empirical_risk": self.empirical_risk,
                "coverage": self.coverage, "selected_patient_count": self.selected_patient_count,
                "eligible_patient_count": self.eligible_patient_count,
                "risk_defined": self.risk_defined}


@dataclass(frozen=True, repr=False)
class SelectivePolicyArtifact:
    scope: PolicyScope
    protocol_id: str
    protocol_version: str
    protocol_digest: str
    estimator_digest: str
    calibrator_digest: str
    original_dataset_reference: Mapping[str, object]
    original_signal_reference: Mapping[str, object]
    policy_evidence: PolicyEvidenceReference
    selection_configuration: Mapping[str, object]
    selection: PolicySelectionSummary
    selection_evidence_spent: bool = True
    independent_evaluation_complete: bool = False
    protected_test_accessed: bool = False
    deployable: bool = False
    clinical_validity_established: bool = False
    artifact_version: str = "safira-selective-policy-v1"
    digest: str = ""

    def __post_init__(self):
        if type(self.scope) is not PolicyScope or type(self.policy_evidence) is not PolicyEvidenceReference or type(self.selection) is not PolicySelectionSummary:
            raise ValueError("artifact_input")
        for name in ("protocol_id", "protocol_version", "protocol_digest", "estimator_digest", "calibrator_digest", "artifact_version"):
            _text(getattr(self, name), name)
        for name in ("selection_evidence_spent", "protected_test_accessed", "deployable", "clinical_validity_established"):
            if getattr(self, name) is not (name == "selection_evidence_spent"):
                raise ValueError("artifact_lifecycle")
        if self.independent_evaluation_complete is not False:
            raise ValueError("artifact_lifecycle")
        if set(self.original_dataset_reference) != {"dataset_id", "manifest_reference", "manifest_digest",
                "protocol_id", "protocol_version", "builder_version", "dataset_fingerprint",
                "admitted_inventory_digest"}:
            raise ValueError("artifact_dataset_reference")
        if set(self.original_signal_reference) != {"run_version", "feature_set_fingerprint",
                "method_ids", "fitted_state_ids", "scope_key"}:
            raise ValueError("artifact_signal_reference")
        if tuple(self.original_signal_reference["scope_key"]) != self.scope.source_key:
            raise ValueError("artifact_scope")
        for key in ("manifest_digest", "dataset_fingerprint", "admitted_inventory_digest"):
            value = self.original_dataset_reference[key]
            if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("artifact_dataset_digest")
        value = self.original_signal_reference["feature_set_fingerprint"]
        if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("artifact_signal_digest")
        if (not isinstance(self.original_signal_reference["method_ids"], (tuple, list))
                or not isinstance(self.original_signal_reference["fitted_state_ids"], (tuple, list))):
            raise ValueError("artifact_signal_reference")
        expected_configuration = {"risk_ceiling", "candidate_cutoffs", "target_bindings", "minimum_eligible_patients",
            "minimum_selected_patients", "correctness_support", "comparison", "tie_rule",
            "index_rule", "valid_below_cutoff_status", "invalid_input_status"}
        if set(self.selection_configuration) != expected_configuration:
            raise ValueError("artifact_selection_configuration")
        if (self.selection_configuration["valid_below_cutoff_status"] != "CAUTION"
                or self.selection_configuration["invalid_input_status"] != "DEFER"):
            raise ValueError("artifact_status_mapping")
        ceiling = self.selection_configuration["risk_ceiling"]
        candidates = self.selection_configuration["candidate_cutoffs"]
        if (type(ceiling) not in (int, float) or type(ceiling) is bool
                or not math.isfinite(ceiling) or not 0 <= ceiling <= 1
                or not isinstance(candidates, (tuple, list))
                or self.selection.cutoff not in candidates
                or self.selection.empirical_risk > ceiling
                or self.selection.eligible_patient_count < self.selection_configuration["minimum_eligible_patients"]
                or self.selection.selected_patient_count < self.selection_configuration["minimum_selected_patients"]):
            raise ValueError("artifact_selection_inconsistent")
        object.__setattr__(self, "original_dataset_reference", _freeze(self.original_dataset_reference))
        object.__setattr__(self, "original_signal_reference", _freeze(self.original_signal_reference))
        object.__setattr__(self, "selection_configuration", _freeze(self.selection_configuration))
        body = self._body()
        expected = canonical_digest(body)
        if self.digest and self.digest != expected:
            raise ValueError("artifact_digest")
        object.__setattr__(self, "digest", expected)

    def _body(self):
        return {"artifact_version": self.artifact_version, "scope": self.scope.to_dict(),
                "protocol_id": self.protocol_id, "protocol_version": self.protocol_version,
                "protocol_digest": self.protocol_digest, "estimator_digest": self.estimator_digest,
                "calibrator_digest": self.calibrator_digest,
                "original_dataset_reference": _plain(self.original_dataset_reference),
                "original_signal_reference": _plain(self.original_signal_reference),
                "policy_evidence": self.policy_evidence.to_dict(),
                "selection_configuration": _plain(self.selection_configuration),
                "selection": self.selection.to_dict(),
                "selection_evidence_spent": self.selection_evidence_spent,
                "independent_evaluation_complete": self.independent_evaluation_complete,
                "protected_test_accessed": self.protected_test_accessed,
                "deployable": self.deployable,
                "clinical_validity_established": self.clinical_validity_established}

    def to_dict(self):
        return {**self._body(), "digest": self.digest}

    def __repr__(self):
        return (f"SelectivePolicyArtifact(scope={self.scope.source_key!r}, "
                f"status='SELECTED_UNEVALUATED', digest={self.digest[:12]!r})")


@dataclass(frozen=True, repr=False)
class PolicySelectionOutcome:
    scope: PolicyScope
    status: PolicyStatus
    reason_code: str
    artifact: SelectivePolicyArtifact | None = None
    summary: PolicySelectionSummary | None = None

    def __post_init__(self):
        if type(self.scope) is not PolicyScope or type(self.status) is not PolicyStatus:
            raise ValueError("outcome")
        _text(self.reason_code, "reason_code")
        if (self.status is PolicyStatus.SELECTED_UNEVALUATED) != (self.artifact is not None):
            raise ValueError("outcome_artifact")
        if self.artifact is not None and self.artifact.scope != self.scope:
            raise ValueError("outcome_scope")
        if self.artifact is not None and (self.summary != self.artifact.selection
                                          or self.summary is None):
            raise ValueError("outcome_summary")

    def to_dict(self):
        return {"scope": self.scope.to_dict(), "status": self.status.value,
                "reason_code": self.reason_code,
                "artifact": None if self.artifact is None else self.artifact.to_dict(),
                "summary": None if self.summary is None else self.summary.to_dict()}

    def __repr__(self):
        return f"PolicySelectionOutcome(scope={self.scope.source_key!r}, status={self.status.value!r})"
