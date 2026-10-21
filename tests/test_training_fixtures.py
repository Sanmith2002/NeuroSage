from tests.training_fixtures import build_inputs


def test_training_fixture_builds_exact_synthetic_single_binary_scope(registered_collection):
    registry, register = registered_collection
    definition, dataset, signals, reference = build_inputs(registry, register)

    assert definition.model_id == "training-model"
    assert definition.model_version == "v1"
    assert [(row.prediction.model_id, row.prediction.model_version, row.prediction.label_id)
            for row in dataset.development.train] == [("training-model", "v1", "label-a")] * 2
    assert len(signals.training) == len(dataset.development.train)
    assert reference.manifest_digest


def test_training_fixture_can_build_multilabel_and_independent_contributors(registered_collection):
    registry, register = registered_collection
    _, multi, multi_signals, _ = build_inputs(
        registry, register, model_id="multi", labels=("label-a", "label-b"),
        partitions={"train": (("g1", 1), ("g2", 0)), "validation": (), "calibration": ()},
    )
    _, other, other_signals, _ = build_inputs(
        registry, register, model_id="other", labels=("label-a",),
        partitions={"train": (("g3", 1),), "validation": (), "calibration": ()},
    )

    assert {row.prediction.label_id for row in multi.development.train} == {"label-a", "label-b"}
    assert len(multi_signals.training) == 2
    assert {row.prediction.model_id for row in other.development.train} == {"other"}
    assert len(other_signals.training) == 1


def test_fixture_ledger_requires_prior_independent_admission(registered_collection):
    from signals_fixtures import SyntheticSignalVerifier
    from tests.training_fixtures import SyntheticTrainingLedger

    registry, register = registered_collection
    _, dataset, signals, _ = build_inputs(registry, register)
    ledger = SyntheticTrainingLedger(SyntheticSignalVerifier())

    assert not ledger.has_admission(dataset, signals)
