from types import SimpleNamespace

from safira.policy.records import (PolicyEvidenceReference, PolicyScope,
    PolicySelectionProtocol, PolicyStatus)
from safira.policy.selection import _choose_cutoff


def protocol(cutoffs=(.5, .7, .9), ceiling=.34, tie="lowest_cutoff", support=None):
    scope = PolicyScope("m", "v1", "l", "a" * 64, "adapter", "v1", "b" * 64, {})
    return PolicySelectionProtocol("p", "v1", (scope,), PolicyEvidenceReference("d", "p", "v1", "mref", "b", "c" * 64),
        {"m\0v1\0l": ("target", "v1")},
        ceiling, cutoffs, 3, 1, support or {}, ">=", tie,
        "lexicographic_assessment_ref_v1", True, "approval")


def test_selects_maximum_coverage_under_empirical_risk_ceiling():
    # With a .2 ceiling, only the highest cutoff selects a feasible nonempty set.
    result = _choose_cutoff((.9, .8, .7, .4), (1, 0, 1, 1), ("g1", "g2", "g3", "g4"), protocol(ceiling=.2))
    assert result.status is PolicyStatus.SELECTED_UNEVALUATED
    assert result.summary.cutoff == .9
    assert result.summary.empirical_risk == 0
    assert result.summary.coverage == .25


def test_equal_coverage_cutoff_tie_uses_protocol_rule():
    result = _choose_cutoff((.9, .8, .4), (1, 1, 0), ("a", "b", "c"), protocol((.85, .9), .1, "highest_cutoff"))
    assert result.summary.cutoff == .9


def test_non_monotonic_empirical_risk_selects_later_feasible_cutoff():
    # The risk at .8 is worse than at .9, but a broader .6 set is feasible.
    result = _choose_cutoff((.9, .8, .7, .6), (1, 0, 1, 1),
                            ("g1", "g2", "g3", "g4"),
                            protocol((.9, .8, .6), .3, support={1: 1}))
    assert result.status is PolicyStatus.SELECTED_UNEVALUATED
    assert result.summary.cutoff == .6
    assert result.summary.empirical_risk == .25
    assert result.summary.coverage == 1.0


def test_empty_set_is_undefined_and_never_successful():
    result = _choose_cutoff((.4, .3, .2), (0, 1, 1), ("a", "b", "c"), protocol((.8, .9), .2))
    assert result.status is PolicyStatus.NO_FEASIBLE_CUTOFF
    assert result.summary is None


def test_support_is_candidate_specific_and_constant_scores_are_all_or_none():
    result = _choose_cutoff((.7, .7, .7), (1, 0, 1), ("a", "b", "c"), protocol((.7, .8), .1, support={0: 1}))
    assert result.status is PolicyStatus.NO_FEASIBLE_CUTOFF


def test_duplicate_visits_choose_index_by_assessment_not_correctness():
    from safira.policy.selection import _index_assessments
    rows = [SimpleNamespace(patient_group_ref="g", prediction=SimpleNamespace(
        source_key=("m", "v1", "l"), association=SimpleNamespace(assessment_ref="z")), correctness_target=1),
        SimpleNamespace(patient_group_ref="g", prediction=SimpleNamespace(
        source_key=("m", "v1", "l"), association=SimpleNamespace(assessment_ref="a")), correctness_target=0)]
    result = _index_assessments(rows, ("m", "v1", "l"))
    assert len(result) == 1
    assert result[0].prediction.association.assessment_ref == "a"


def test_index_selection_is_outcome_blind_and_rejects_ambiguous_index_key():
    import pytest
    from safira.policy.selection import _index_assessments
    def row(assessment, target, occurrence):
        return SimpleNamespace(patient_group_ref="g", correctness_target=target, prediction=SimpleNamespace(
            source_key=("m", "v1", "l"), association=SimpleNamespace(
                assessment_ref=assessment, occurrence_ref=occurrence)))
    first = row("a", 0, "occ-1")
    later = row("z", 1, "occ-2")
    changed = row("a", 1, "occ-1")
    assert _index_assessments((first, later), ("m", "v1", "l"))[0] is first
    assert _index_assessments((changed, later), ("m", "v1", "l"))[0] is changed
    with pytest.raises(ValueError, match="index_assessment_ambiguous"):
        _index_assessments((first, row("a", 1, "occ-3")), ("m", "v1", "l"))


def test_selection_summary_rejects_inconsistent_coverage():
    import pytest
    from safira.policy.records import PolicySelectionSummary
    with pytest.raises(ValueError):
        PolicySelectionSummary(.8, .1, .7, 2, 4)


def test_scopes_with_same_label_but_different_contributors_or_versions_are_not_pooled():
    from safira.policy.selection import _index_assessments
    sources = (("model-a", "v1", "shared-label"), ("model-b", "v1", "shared-label"),
               ("model-a", "v2", "shared-label"))
    rows = tuple(SimpleNamespace(patient_group_ref=f"patient-{index}", correctness_target=index % 2,
        prediction=SimpleNamespace(source_key=source, association=SimpleNamespace(
            assessment_ref=f"assessment-{index}"))) for index, source in enumerate(sources))
    for source in sources:
        selected = _index_assessments(rows, source)
        assert len(selected) == 1
        assert tuple(selected[0].prediction.source_key) == source
    # Each scope is evaluated on its own observations: a good scope can succeed
    # while another scope has no feasible cutoff or lacks minimum support.
    good = _choose_cutoff((.9, .8, .7), (1, 1, 1), ("a", "b", "c"),
                          protocol((.7,), .1, support={1: 1}))
    infeasible = _choose_cutoff((.9, .8, .7), (0, 0, 0), ("d", "e", "f"),
                                protocol((.7,), .1, support={1: 1}))
    insufficient = _choose_cutoff((.9, .8), (1, 1), ("g", "h"),
                                   protocol((.7,), .1, support={1: 1}))
    assert good.status is PolicyStatus.SELECTED_UNEVALUATED
    assert infeasible.status is PolicyStatus.NO_FEASIBLE_CUTOFF
    assert insufficient.status is PolicyStatus.INSUFFICIENT_EVIDENCE
