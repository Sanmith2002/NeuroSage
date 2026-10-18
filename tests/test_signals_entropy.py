"""T008: registered binary probability entropy semantics and edge cases."""

import math

import pytest

from safira.signals.stateless import _bernoulli_entropy

from signals_fixtures import make_live_record


@pytest.mark.parametrize("probability,expected", [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)])
def test_entropy_base_two_boundaries(registered_collection, probability, expected):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register, model_id=f"entropy-{probability}", scores=(probability,))
    result = _bernoulli_entropy(record, log_base=2)
    assert result.value == pytest.approx(expected)
    assert result.method_parameters == {"log_base": 2}
    assert result.meaning == "Bernoulli predictive entropy in bits; not correctness or reliability."
    assert "primary_output" in result.evidence_sources


def test_entropy_natural_log_matches_formula(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register, model_id="entropy-natural", scores=(0.25,))
    result = _bernoulli_entropy(record, log_base="e")
    expected = -0.25 * math.log(0.25) - 0.75 * math.log(0.75)
    assert result.value == pytest.approx(expected)


@pytest.mark.parametrize("base", [0, 1, -2, "10", True])
def test_invalid_log_base_rejected(registered_collection, base):
    registry, register = registered_collection
    _, _, record = make_live_record(registry, register)
    with pytest.raises(ValueError):
        _bernoulli_entropy(record, log_base=base)


def test_entropy_rejects_non_probability_score_without_value(registered_collection):
    registry, register = registered_collection
    _, _, record = make_live_record(
        registry, register, model_id="entropy-score", value_kinds=("continuous_score",), scores=(0.25,),
    )
    result = _bernoulli_entropy(record, log_base=2)
    assert result.state.value == "invalid"
    assert result.value is None
