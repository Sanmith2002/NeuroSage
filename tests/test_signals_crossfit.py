import hashlib
import pytest

from safira.signals.exceptions import SignalCompatibilityError, SignalProtocolError
from safira.signals.records import SignalMethodConfig, SignalSourceKey
from safira.signals.reference import (
    ReferenceCompatibilityKey,
    ReferenceFitConfig,
    ReferenceObservation,
    assign_group_folds,
    crossfit_knn,
)
from safira.signals import reference as reference_module


def fixture_rows(groups=None):
    key = SignalSourceKey("m", "v1", "label")
    names = groups or ["patient-a", "patient-a", "patient-b", "patient-b", "patient-c", "patient-d"]
    return tuple(
        ReferenceObservation(
            f"row-{index}", key, group, "embedding-v1", "preprocess-v1",
            (float(index), float(index % 2)), evidence_ref=f"evidence-{index}",
        )
        for index, group in enumerate(names)
    )


def fit_config(seed="one-approved-seed", folds=2):
    key = ReferenceCompatibilityKey(
        SignalSourceKey("m", "v1", "label"), "knn_distance", "v1",
        {"k": 1, "metric": "euclidean"}, "embedding-v1", "preprocess-v1",
        "dataset", "protocol", "1", "manifest", "cohort-main",
    )
    return ReferenceFitConfig(
        key, SignalMethodConfig("knn_distance", "v1", {"k": 1, "metric": "euclidean"}),
        folds, seed,
    )


def expected_fold(group, seed, fold_count):
    digest = hashlib.sha256(seed.encode() + b"\0" + group.encode()).digest()
    return int.from_bytes(digest, "big") % fold_count


def test_hash_fold_assignment_uses_exact_documented_seed_rule_and_is_deterministic(monkeypatch):
    groups = ("g1", "g2", "g1", "g3")
    expected = {group: expected_fold(group, "approved", 3) for group in set(groups)}
    original_sha256 = hashlib.sha256
    hashed_inputs = []

    def record_hash(value):
        hashed_inputs.append(value)
        return original_sha256(value)

    monkeypatch.setattr(reference_module.hashlib, "sha256", record_hash)
    result = assign_group_folds(groups, seed="approved", fold_count=3)
    assert result == assign_group_folds(groups, seed="approved", fold_count=3)
    assert result == expected
    # Exactly one deterministic assignment per unique group per call; there is
    # no candidate-seed loop or favorable-fold retry.
    assert len(hashed_inputs) == 2 * len(set(groups))
    assert set(hashed_inputs) == {b"approved\0g1", b"approved\0g2", b"approved\0g3"}


def test_all_visits_and_labels_of_a_group_stay_in_one_fold_and_are_excluded():
    rows = fixture_rows()
    outputs = crossfit_knn(rows, fit_config())
    assignments = {output.row_key: output.fold_id for output in outputs}
    group_by_row = {row.row_key: row.patient_group_ref for row in rows}
    fold_by_group = {}
    for row_key, fold in assignments.items():
        group = group_by_row[row_key]
        assert fold_by_group.setdefault(group, fold) == fold
    for output in outputs:
        own_group_keys = {r.row_key for r in rows if r.patient_group_ref == group_by_row[output.row_key]}
        assert own_group_keys.isdisjoint(output.reference_row_keys)


def test_grouping_changes_may_change_scores_but_never_self_inclusion():
    rows_a = fixture_rows(["p1", "p2", "p3", "p4", "p5", "p6"])
    rows_b = fixture_rows(["p1", "p1", "p3", "p4", "p5", "p6"])
    outputs_a = crossfit_knn(rows_a, fit_config())
    outputs_b = crossfit_knn(rows_b, fit_config())
    # Grouping can alter the fold and score; the contract does not require it
    # to improve or even change a score for every valid fixture.
    assert any(a.fold_id != b.fold_id for a, b in zip(outputs_a, outputs_b))
    for rows, outputs in ((rows_a, outputs_a), (rows_b, outputs_b)):
        by_key = {row.row_key: row for row in rows}
        for output in outputs:
            group_keys = {r.row_key for r in rows if r.patient_group_ref == by_key[output.row_key].patient_group_ref}
            assert group_keys.isdisjoint(output.reference_row_keys)


def test_crossfit_rerun_is_identical_with_same_rows_and_protocol():
    rows = fixture_rows()
    assert crossfit_knn(rows, fit_config()) == crossfit_knn(rows, fit_config())


def test_too_few_groups_or_infeasible_reference_yields_non_value():
    outputs = crossfit_knn(fixture_rows(["only", "only"]), fit_config(folds=2))
    assert outputs
    assert all(output.state == "insufficient_evidence" and output.value is None for output in outputs)


def test_group_reference_names_do_not_appear_in_crossfit_output_repr():
    rows = fixture_rows()
    outputs = crossfit_knn(rows, fit_config())
    rendered = repr(outputs)
    assert "patient-a" not in rendered
    assert "patient-b" not in rendered


def test_explicit_assignments_require_complete_unique_group_coverage():
    rows = fixture_rows(["g1", "g1", "g2", "g2"])
    cfg = fit_config()
    incomplete = type(cfg)(cfg.compatibility_key, cfg.method_config, cfg.fold_count,
                           cfg.seed, explicit_assignments={"g1": 0})
    with pytest.raises(SignalProtocolError, match="fold_assignments_incomplete"):
        crossfit_knn(rows, incomplete)


def test_same_patient_group_has_same_hash_fold_across_contributors_and_labels():
    # Fold assignment keys only on the verified group reference, so all source
    # combinations share one fold without pooling their reference observations.
    result = assign_group_folds(("shared-group", "shared-group", "other-group"),
                                seed="approved", fold_count=3)
    assert result["shared-group"] == expected_fold("shared-group", "approved", 3)


def test_mixed_source_rows_are_not_pooled_into_one_reference():
    rows = list(fixture_rows(["shared", "shared", "other", "other"]))
    rows[1] = ReferenceObservation("different-contributor", SignalSourceKey("other", "v1", "label"),
                                   "shared", "embedding-v1", "preprocess-v1", (1.0, 1.0),
                                   evidence_ref="different-source-evidence")
    with pytest.raises(SignalCompatibilityError) as exc_info:
        crossfit_knn(tuple(rows), fit_config())
    assert "reference_source_mismatch" in str(exc_info.value)
