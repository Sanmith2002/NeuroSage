"""T009: comparable same-contributor modality probabilities use Bernoulli JSD."""

from dataclasses import replace

import pytest

from safira.adapters import AdapterCapabilities
from safira.collection import EvidenceItem
from safira.signals.stateless import _modality_jsd

from signals_fixtures import make_live_record


def _record(registered_collection, output):
    registry, register = registered_collection
    _, _, record = make_live_record(
        registry, register, model_id="modality", capabilities=AdapterCapabilities(
            prediction_probability=True, modality_outputs=True,
        ), evidence={"modality_outputs": output},
        interpretations={"modality_outputs": {
            "meaning": "synthetic modality probabilities", "modality_ids": list(output),
            "output_space": "probability", "target_label": "label-a",
            "target_output": "positive-class-probability", "calibrated": True,
            "calibration_method": "synthetic-calibration-v1", "timing_scope": "same-occurrence",
        }},
    )
    return record


def test_equal_modalities_have_zero_jsd(registered_collection):
    record = _record(registered_collection, {"image": 0.6, "tabular": 0.6})
    result = _modality_jsd(record, log_base=2)
    assert result.value[0]["divergence"] == pytest.approx(0.0)


def test_opposite_modalities_have_one_bit_jsd(registered_collection):
    record = _record(registered_collection, {"image": 0.0, "tabular": 1.0})
    result = _modality_jsd(record, log_base=2)
    assert result.value[0]["divergence"] == pytest.approx(1.0)


def test_incomparable_target_or_calibration_is_not_combined(registered_collection):
    record = _record(registered_collection, {"image": 0.2, "tabular": 0.8})
    from dataclasses import replace
    item = next(e for e in record.evidence if e.category == "modality_outputs")
    interpretation = item.to_dict()["interpretation"]
    interpretation["target_label"] = "other-label"
    changed_item = replace(item, interpretation=interpretation)
    changed = replace(record, evidence=tuple(changed_item if e.category == item.category else e for e in record.evidence))
    result = _modality_jsd(changed, log_base=2)
    assert result.state.value in {"invalid", "not_ready"}
    assert result.value is None


def test_absent_modality_evidence_is_missing_not_zero(registered_collection):
    record = _record(registered_collection, {"image": 0.2, "tabular": 0.8})
    missing = EvidenceItem(record.association, record.source_key, "modality_outputs", "missing")
    changed = replace(
        record, evidence=tuple(missing if item.category == "modality_outputs" else item
                              for item in record.evidence),
    )
    result = _modality_jsd(changed, log_base=2)
    assert result.state.value == "missing"
    assert result.value is None


def test_per_modality_calibration_mismatch_is_rejected(registered_collection):
    record = _record(registered_collection, {"image": 0.2, "tabular": 0.8})
    item = next(value for value in record.evidence if value.category == "modality_outputs")
    interpretation = item.to_dict()["interpretation"]
    common = {key: interpretation[key] for key in (
        "target_label", "target_output", "output_space", "calibrated", "calibration_method", "timing_scope",
    )}
    other = dict(common, calibration_method="different-calibration")
    interpretation["modality_semantics"] = {"image": common, "tabular": other}
    altered_item = replace(item, interpretation=interpretation)
    changed = replace(record, evidence=tuple(
        altered_item if value.category == "modality_outputs" else value for value in record.evidence
    ))
    result = _modality_jsd(changed, log_base=2)
    assert result.state.value == "invalid"
    assert result.value is None
