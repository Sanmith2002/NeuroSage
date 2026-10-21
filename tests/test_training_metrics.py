from test_training_selection import _selection_fixture


def test_optional_secondary_metric_states_are_reported_without_invalidating_brier_selection():
    scope, protocol, baseline, logistic, compare, Status = _selection_fixture()
    # Two classes make both metrics available, even when Brier chooses a model.
    result = compare(protocol, scope, baseline, logistic, ((0.0,), (1.0,), (.25,), (.75,)),
                     (0, 1, 0, 1), patient_group_refs=("g1", "g2", "g3", "g4"))
    assert result.status in (Status.SELECTED_BASELINE, Status.SELECTED_LOGISTIC)
    assert result.secondary_metrics["l2_logistic"]["auroc"].state == "available"
    assert result.secondary_metrics["l2_logistic"]["average_precision"].state == "available"
    assert result.metrics_role == "selection_evidence"


def test_optional_secondary_metrics_can_be_undefined_when_brier_requirement_allows_it():
    from dataclasses import replace
    from safira.training.records import ValidationSupportCriteria
    scope, protocol, baseline, logistic, compare, Status = _selection_fixture()
    protocol = replace(protocol, validation_adequacy={scope.source_key: ValidationSupportCriteria(2, {})})
    result = compare(protocol, scope, baseline, logistic, ((0.0,), (1.0,), (.25,), (.75,)),
                     (1, 1, 1, 1), patient_group_refs=("g1", "g2", "g3", "g4"))
    assert result.status in (Status.SELECTED_BASELINE, Status.SELECTED_LOGISTIC)
    assert result.secondary_metrics["l2_logistic"]["auroc"].state == "undefined"
    assert result.secondary_metrics["l2_logistic"]["average_precision"].state == "undefined"

