"""T007: coverage is a structured profile of Feature 002's original states."""

import pytest

from safira.collection import EvidenceItem
from safira.dataset import CorrectnessExample
from safira.signals.exceptions import SignalInputError
from safira.signals.records import CohortAdequacyCriteria, SignalSourceKey
from safira.signals.service import _cohort_support_by_source
from safira.signals.stateless import _evidence_coverage

from signals_fixtures import make_live_record


@pytest.mark.parametrize("state", ["unsupported", "missing", "unavailable", "invalid"])
def test_coverage_preserves_non_available_evidence_states(registered_collection, state):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    key = record.source_key
    if state == "available":
        item = EvidenceItem(record.association, key, "feature_representation", state,
                            value=[0.25], interpretation={"meaning": "synthetic vector", "shape": [1]})
    else:
        item = EvidenceItem(record.association, key, "feature_representation", state)
    altered = type(record)(
        record.association, record.model_id, record.model_version, record.label_id,
        record.primary, record.provenance, (item,), record.component, record.input_verification,
    )
    result = _evidence_coverage(altered, ("feature_representation",))
    assert result.value["feature_representation"] == state
    assert result.state.value == "available"
    assert result.value != {"feature_representation": 0}


def test_coverage_reports_missing_expected_category_without_fabricating_zero(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    altered = type(record)(record.association, record.model_id, record.model_version, record.label_id,
                           record.primary, record.provenance,
                           tuple(item for item in record.evidence if item.category != "explanation"),
                           record.component, record.input_verification)
    result = _evidence_coverage(altered, ("explanation", "feature_representation"))
    assert result.value == {"explanation": "missing", "feature_representation": "unsupported"}


def test_duplicate_evidence_categories_are_invalid(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    item = EvidenceItem(record.association, record.source_key, "feature_representation", "missing")
    altered = type(record)(record.association, record.model_id, record.model_version, record.label_id,
                           record.primary, record.provenance, (item, item))
    with pytest.raises(SignalInputError):
        _evidence_coverage(altered, ("feature_representation",))


def test_internal_cohort_support_is_exactly_scoped_and_patient_grouped(registered_collection):
    registry, register = registered_collection
    first_def, _, first = make_live_record(registry, register, model_id="cohort-a", labels=("shared",))
    second_def, _, second = make_live_record(registry, register, model_id="cohort-b", labels=("shared",))
    examples = (
        CorrectnessExample(first, "target", "v1", 1, 1, "group-a", "train"),
        CorrectnessExample(first, "target", "v1", 0, 0, "group-a", "train"),
        CorrectnessExample(first, "target", "v1", 1, 1, "group-b", "train"),
        CorrectnessExample(second, "target", "v1", 1, 1, "group-a", "train"),
    )
    first_key = SignalSourceKey(first_def.model_id, "v1", "shared")
    second_key = SignalSourceKey(second_def.model_id, "v1", "shared")
    summary = _cohort_support_by_source(
        examples,
        criteria_by_source={first_key: CohortAdequacyCriteria(2, {0: 1, 1: 1}),
                            second_key: CohortAdequacyCriteria(1)},
        source_keys=(first_key, second_key),
    )
    assert summary[(first_def.model_id, "v1", "shared")]["unique_patient_groups"] == 2
    assert summary[(first_def.model_id, "v1", "shared")]["correctness_class_patient_groups"] == {"0": 0, "1": 1}
    assert summary[(first_def.model_id, "v1", "shared")]["conflicting_correctness_patient_groups"] == 1
    assert summary[(second_def.model_id, "v1", "shared")]["unique_patient_groups"] == 1
    assert len(summary) == 2
    with pytest.raises(TypeError):
        summary[(first_def.model_id, "v1", "shared")]["unique_patient_groups"] = 99
