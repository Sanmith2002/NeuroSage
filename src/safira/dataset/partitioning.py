"""Patient-group assignment, exact duplicate checks and history validation."""

from hashlib import sha256

from .exceptions import DatasetProtocolError, PatientGroupingConflict
from .verification import validate_linkage_check, validate_prior_check


ROLES = ("train", "validation", "calibration", "protected_test")

def _namespace(record):
    # Feature 002's provenance contract identifies the source contract; the
    # research integration supplies a more specific namespace when present.
    return record.provenance.details.get("source_namespace", record.provenance.details.get("source_contract_id", "unknown"))


def resolve_groups(predictions, declaration):
    result={}
    for record in predictions:
        alias=(_namespace(record), record.association.patient_ref)
        group=declaration.entries.get(alias)
        if group is None:
            # Same-source identity can be grouped only when explicitly listed.
            raise PatientGroupingConflict("patient_linkage_unknown")
        if alias in result and result[alias] != group:
            raise PatientGroupingConflict("patient_linkage_conflict")
        result[alias]=group
    return {(_namespace(r),r.association.patient_ref): declaration.entries[(_namespace(r),r.association.patient_ref)] for r in predictions}


def deduplicate(predictions):
    unique={}
    for record in predictions:
        key=(record.source_key,record.association.assessment_ref,record.association.occurrence_ref)
        prior=unique.get(key)
        if prior is not None and prior.to_dict()!=record.to_dict():
            raise PatientGroupingConflict("conflicting_duplicate_prediction")
        unique[key]=record
    return tuple(unique[k] for k in sorted(unique))


def assign_groups(groups, protocol):
    if protocol.hard_constraints:
        raise DatasetProtocolError("unsupported_hard_constraint")
    if protocol.partition_mode == "supplied":
        assignments=dict(protocol.assignments)
        if set(assignments) != set(groups) or any(v not in ROLES for v in assignments.values()):
            raise DatasetProtocolError("supplied_assignments_incomplete")
        return assignments
    if not protocol.seed or not protocol.algorithm_version or not protocol.allocation_order or any(r not in ROLES for r in protocol.allocation_order):
        raise DatasetProtocolError("deterministic_configuration_incomplete")
    ordered=sorted(groups)
    # Each group is assigned once using the declared seed/configuration. There
    # is no retry or inspection of outcomes when this assignment is infeasible.
    return {group:protocol.allocation_order[int.from_bytes(sha256((protocol.seed+"\0"+group).encode()).digest()[:8],"big") % len(protocol.allocation_order)] for group in ordered}


def check_prior_history(verifier, manifests, scope, protocol, *, include_checks=False):
    protected=set()
    checks=[]
    for manifest in manifests:
        try:
            check=verifier.verify_prior_history(manifest,scope,protocol)
            validate_prior_check(check,manifest,scope)
            if any(manifest.assignments.get(group) != "protected_test" for group in check.protected_membership):
                raise PatientGroupingConflict("prior_manifest_membership_conflict")
            protected.update(check.protected_membership)
            checks.append(check)
        except Exception:
            if protocol.require_prior_history:
                return (None,()) if include_checks else None
    if protocol.require_prior_history and not manifests: return (None,()) if include_checks else None
    return (protected,tuple(checks)) if include_checks else protected
