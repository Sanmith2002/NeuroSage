"""T006: source scope remains independent for all Feature 001 configurations."""

from safira.signals.service import SignalExtractor

from signals_fixtures import SyntheticSignalVerifier, make_live_record, signal_protocol


def test_single_label_and_multi_label_predictions_keep_exact_identity(registered_collection):
    registry, register = registered_collection
    single_def, _, single = make_live_record(registry, register, model_id="single")
    multi_def, _, multi_a = make_live_record(
        registry, register, model_id="multi", labels=("label-a", "label-b"), scores=(0.2, 0.8),
    )
    assert len(single_def.labels) == 1
    assert len(multi_def.labels) == 2
    for record in (single, multi_a):
        verifier = SyntheticSignalVerifier()
        verifier.admit(record)
        result = SignalExtractor(
            registry, signal_protocol(record.source_key, {"bernoulli_entropy": {"log_base": 2}}), verifier,
        ).extract_record(record)[0]
        assert result.source_key.to_tuple() == record.source_key


def test_overlapping_labels_from_independent_models_are_not_merged(registered_collection):
    registry, register = registered_collection
    left_def, _, left = make_live_record(registry, register, model_id="left", labels=("shared",))
    right_def, _, right = make_live_record(registry, register, model_id="right", labels=("shared",), scores=(0.9,))
    values = []
    for record in (left, right):
        verifier = SyntheticSignalVerifier()
        verifier.admit(record)
        values.extend(SignalExtractor(
            registry, signal_protocol(record.source_key, {"bernoulli_entropy": {"log_base": 2}}), verifier,
        ).extract_record(record))
    assert left_def.model_id != right_def.model_id
    assert len(values) == 2
    assert [value.source_key.model_id for value in values] == ["left", "right"]
