"""T008/T014: optional repeated-output dispersion requires declared repeat lineage."""

import pytest

from safira.adapters import AdapterCapabilities
from safira.signals.stateless import _repeated_output_variance

from signals_fixtures import make_live_record


def test_repeat_variance_records_exact_repeat_parameters(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(
        registry, register, model_id="repeat-model",
        capabilities=AdapterCapabilities(prediction_probability=True, repeated_outputs=True),
        evidence={"repeated_outputs": [0.2, 0.4, 0.6]},
        interpretations={"repeated_outputs": {
            "meaning": "synthetic repeated probabilities", "repeat_ids": ["r1", "r2", "r3"],
            "provenance": "synthetic-repeat-ledger", "same_input": True,
            "stochastic_mechanism": "synthetic-seed-stream-v1", "output_space": "probability",
            "target_label": "label-a", "calibrated": True,
            "calibration_method": "synthetic-calibration-v1",
        }},
    )
    result = _repeated_output_variance(record)
    assert result.value == pytest.approx(0.026666666666666666)
    assert result.method_parameters == {"ddof": 0, "repeat_count": 3}
    assert "repeated_outputs" in result.evidence_sources


def test_missing_repeat_provenance_is_unavailable_not_zero(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(
        registry, register, model_id="repeat-missing",
        capabilities=AdapterCapabilities(prediction_probability=True, repeated_outputs=True),
        evidence={"repeated_outputs": [0.2, 0.5]},
        interpretations={"repeated_outputs": {
            "meaning": "synthetic repeated probabilities", "repeat_ids": ["r1", "r2"],
            "provenance": "synthetic-repeat-ledger",
        }},
    )
    result = _repeated_output_variance(record)
    assert result.state.value == "not_ready"
    assert result.value is None
