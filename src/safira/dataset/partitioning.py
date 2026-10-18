"""Patient-group assignment, exact duplicate checks and history validation."""

from hashlib import sha256
from datetime import datetime
from collections.abc import Mapping

from .exceptions import DatasetProtocolError, PatientGroupingConflict
from .verification import validate_linkage_check, validate_prior_check
from .verification import prediction_fingerprint


ROLES = ("train", "validation", "calibration", "protected_test")

def _namespace(record, namespaces=None):
    namespace = (namespaces or {}).get(prediction_fingerprint(record))
    if namespace is None:
        namespace = record.provenance.details.get("source_namespace") or record.provenance.details.get("source_contract_id")
    if type(namespace) is not str or not namespace.strip() or namespace == "unknown":
        raise PatientGroupingConflict("patient_namespace_unknown")
    return namespace


def resolve_groups(predictions, declaration, namespaces=None):
    result={}
    for record in predictions:
        alias=(_namespace(record, namespaces), record.association.patient_ref)
        group=declaration.entries.get(alias)
        if group is None:
            # Same-source identity can be grouped only when explicitly listed.
            raise PatientGroupingConflict("patient_linkage_unknown")
        if alias in result and result[alias] != group:
            raise PatientGroupingConflict("patient_linkage_conflict")
        result[alias]=group
    return {(_namespace(r,namespaces),r.association.patient_ref): declaration.entries[(_namespace(r,namespaces),r.association.patient_ref)] for r in predictions}


def deduplicate(predictions):
    unique={}
    for record in predictions:
        key=(record.source_key,record.association.assessment_ref,record.association.occurrence_ref)
        prior=unique.get(key)
        if prior is not None and prior.to_dict()!=record.to_dict():
            raise PatientGroupingConflict("conflicting_duplicate_prediction")
        unique[key]=record
    return tuple(unique[k] for k in sorted(unique))


def _parse_time(value):
    if type(value) is not str or not value:
        raise DatasetProtocolError("partition_metadata_missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed
    except ValueError:
        raise DatasetProtocolError("invalid_partition_constraint") from None


def _validate_constraint_shape(protocol):
    hard = protocol.hard_constraints
    unknown = set(hard) - {"site_isolation", "time_windows"}
    if unknown:
        raise DatasetProtocolError("unsupported_partition_constraint")
    if "site_isolation" in hard and hard["site_isolation"] != "same_partition":
        raise DatasetProtocolError("unsupported_partition_constraint")
    if "time_windows" in hard:
        windows = hard["time_windows"]
        if not isinstance(windows, Mapping) or set(windows) - set(ROLES) or not windows:
            raise DatasetProtocolError("invalid_partition_constraint")
        parsed_windows=[]
        for bounds in windows.values():
            if not isinstance(bounds, Mapping) or set(bounds) != {"start", "end"}:
                raise DatasetProtocolError("invalid_partition_constraint")
            start, end = _parse_time(bounds["start"]), _parse_time(bounds["end"])
            if start >= end:
                raise DatasetProtocolError("invalid_partition_constraint")
            parsed_windows.append((start,end))
        parsed_windows.sort()
        if any(parsed_windows[index][1] > parsed_windows[index+1][0]
               for index in range(len(parsed_windows)-1)):
            raise DatasetProtocolError("invalid_partition_constraint")


def _validate_assignments(assignments, groups, protocol, group_attributes):
    _validate_constraint_shape(protocol)
    required_attributes = set()
    if "site_isolation" in protocol.hard_constraints: required_attributes.add("site")
    if "time_windows" in protocol.hard_constraints: required_attributes.add("time")
    if protocol.allowed_strata: required_attributes.add("stratum")
    if required_attributes and not isinstance(group_attributes, Mapping):
        raise DatasetProtocolError("partition_metadata_missing")
    sites = {}
    windows = protocol.hard_constraints.get("time_windows", {})
    for group in groups:
        attrs = group_attributes.get(group) if isinstance(group_attributes, Mapping) else None
        if required_attributes and not isinstance(attrs, Mapping):
            raise DatasetProtocolError("partition_metadata_missing")
        if "site" in required_attributes:
            site = attrs.get("site")
            if type(site) is not str or not site:
                raise DatasetProtocolError("partition_metadata_missing")
            prior = sites.setdefault(site, assignments[group])
            if prior != assignments[group]:
                raise DatasetProtocolError("partition_constraints_infeasible")
        if protocol.allowed_strata:
            stratum = attrs.get("stratum")
            if type(stratum) is not str or not stratum:
                raise DatasetProtocolError("partition_metadata_missing")
            if stratum not in protocol.allowed_strata:
                raise DatasetProtocolError("partition_constraints_infeasible")
        if windows:
            moment = _parse_time(attrs.get("time"))
            bounds = windows.get(assignments[group])
            if bounds is None or not (_parse_time(bounds["start"]) <= moment < _parse_time(bounds["end"])):
                raise DatasetProtocolError("partition_constraints_infeasible")
    return assignments


def _time_role(group, windows, group_attributes):
    attrs = group_attributes.get(group) if isinstance(group_attributes, Mapping) else None
    if not isinstance(attrs, Mapping):
        raise DatasetProtocolError("partition_metadata_missing")
    moment = _parse_time(attrs.get("time"))
    matching = [role for role,bounds in windows.items()
                if _parse_time(bounds["start"]) <= moment < _parse_time(bounds["end"])]
    if len(matching) != 1:
        raise DatasetProtocolError("partition_constraints_infeasible")
    return matching[0]


def assign_groups(groups, protocol, group_attributes=None):
    _validate_constraint_shape(protocol)
    if protocol.partition_mode == "supplied":
        assignments=dict(protocol.assignments)
        if set(assignments) != set(groups) or any(v not in ROLES for v in assignments.values()):
            raise DatasetProtocolError("supplied_assignments_incomplete")
        return _validate_assignments(assignments, groups, protocol, group_attributes)
    if not protocol.seed or not protocol.algorithm_version or not protocol.allocation_order or any(r not in ROLES for r in protocol.allocation_order):
        raise DatasetProtocolError("deterministic_configuration_incomplete")
    ordered=sorted(groups)
    # Hash exactly once per free allocation unit. No retry or alternative seed
    # is attempted when the approved protocol's constraints cannot be met.
    windows = protocol.hard_constraints.get("time_windows", {})
    site_isolation = "site_isolation" in protocol.hard_constraints
    if windows and not set(windows).issubset(protocol.allocation_order):
        raise DatasetProtocolError("invalid_partition_constraint")
    forced = {group: _time_role(group, windows, group_attributes) for group in ordered} if windows else {}
    if site_isolation:
        if not isinstance(group_attributes, Mapping):
            raise DatasetProtocolError("partition_metadata_missing")
        sites={}
        for group in ordered:
            attrs=group_attributes.get(group)
            site=attrs.get("site") if isinstance(attrs,Mapping) else None
            if type(site) is not str or not site:
                raise DatasetProtocolError("partition_metadata_missing")
            sites.setdefault(site,[]).append(group)
        site_roles={}
        for site,members in sites.items():
            required={forced[group] for group in members if group in forced}
            if len(required)>1:
                raise DatasetProtocolError("partition_constraints_infeasible")
            if required:
                site_roles[site]=next(iter(required))
            else:
                site_roles[site]=protocol.allocation_order[int.from_bytes(sha256((protocol.seed+"\0site\0"+site).encode()).digest()[:8],"big") % len(protocol.allocation_order)]
        assignments={group:site_roles[group_attributes[group]["site"]] for group in ordered}
    else:
        assignments={group:protocol.allocation_order[int.from_bytes(sha256((protocol.seed+"\0"+group).encode()).digest()[:8],"big") % len(protocol.allocation_order)] for group in ordered}
        assignments.update(forced)
    return _validate_assignments(assignments, groups, protocol, group_attributes)


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
