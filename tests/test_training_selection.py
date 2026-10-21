import pytest


def _selection_api():
    from safira.training.candidates import (
        CandidateResult, CandidateStatus, SelectionStatus, ValidationSupportCriteria,
        compare_candidates,
    )
    from safira.training.records import (CandidateFailurePolicy, TrainingProtocol, TrainingScope,
                                         TrainingSupportCriteria)
    return (CandidateResult, CandidateStatus, SelectionStatus, ValidationSupportCriteria,
            compare_candidates, CandidateFailurePolicy, TrainingProtocol, TrainingScope, TrainingSupportCriteria)


def _selection_fixture():
    (Candidate, CandidateStatus, SelectionStatus, Validation, compare,
     FailurePolicy, Protocol, Scope, Support) = _selection_api()
    scope = Scope("m", "v1", "label", "a" * 64, "adapter", "v1", "b" * 64, "prep")
    protocol = Protocol(
        "p", "v1", (scope,), {scope.source_key: Support(2, {0: 1, 1: 1})},
        {scope.source_key: ()}, {}, {}, {},
        {scope.source_key: Validation(2, {0: 1, 1: 1})},
        {scope.source_key: FailurePolicy.ALLOW_REMAINING},
    )
    baseline = Candidate(scope.source_key, "prevalence_baseline", CandidateStatus.FITTED,
                         probability=.5, classes=(0, 1))
    logistic = Candidate(scope.source_key, "l2_logistic", CandidateStatus.FITTED,
                         coefficients=(3.0,), intercept=-1.5, classes=(0, 1))
    return scope, protocol, baseline, logistic, compare, SelectionStatus


def test_selection_uses_exact_brier_and_baseline_wins_exact_tie_on_identical_validation_rows():
    scope, protocol, baseline, logistic, compare, Status = _selection_fixture()
    # Both yield exactly .5 for these deliberately symmetric labels and scores.
    logistic = type(logistic)(scope.source_key, "l2_logistic", logistic.status,
                              coefficients=(0.0,), intercept=0.0, classes=(0, 1))
    result = compare(protocol, scope, baseline, logistic, ((0.0,), (1.0,)), (0, 1),
                     patient_group_refs=("g1", "g2"))
    assert result.status is Status.SELECTED_BASELINE
    assert result.brier_scores == {"prevalence_baseline": .25, "l2_logistic": .25}
    assert result.validation_role == "selection_evidence"
    assert result.validation_spent is True


def test_lower_brier_wins_and_optional_one_class_secondary_metrics_are_explicit():
    scope, protocol, baseline, logistic, compare, Status = _selection_fixture()
    result = compare(protocol, scope, baseline, logistic, ((0.0,), (1.0,)), (0, 1),
                     patient_group_refs=("g1", "g2"))
    assert result.status is Status.SELECTED_LOGISTIC
    assert result.brier_scores["l2_logistic"] < result.brier_scores["prevalence_baseline"]
    # secondary metrics are undefined with the two-row validation sample? AUROC is defined;
    # AP remains defined. A one-class sample returns explicit undefined reasons.
    one_class = compare(protocol, scope, baseline, logistic, ((0.0,), (1.0,)), (1, 1),
                        patient_group_refs=("g1", "g2"))
    assert one_class.status is Status.COMPARISON_UNDEFINED
    assert one_class.reason_code == "validation_class_support_insufficient"


def test_candidate_failure_requires_predeclared_policy_and_validation_feasibility_is_scoped():
    scope, protocol, baseline, logistic, compare, Status = _selection_fixture()
    failed = type(logistic)(scope.source_key, "l2_logistic", type(logistic.status).FIT_FAILED,
                            reason_code="candidate_fit_failed")
    allowed = compare(protocol, scope, baseline, failed, ((0.0,), (1.0,)), (0, 1),
                      patient_group_refs=("g1", "g2"))
    assert allowed.status is Status.SELECTED_BASELINE
    missing = compare(protocol, scope, baseline, logistic, ((0.0,),), (1,),
                      patient_group_refs=("g1",))
    assert missing.status is Status.COMPARISON_UNDEFINED
    assert missing.brier_scores == {}


def test_require_all_candidate_policy_does_not_silently_drop_failed_logistic():
    from dataclasses import replace
    from safira.training.records import CandidateFailurePolicy
    scope, protocol, baseline, logistic, compare, Status = _selection_fixture()
    protocol = replace(protocol, candidate_failure_policies={scope.source_key: CandidateFailurePolicy.REQUIRE_ALL})
    failed = type(logistic)(scope.source_key, "l2_logistic", type(logistic.status).FIT_FAILED,
                            reason_code="candidate_fit_failed")
    result = compare(protocol, scope, baseline, failed, ((0.0,), (1.0,)), (0, 1),
                     patient_group_refs=("g1", "g2"))
    assert result.status is Status.COMPARISON_UNDEFINED
    assert result.reason_code == "candidate_failure_policy_blocked"


def test_selection_rejects_nonfinite_candidate_probabilities_and_group_mismatch():
    scope, protocol, baseline, logistic, compare, Status = _selection_fixture()
    with pytest.raises(ValueError):
        type(baseline)(scope.source_key, "prevalence_baseline", baseline.status,
                       probability=float("nan"), classes=(0, 1))
    result = compare(protocol, scope, baseline, logistic, ((0.0,), (1.0,)), (0, 1),
                     patient_group_refs=("g1",))
    assert result.status is Status.COMPARISON_UNDEFINED

