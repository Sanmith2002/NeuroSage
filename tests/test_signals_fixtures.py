"""T001: Feature 004 fixtures remain synthetic and preserve patient grouping."""

from safira.collection import CollectionAssociation, collect_live
from safira.signals.records import SignalSourceKey

from signals_fixtures import make_synthetic_feature003_result


def test_fixture_builds_feature003_development_rows_without_splitting_groups(registered_collection):
    registry, register = registered_collection
    definition, _ = register(model_id="fixture-grouped", labels=("label-a", "label-b"), scores=(0.7, 0.3))
    association = CollectionAssociation(
        "opaque-synthetic-patient", "visit-1", "occurrence-1",
    )
    records = collect_live(
        registry, association,
        [(definition.model_id, "v1", "label-a"), (definition.model_id, "v1", "label-b")],
        {"synthetic-feature": [0.2]},
    ).records
    result = make_synthetic_feature003_result({
        "train": [(records[0], "group-opaque"), (records[1], "group-opaque")],
        "validation": [], "calibration": [],
    })
    rows = result.development.train
    assert {row.patient_group_ref for row in rows} == {"group-opaque"}
    assert {SignalSourceKey(*row.prediction.source_key).label_id for row in rows} == {"label-a", "label-b"}
    assert result.readiness.state == "ready"
    assert result.to_dict()["readiness"]["scope"] == "synthetic-only"
