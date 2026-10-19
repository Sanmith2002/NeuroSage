from safira.adapters import AdapterCapabilities
from safira.collection import EvidenceItem
from safira.signals.base import SignalDimension
from safira.signals.service import SignalExtractor
from safira.signals.stateless import _explanation_applicability

from signals_fixtures import make_live_record, signal_protocol
from signals_fixtures import SyntheticSignalVerifier


def test_explanation_metadata_is_traceable_and_never_a_numeric_reliability_score(registered_collection):
    registry, register = registered_collection
    _, _, original = make_live_record(registry, register,
                                      capabilities=AdapterCapabilities(prediction_probability=True,
                                                                      explanation=True))
    item = EvidenceItem(original.association, original.source_key, "explanation", "available",
        value={"feature": 0.3}, interpretation={"meaning": "synthetic explanation",
            "method": "synthetic-shap", "target_label": original.label_id,
            "target_output": "uncalibrated-margin", "output_space": "margin",
            "calibrated": False, "calibration_relation": "explains-pre-calibration-output"})
    record = type(original)(original.association, original.model_id, original.model_version,
        original.label_id, original.primary, original.provenance, (item,), original.component,
        original.input_verification)
    result = _explanation_applicability(record)
    assert result.dimension is SignalDimension.EXPLANATION_RELIABILITY
    assert result.state.value == "available"
    assert result.value["calibration_relation"] == "explains-pre-calibration-output"
    assert result.value["output_space"] == "margin"
    assert result.method_parameters["numeric_score"] is False
    assert not isinstance(result.value, (int, float))


def test_explanation_metadata_is_not_ready_when_not_supplied(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    result = _explanation_applicability(record)
    assert result.state.value == "unsupported"
    assert result.value is None
