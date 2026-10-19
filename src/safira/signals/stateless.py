"""Model-agnostic Batch A signal calculations over admitted Feature 002 records."""

from __future__ import annotations

import hashlib
from itertools import combinations
import json
from math import isfinite, log
from collections.abc import Mapping

from safira.signals.base import SignalDimension, SignalState
from safira.signals.exceptions import SignalInputError
from safira.signals.records import SignalResult, SignalSourceKey


_STATE_MAP = {
    "unsupported": SignalState.UNSUPPORTED,
    "missing": SignalState.MISSING,
    "unavailable": SignalState.UNAVAILABLE,
    "invalid": SignalState.INVALID,
}
_SAFE_REASONS = {
    "missing": "evidence_missing",
    "unsupported": "evidence_unsupported",
    "unavailable": "evidence_unavailable",
    "invalid": "evidence_invalid",
}


def _evidence_map(record):
    result = {}
    for item in record.evidence:
        if item.category in result:
            raise SignalInputError("duplicate_evidence_category")
        if item.association != record.association or item.source_key != record.source_key:
            raise SignalInputError("evidence_source_mismatch")
        result[item.category] = item
    return result


def _provenance(record, admission_check=None, evidence_sources=()):
    """Retain safe evidence semantics and an opaque digest of verified admission."""
    lineage = {}
    allowed_interpretation = {
        "target_label", "target_output", "output_space", "calibrated",
        "calibration_method", "timing_scope", "same_input", "stochastic_mechanism",
    }

    def digest(value):
        try:
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        except Exception:
            raise SignalInputError("evidence_not_canonical") from None

    evidence = _evidence_map(record)
    for category in evidence_sources:
        if category == "primary_output":
            lineage[category] = {"state": "available", "content_sha256": digest(record.primary.to_dict())}
            continue
        item = evidence.get(category)
        if item is None:
            lineage[category] = {"state": "missing"}
        else:
            lineage[category] = {
                "state": item.state,
                "content_sha256": digest(item.to_dict()),
                "interpretation": {key: item.interpretation[key]
                                   for key in allowed_interpretation if key in item.interpretation},
            }
            provenance_ref = item.interpretation.get("provenance")
            if type(provenance_ref) is str and provenance_ref:
                lineage[category]["provenance_sha256"] = digest(provenance_ref)
    verification_digest = None
    if admission_check is not None:
        evidence = {
            "record_fingerprint": admission_check.record_fingerprint,
            "source_key": list(admission_check.source_key),
            "association": list(admission_check.association),
            "provenance_mode": admission_check.provenance_mode,
            "authority": admission_check.authority,
            "method": admission_check.method,
            "evidence_ref": admission_check.evidence_ref,
            "input_scope": admission_check.input_scope,
        }
        verification_digest = digest(evidence)
    return {"mode": record.provenance.mode, "assurance": record.provenance.assurance,
            "source_provenance_sha256": digest(record.provenance.to_dict()),
            "primary_output_sha256": digest(record.primary.to_dict()),
            "admission_check_sha256": verification_digest, "evidence_lineage": lineage}


def _result(record, dimension, method_id, parameters, state, value, meaning,
            evidence_sources, reason=None, method_version="v1", admission_check=None):
    return SignalResult(
        SignalSourceKey(*record.source_key), dimension, method_id, method_version,
        parameters, state, value, meaning, tuple(evidence_sources),
        _provenance(record, admission_check, evidence_sources), reason,
        record.primary.to_dict(),
    )


def _nonvalue(record, dimension, method_id, parameters, state, evidence_sources, reason,
              meaning, method_version="v1", admission_check=None):
    return _result(record, dimension, method_id, parameters, state, None, meaning,
                   evidence_sources, reason, method_version, admission_check)


def _lookup_state(record, category):
    item = _evidence_map(record).get(category)
    if item is None:
        return None, SignalState.MISSING, "evidence_missing"
    if item.state != "available":
        return item, _STATE_MAP.get(item.state, SignalState.INVALID), _SAFE_REASONS.get(item.state, "evidence_invalid")
    return item, SignalState.AVAILABLE, None


def _validated_categories(categories):
    if not isinstance(categories, (tuple, list)):
        raise ValueError("required_evidence")
    values = tuple(categories)
    if any(type(value) is not str or not value.strip() for value in values) or len(values) != len(set(values)):
        raise ValueError("required_evidence")
    return values


def _evidence_coverage(record, required_evidence, *, admission_check=None):
    """Return prerequisite states, not a scalar score or cohort adequacy claim."""
    required = _validated_categories(required_evidence)
    items = _evidence_map(record)
    profile = {}
    for category in required:
        item = items.get(category)
        profile[category] = item.state if item is not None else "missing"
    return _result(
        record, SignalDimension.DATA_SUFFICIENCY, "evidence_coverage",
        {"required_evidence": required, "aggregation": "none"}, SignalState.AVAILABLE,
        profile,
        "Feature 002 prerequisite evidence states; not cohort adequacy, clinical eligibility, correctness, or safety.",
        required, admission_check=admission_check,
    )


def _log_base(base):
    if base == "e" and type(base) is str:
        return "e", None
    if type(base) not in (int, float) or not isfinite(base) or base <= 1:
        raise ValueError("log_base")
    return base, log(base)


def _binary_entropy(probability, base):
    if probability in (0, 1):
        return 0.0
    divisor = None if base == "e" else log(base)
    value = -probability * log(probability) - (1.0 - probability) * log(1.0 - probability)
    return value if divisor is None else value / divisor


def _bernoulli_entropy(record, *, log_base, admission_check=None):
    """Calculate binary entropy of the declared primary probability, not error."""
    normalized_base, _ = _log_base(log_base)
    params = {"log_base": normalized_base}
    primary = record.primary
    if primary.value_kind != "probability" or type(primary.value) not in (int, float):
        return _nonvalue(record, SignalDimension.PREDICTION_UNCERTAINTY,
                         "bernoulli_entropy", params, SignalState.INVALID,
                         ("primary_output",), "primary_output_not_probability",
                         "Bernoulli predictive entropy; not correctness or reliability.", admission_check=admission_check)
    probability = float(primary.value)
    if not isfinite(probability) or not 0 <= probability <= 1:
        return _nonvalue(record, SignalDimension.PREDICTION_UNCERTAINTY,
                         "bernoulli_entropy", params, SignalState.INVALID,
                         ("primary_output",), "primary_probability_invalid",
                         "Bernoulli predictive entropy; not correctness or reliability.", admission_check=admission_check)
    return _result(record, SignalDimension.PREDICTION_UNCERTAINTY,
                   "bernoulli_entropy", params, SignalState.AVAILABLE,
                   _binary_entropy(probability, normalized_base),
                   f"Bernoulli predictive entropy in {'bits' if normalized_base == 2 else 'nats' if normalized_base == 'e' else f'log base {normalized_base}'}; not correctness or reliability.",
                   ("primary_output",), admission_check=admission_check)


def _modality_jsd(record, *, log_base, admission_check=None):
    """Return all unordered pairwise JSD values for comparable modality probabilities."""
    normalized_base, _ = _log_base(log_base)
    params = {"log_base": normalized_base, "aggregation": "all_unordered_pairs"}
    meaning = "Pairwise Jensen-Shannon divergence between comparable modality Bernoulli probabilities."
    item, state, reason = _lookup_state(record, "modality_outputs")
    if state is not SignalState.AVAILABLE:
        return _nonvalue(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                         state, ("modality_outputs",), reason, meaning, admission_check=admission_check)
    if not isinstance(item.value, Mapping) or len(item.value) < 2:
        return _nonvalue(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                         SignalState.INSUFFICIENT_EVIDENCE, ("modality_outputs",),
                         "fewer_than_two_modalities", meaning, admission_check=admission_check)
    interpretation = item.interpretation
    required = ("modality_ids", "output_space", "target_label", "target_output",
                "calibrated", "calibration_method", "timing_scope")
    if any(key not in interpretation for key in required):
        return _nonvalue(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                         SignalState.NOT_READY, ("modality_outputs",),
                         "comparison_semantics_incomplete", meaning, admission_check=admission_check)
    ids = tuple(interpretation["modality_ids"])
    if (set(ids) != set(item.value) or len(ids) != len(set(ids))
            or interpretation["output_space"] != "probability"
            or interpretation["target_label"] != record.label_id
            or type(interpretation["target_output"]) is not str
            or not interpretation["target_output"].strip()
            or type(interpretation["calibrated"]) is not bool
            or type(interpretation["calibration_method"]) is not str
            or not interpretation["calibration_method"].strip()
            or type(interpretation["timing_scope"]) is not str
            or not interpretation["timing_scope"].strip()):
        return _nonvalue(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                         SignalState.INVALID, ("modality_outputs",),
                         "comparison_semantics_invalid", meaning, admission_check=admission_check)
    semantics = interpretation.get("modality_semantics")
    if semantics is not None:
        if not isinstance(semantics, Mapping) or set(semantics) != set(ids):
            return _nonvalue(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                             SignalState.INVALID, ("modality_outputs",),
                             "modality_semantics_mismatch", meaning, admission_check=admission_check)
        keys = ("target_label", "target_output", "output_space", "calibrated",
                "calibration_method", "timing_scope")
        normalized = [{key: semantics[mid].get(key) for key in keys}
                      if isinstance(semantics[mid], Mapping) else None for mid in ids]
        if any(value != normalized[0] for value in normalized[1:]) or normalized[0] != {
            key: interpretation[key] for key in keys
        }:
            return _nonvalue(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                             SignalState.INVALID, ("modality_outputs",),
                             "modality_semantics_incomparable", meaning, admission_check=admission_check)
    try:
        probabilities = {name: float(item.value[name]) for name in ids}
    except Exception:
        probabilities = {}
    if any(not isfinite(value) or not 0 <= value <= 1 for value in probabilities.values()) or len(probabilities) != len(ids):
        return _nonvalue(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                         SignalState.INVALID, ("modality_outputs",),
                         "modality_probability_invalid", meaning, admission_check=admission_check)
    pairs = []
    for left, right in combinations(ids, 2):
        p, q = probabilities[left], probabilities[right]
        mixture = (p + q) / 2.0
        divergence = _binary_entropy(mixture, normalized_base) - (
            _binary_entropy(p, normalized_base) + _binary_entropy(q, normalized_base)
        ) / 2.0
        # Floating point cancellation may produce a tiny negative at equality.
        divergence = max(0.0, divergence)
        pairs.append({"left_modality": left, "right_modality": right, "divergence": divergence})
    return _result(record, SignalDimension.MODALITY_AGREEMENT, "modality_jsd", params,
                   SignalState.AVAILABLE, tuple(pairs), meaning, ("modality_outputs",), admission_check=admission_check)


def _repeated_output_variance(record, *, admission_check=None):
    """Descriptive population variance over a verified, exact set of same-input repeats."""
    meaning = "Population variance of the declared repeated primary probabilities; not decomposed uncertainty."
    params_base = {"ddof": 0}
    item, state, reason = _lookup_state(record, "repeated_outputs")
    if state is not SignalState.AVAILABLE:
        return _nonvalue(record, SignalDimension.PREDICTION_UNCERTAINTY,
                         "repeated_output_variance", params_base, state,
                         ("repeated_outputs",), reason, meaning, admission_check=admission_check)
    interpretation = item.interpretation
    repeat_ids = interpretation.get("repeat_ids")
    required = (interpretation.get("same_input") is True
                and type(interpretation.get("stochastic_mechanism")) is str
                and bool(interpretation.get("stochastic_mechanism").strip())
                and type(interpretation.get("provenance")) is str
                and bool(interpretation.get("provenance").strip())
                and interpretation.get("output_space") == "probability"
                and interpretation.get("target_label") == record.label_id
                and type(interpretation.get("calibrated")) is bool
                and type(interpretation.get("calibration_method")) is str
                and bool(interpretation.get("calibration_method").strip()))
    if not required:
        return _nonvalue(record, SignalDimension.PREDICTION_UNCERTAINTY,
                         "repeated_output_variance", params_base, SignalState.NOT_READY,
                         ("repeated_outputs",), "repeat_provenance_incomplete", meaning, admission_check=admission_check)
    values = item.value
    if (record.primary.value_kind != "probability" or not isinstance(values, (tuple, list))
            or any(type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1
                   for value in values)):
        return _nonvalue(record, SignalDimension.PREDICTION_UNCERTAINTY,
                         "repeated_output_variance", params_base, SignalState.INVALID,
                         ("repeated_outputs",), "repeat_probability_invalid", meaning, admission_check=admission_check)
    if (not isinstance(repeat_ids, (tuple, list)) or len(repeat_ids) != len(values)
            or len(set(repeat_ids)) != len(repeat_ids)):
        return _nonvalue(record, SignalDimension.PREDICTION_UNCERTAINTY,
                         "repeated_output_variance", params_base, SignalState.INVALID,
                         ("repeated_outputs",), "repeat_identity_invalid", meaning, admission_check=admission_check)
    if len(values) < 2:
        return _nonvalue(record, SignalDimension.PREDICTION_UNCERTAINTY,
                         "repeated_output_variance", {**params_base, "repeat_count": len(values)},
                         SignalState.INSUFFICIENT_EVIDENCE, ("repeated_outputs",),
                         "fewer_than_two_repeats", meaning, admission_check=admission_check)
    normalized = tuple(float(value) for value in values)
    mean = sum(normalized) / len(normalized)
    variance = sum((value - mean) ** 2 for value in normalized) / len(normalized)
    return _result(record, SignalDimension.PREDICTION_UNCERTAINTY,
                   "repeated_output_variance",
                   {**params_base, "repeat_count": len(normalized)},
                   SignalState.AVAILABLE, variance, meaning, ("repeated_outputs",), admission_check=admission_check)


def _explanation_applicability(record, *, admission_check=None):
    """Preserve explanation provenance without scoring explanation reliability."""
    meaning = "Explanation metadata and applicability only; no numeric reliability score is defined in V1."
    item, state, reason = _lookup_state(record, "explanation")
    if state is not SignalState.AVAILABLE:
        return _nonvalue(record, SignalDimension.EXPLANATION_RELIABILITY,
                         "explanation_applicability", {}, state, ("explanation",), reason,
                         meaning, admission_check=admission_check)
    info = item.interpretation
    required = ("method", "target_label", "target_output", "output_space", "calibrated")
    if (any(name not in info for name in required) or info.get("target_label") != record.label_id
            or type(info.get("calibrated")) is not bool):
        return _nonvalue(record, SignalDimension.EXPLANATION_RELIABILITY,
                         "explanation_applicability", {}, SignalState.INVALID,
                         ("explanation",), "explanation_metadata_invalid", meaning,
                         admission_check=admission_check)
    value = {
        "applicability": "metadata_only",
        "method": info["method"],
        "target_label": info["target_label"],
        "target_output": info["target_output"],
        "output_space": info["output_space"],
        "calibrated": info["calibrated"],
        "calibration_relation": info.get("calibration_relation", "not_declared"),
        "truncated": info.get("truncated", False),
    }
    return _result(record, SignalDimension.EXPLANATION_RELIABILITY,
                   "explanation_applicability", {"numeric_score": False}, SignalState.AVAILABLE,
                   value, meaning, ("explanation",), admission_check=admission_check)
