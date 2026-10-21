"""Private patient-level empirical cutoff calculations."""

from __future__ import annotations

from dataclasses import dataclass

from safira.policy.records import (PolicyScope, PolicySelectionProtocol,
    PolicySelectionSummary, PolicyStatus)


@dataclass(frozen=True, repr=False)
class _CutoffResult:
    status: PolicyStatus
    reason_code: str
    summary: PolicySelectionSummary | None = None


def _index_assessments(examples, source_key):
    """Choose one assessment lexicographically before consulting any target."""
    selected = {}
    for example in examples:
        prediction = example.prediction
        if tuple(prediction.source_key) != tuple(source_key):
            continue
        group = example.patient_group_ref
        assessment = prediction.association.assessment_ref
        previous = selected.get(group)
        previous_assessment = (None if previous is None
                               else previous.prediction.association.assessment_ref)
        if previous is not None and assessment == previous_assessment:
            # The approved index rule has no secondary tie-breaker. Do not let
            # input ordering choose an assessment when its key is ambiguous.
            raise ValueError("index_assessment_ambiguous")
        if previous is None or assessment < previous_assessment:
            selected[group] = example
    return tuple(selected[key] for key in sorted(selected))


def _choose_cutoff(scores, correctness, groups, protocol: PolicySelectionProtocol, *, scope=None):
    """Return only aggregate selection values; empty-set risk remains undefined."""
    if type(protocol) is not PolicySelectionProtocol:
        raise ValueError("protocol")
    scores, correctness, groups = tuple(scores), tuple(correctness), tuple(groups)
    if not (len(scores) == len(correctness) == len(groups)) or not scores:
        return _CutoffResult(PolicyStatus.INSUFFICIENT_EVIDENCE, "insufficient_evidence")
    if len(set(groups)) != len(groups) or any(type(v) not in (float, int) or not 0 <= v <= 1 for v in scores):
        return _CutoffResult(PolicyStatus.INVALID_INPUT, "input_invalid")
    if any(type(v) is not int or v not in (0, 1) for v in correctness):
        return _CutoffResult(PolicyStatus.INVALID_INPUT, "input_invalid")
    if len(scores) < protocol.minimum_eligible_patients:
        return _CutoffResult(PolicyStatus.INSUFFICIENT_EVIDENCE, "insufficient_evidence")

    candidates = []
    for cutoff in protocol.candidate_cutoffs:
        chosen = [i for i, score in enumerate(scores)
                  if (score >= cutoff if protocol.comparison == ">=" else score > cutoff)]
        if not chosen:
            continue
        count = len(chosen)
        errors = sum(correctness[i] == 0 for i in chosen)
        risk = errors / count
        support = {value: sum(correctness[i] == value for i in chosen) for value in (0, 1)}
        if (count < protocol.minimum_selected_patients or risk > protocol.risk_ceiling
                or any(support[value] < minimum for value, minimum in protocol.correctness_support.items())):
            continue
        candidates.append(PolicySelectionSummary(float(cutoff), risk, count / len(scores), count, len(scores)))
    if not candidates:
        return _CutoffResult(PolicyStatus.NO_FEASIBLE_CUTOFF, "no_feasible_cutoff")
    best_coverage = max(item.coverage for item in candidates)
    tied = [item for item in candidates if item.coverage == best_coverage]
    chooser = min if protocol.tie_rule == "lowest_cutoff" else max
    best = chooser(tied, key=lambda item: item.cutoff)
    return _CutoffResult(PolicyStatus.SELECTED_UNEVALUATED, "selection_complete", best)

