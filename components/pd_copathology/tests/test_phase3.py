"""Tests for the Phase 3 training harness. Synthetic data only; no test reads PPMI data."""

from __future__ import annotations

import csv
import json
import shutil

import numpy as np
import pandas as pd
import pytest
import yaml

from copath.data import split
from copath.evaluation import metrics, selection
from copath.explain import shap_explainer
from copath.features import leakage_guard
from copath.models import baselines, candidates
from copath.models.preprocessing import DropDegenerateColumns
from copath.phase2 import registry_has_runs, run_phase2
from copath.phase3 import commands, final, reset
from copath.phase3.__main__ import main
from copath.phase3.core import Phase3Error, PrivacyCheckError, load_context, prepare, privacy_check, sha256, write_csv
from copath.targets import builders
from copath.training import registry, train, tuning

from .conftest_phase2 import isolated_paths
from .conftest_phase3 import phase3_paths
from .fixtures import build_phase2_fixtures as fx

FAST = {"candidates": ["lr_l2", "lr_enet", "hgb"], "hgb": {"max_iter": 20},
        "robustness": {"n_seeds": 2, "top_k": 10, "shap_rows_per_fold": 20},
        "ablation": {"modalities": ["DAT", "cognition", "vascular evidence"],
                     "clinical_demographics": ["cognition", "motor", "non-motor clinical", "demographics"]}}
MATRIX = leakage_guard.load_matrix()
SPEC = {"gates": {"slope_min": 0.7, "slope_max": 1.3}, "tolerances": {"slope": 0.05, "jaccard": 0.05, "strict_drop": 0.01},
        "simplicity": ["lr_l2", "lr_enet", "hgb", "rf", "xgb"]}


@pytest.fixture(scope="session")
def phase2(tmp_path_factory):
    work = tmp_path_factory.mktemp("phase3_input")
    paths = isolated_paths(work)
    run_phase2(fx.build(work / "download"), paths)
    return paths


def _paths(work, phase2, **changes):
    paths = phase3_paths(work, phase2, **{**FAST, **changes})
    shutil.copytree(phase2.processed, paths.processed)
    return paths


@pytest.fixture(scope="session")
def pipe(phase2, tmp_path_factory):
    """Commands 1-6 once, on the synthetic Phase 2 output."""
    paths = _paths(tmp_path_factory.mktemp("phase3_run"), phase2)
    for step in (commands.cmd_cv, commands.cmd_select_preliminary, commands.cmd_robustness, commands.cmd_select_final,
                 commands.cmd_extras, commands.cmd_explain):
        step(load_context(paths))
    return paths


def _report(paths, name):
    return pd.read_csv(paths.reports / name, dtype=str, keep_default_na=False)


def _rows(paths):
    return registry.read(paths.registry)


def _test_ids(paths):
    return set(pd.read_csv(paths.splits / "split_v1_test_ids.csv", dtype=str)["PATNO"])


# ---------------------------------------------------------------- pipeline

def test_commands_1_to_6_write_the_expected_reports(pipe):
    names = {p.name for p in pipe.reports.iterdir() if p.is_file()}
    assert {"baseline_results.csv", "candidate_results.csv", "leakage_checks.csv", "selection_preliminary.md",
            "robustness_tieset.csv", "shap_stability_tieset.csv", "selection_final.md", "modality_ablation.csv",
            "sensitivity_labels.csv", "calibration_comparison.csv", "shap_plausibility.csv", "shap_summary.md",
            "extras_notes.md"} <= names
    for label in builders.PRIMARY_LABELS:
        assert {f"shap_global_{label}.csv", f"shap_modality_{label}.csv", f"shap_dependence_{label}.csv"} <= names
    assert "final_test_results.csv" not in names and not pipe.lock.exists() and not pipe.approval.exists()
    assert {p.suffix for p in (pipe.reports / "figures").iterdir()} == {".png"}
    results = _report(pipe, "candidate_results.csv")
    assert set(results["model"]) == {"lr_l2", "lr_enet", "hgb"} and set(results["tier"]) == {"primary"}
    one = results[(results["label"] == "ad_like_v1") & (results["model"] == "lr_enet")]
    assert {"pooled", "mean", "sd", "se", "fold 0", "fold 4"} <= set(one["scope"])
    assert 0.5 < float(one[one["scope"] == "pooled"]["auroc"].iloc[0]) <= 1
    system = results[results["label"] == "ALL (macro over labels)"]
    assert len(system) == 3 and (system["hamming_loss"] != "").all() and (system["n_all_eligible"] != "").all()
    assert set(_report(pipe, "baseline_results.csv")["model"]) == {"b0a", "b0b"}
    prevalence = _report(pipe, "baseline_results.csv").query("model == 'b0a' and scope == 'pooled'")
    assert (prevalence["bss"].astype(float).abs() < 0.02).all()  # the prevalence baseline has no skill by construction
    leakage = _report(pipe, "leakage_checks.csv")
    assert set(leakage["check"]) == {"missingness-only model (AUROC)", "age + sex floor (AUPRC)"}
    calibration = _report(pipe, "calibration_comparison.csv")
    assert set(calibration["calibration"]) == {"sigmoid (selected)", "isotonic", "none"} and len(calibration) == 9
    sensitivity = _report(pipe, "sensitivity_labels.csv")
    assert {"pd_type_saa_v1", "ad_like_lumipulse_v1", "ad_like_v1_cut028", "ad_like_v1_cut022", "ad_like_v1_uncensored",
            "vascular_v2"} <= set(sensitivity["label"])
    assert sensitivity["analysis"].str.contains("medication-log record").sum() == 2
    ablation = _report(pipe, "modality_ablation.csv")
    assert "clinical + demographics only" in set(ablation["analysis"])
    vascular = ablation[(ablation["label"] == "vascular_v1") & (ablation["analysis"] == "without vascular evidence")]
    assert vascular["status"].iloc[0].startswith("not run")  # every vascular-evidence column defines that label
    notes = (pipe.reports / "extras_notes.md").read_text(encoding="utf-8")
    assert "Cognition does not strongly separate the biomarker groups at baseline" in notes
    summary = (pipe.reports / "shap_summary.md").read_text(encoding="utf-8")
    assert "uncalibrated" in summary and "monotonic" in summary and "SHAP / model-output space:" in summary


def test_each_candidate_family_gets_cv_runs_for_every_label(pipe):
    rows = [r for r in _rows(pipe) if r["stage"] == "cv"]
    for label in builders.PRIMARY_LABELS:
        assert {r["model"] for r in rows if r["label"] == label} == {"b0a", "b0b", "missingness", "lr_l2", "lr_enet", "hgb"}
    details = registry.load_details(pipe.runs, "cv-ad_like_v1-primary-lr_l2-s20261011")
    assert all(set(f["params"]) == {"C", "class_weight"} for f in details["folds"])


def test_registry_has_one_row_per_run_with_hashes(pipe):
    rows = _rows(pipe)
    assert len({r["run_id"] for r in rows}) == len(rows) and {r["stage"] for r in rows} == {"cv", "robustness", "extras"}
    with open(pipe.registry, newline="", encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == registry.COLUMNS
    for row in rows:
        assert all(len(row[h]) == 64 for h in registry.HASHES) and row["started_at"] and row["finished_at"]
        assert (pipe.runs / f"{row['run_id']}.json").is_file()
    assert registry_has_runs(pipe.registry)  # so `phase2 --refreeze` is refused from now on


def test_cv_uses_the_primary_tier_only_and_tiers_are_respected(pipe):
    rows = _rows(pipe)
    assert {r["tier"] for r in rows if r["stage"] == "cv"} == {"primary"}
    assert {r["tier"] for r in rows if r["stage"] == "robustness"} == {"primary", "strict"}
    for row in rows:
        details = registry.load_details(pipe.runs, row["run_id"])
        parent = builders.variant_parents(builders.load_cards(pipe.targets)).get(row["label"], row["label"])
        allowed = set(leakage_guard.tier_features(MATRIX, parent, row["tier"]))
        assert set(details.get("features", [])) <= allowed, row["run_id"]
        assert not any(f.startswith("label_") or f in ("PATNO", "fold", "cohort", "COHORT") for f in details.get("features", []))
    strict = registry.load_details(pipe.runs, [r["run_id"] for r in rows if r["tier"] == "strict" and r["label"] == "pd_type_v1"][0])
    assert not set(strict["features"]) & {"updrs3_score", "hy", "MIA_PUTAMEN_L", "CSFSAA", "asyn"}
    primary = registry.load_details(pipe.runs, "cv-pd_type_v1-primary-lr_enet-s20261011")
    assert {"updrs3_score", "CSFSAA"} <= set(primary["features"]) and "saa_status_bl" not in primary["features"]
    assert primary["nonnumeric_tier_features_not_used"] == ["saa_status_bl"]  # a text near-proxy: reported, not used
    with pytest.raises(leakage_guard.LeakageError):
        prepare(load_context(pipe), "ad_like_v1", "primary", features=["age", "abeta"])


def test_masked_participants_are_never_trained_on_or_scored(pipe):
    ctx = load_context(pipe)
    for row in _rows(pipe):
        if row["status"] != "ok":
            continue
        column = builders.label_column(row["label"])
        eligible = set(ctx.frame.loc[ctx.frame[column].notna(), "PATNO"].astype(str))
        oof = pd.read_parquet(pipe.oof / f"{row['run_id']}.parquet")
        assert set(oof["PATNO"]) <= eligible and oof["PATNO"].is_unique, row["run_id"]
        if row["stage"] == "cv":
            assert set(oof["PATNO"]) == eligible  # every eligible participant is predicted exactly once, out of fold
    data = prepare(ctx, "pd_type_v1", "primary")
    masked = set(ctx.frame.loc[ctx.frame["label_pd_type_v1"].isna(), "PATNO"].astype(str))
    assert masked and not set(data["ids"]) & masked and set(np.unique(data["y"])) == {0, 1}


def test_no_test_set_access_before_an_approved_final(pipe, monkeypatch):
    held_out = _test_ids(pipe)
    assert not set(load_context(pipe).frame["PATNO"].astype(str)) & held_out
    for path in list(pipe.oof.glob("*.parquet")) + list(pipe.shap.glob("*.parquet")):
        assert not set(pd.read_parquet(path)["PATNO"].astype(str)) & held_out, path.name

    def forbidden(*args, **kwargs):
        raise AssertionError("the test set was requested")

    monkeypatch.delenv(split.FINAL_EVALUATION_ENV, raising=False)
    with pytest.raises(split.TestSetAccessError):
        split.load_analytic(pipe.processed, pipe.splits, "test")  # the Phase 2 guard still holds
    monkeypatch.setattr(split, "_require_final_evaluation", forbidden)
    monkeypatch.setattr(split, "load_ids", forbidden)
    commands.cmd_cv(load_context(pipe))  # resumes from the registry; never asks for test identifiers or rows
    commands.cmd_select_preliminary(load_context(pipe))


def test_resume_skips_registered_runs_and_cv_is_deterministic(pipe, phase2, tmp_path):
    before = len(_rows(pipe))
    commands.cmd_cv(load_context(pipe))
    assert len(_rows(pipe)) == before  # nothing is run twice
    again = _paths(tmp_path / "again", phase2)
    commands.cmd_cv(load_context(again), labels=["ad_like_v1"], models=["lr_l2", "lr_enet", "hgb", "b0b"])
    assert {r["run_id"] for r in _rows(again)} == {f"cv-ad_like_v1-primary-{m}-s20261011" for m in ("lr_l2", "lr_enet", "hgb", "b0b")}
    for model in ("lr_l2", "lr_enet", "hgb"):
        name = f"cv-ad_like_v1-primary-{model}-s20261011.parquet"
        pd.testing.assert_frame_equal(pd.read_parquet(again.oof / name), pd.read_parquet(pipe.oof / name))
        assert registry.load_details(again.runs, name[:-8])["folds"][0]["params"] == registry.load_details(pipe.runs, name[:-8])["folds"][0]["params"]
    cfg = yaml.safe_load(again.config.read_text(encoding="utf-8"))
    cfg["seed"] += 1
    again.config.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    assert registry.find(again.registry, "cv-ad_like_v1-primary-lr_enet-s20261011", load_context(again).hashes) is None  # other config: not reused


def test_select_final_refuses_without_robustness_results(pipe, phase2, tmp_path):
    hidden = pipe.runs / "robustness-ad_like_v1-strict-lr_enet-s20261011.json"
    tie_set = json.loads((pipe.runs / "selection_preliminary.json").read_text(encoding="utf-8"))["labels"]["ad_like_v1"]["tie_set"]
    if "lr_enet" not in tie_set:
        hidden = pipe.runs / f"robustness-ad_like_v1-strict-{tie_set[0]}-s20261011.json"
    moved = tmp_path / hidden.name
    shutil.move(hidden, moved)
    try:
        with pytest.raises(Phase3Error, match="robustness results are missing"):
            commands.cmd_select_final(load_context(pipe))
    finally:
        shutil.move(moved, hidden)
    fresh = _paths(tmp_path / "fresh", phase2)
    with pytest.raises(Phase3Error, match="preliminary"):
        commands.cmd_robustness(load_context(fresh))
    with pytest.raises(Phase3Error, match="selected_models_v1.yaml"):
        commands.cmd_extras(load_context(fresh))


def test_selection_outputs_follow_the_protocol(pipe):
    selected = yaml.safe_load(pipe.selected.read_text(encoding="utf-8"))
    stage1 = json.loads((pipe.runs / "selection_preliminary.json").read_text(encoding="utf-8"))["labels"]
    assert set(selected["labels"]) == set(builders.PRIMARY_LABELS)
    for label, choice in selected["labels"].items():
        assert choice["model"] in stage1[label]["tie_set"] and choice["tier"] == "primary"
        assert choice["gates_passed"] == stage1[label]["gates_passed"] and choice["cv_run_id"].startswith("cv-")
        assert bool(choice["failed_gates"]) == (not choice["gates_passed"])
    text = (pipe.reports / "selection_final.md").read_text(encoding="utf-8")
    assert sha256(pipe.selected) in text and "Reasoning:" in text
    preliminary = (pipe.reports / "selection_preliminary.md").read_text(encoding="utf-8")
    assert "Tie set (within 1 SE)" in preliminary and "missingness-only AUROC" in preliminary
    stability = _report(pipe, "shap_stability_tieset.csv")
    primary = stability[stability["tier"] == "primary"]
    assert set(primary["n_rankings"]) == {"10"} and primary["shap_space"].str.contains("log-odds|probability").all()
    robustness = _report(pipe, "robustness_tieset.csv")
    assert set(robustness["tier"]) == {"primary", "strict"} and len(set(robustness["seed"])) == 2


# ------------------------------------------------------------ final (locked)

def test_final_is_locked_until_a_human_approves_then_runs_once(pipe, phase2, tmp_path, monkeypatch):
    monkeypatch.delenv(split.FINAL_EVALUATION_ENV, raising=False)
    paths = phase3_paths(tmp_path / "final", phase2, **FAST)
    for source, target in ((pipe.processed, paths.processed), (pipe.runs, paths.runs), (pipe.frozen, paths.frozen)):
        shutil.copytree(source, target)
    shutil.copy(pipe.registry, paths.registry)
    paths.config.write_text(pipe.config.read_text(encoding="utf-8"), encoding="utf-8")

    locked, real_load = {"on": True}, final.load_context

    def loaded(*args, **kwargs):
        assert not locked["on"], "data was loaded while the final evaluation was locked"
        return real_load(*args, **kwargs)

    monkeypatch.setattr(final, "load_context", loaded)
    for flag in (False, True):  # no flag; flag but no approval file
        with pytest.raises(final.FinalLockError):
            final.cmd_final(paths, final_flag=flag)
    approval = {"approved": False, "reviewer": "Synthetic Reviewer", "date": "2031-01-01", "selected_models_sha256": sha256(paths.selected)}
    for change in ({}, {"approved": True, "selected_models_sha256": "0" * 64}, {"approved": True, "reviewer": ""}, {"approved": "yes"}):
        paths.approval.write_text(yaml.safe_dump({**approval, **change}), encoding="utf-8")
        with pytest.raises(final.FinalLockError):
            final.cmd_final(paths, final_flag=True)
        with pytest.raises(final.FinalLockError):
            final.cmd_final(paths, final_flag=False)
    assert not paths.lock.exists() and not (paths.reports / "final_test_results.csv").exists()
    locked["on"] = False

    provisional = yaml.safe_load(paths.selected.read_text(encoding="utf-8"))["provisional_labels"]
    assert provisional  # the synthetic selection is provisional for at least one label
    paths.approval.write_text(yaml.safe_dump({**approval, "approved": True}), encoding="utf-8")
    with pytest.raises(final.FinalLockError, match="PROVISIONAL"):
        final.cmd_final(paths, final_flag=True)  # a valid approval alone does not unlock a provisional selection
    assert not paths.lock.exists()
    paths.approval.write_text(yaml.safe_dump({**approval, "approved": True, "acknowledge_provisional": provisional}), encoding="utf-8")
    final.cmd_final(paths, final_flag=True)
    assert split.FINAL_EVALUATION_ENV not in __import__("os").environ  # the switch is not left on
    results = _report(paths, "final_test_results.csv")
    assert set(builders.PRIMARY_LABELS) <= set(results["label"]) and {"value", "ci_low", "ci_high", "n_bootstrap"} <= set(results.columns)
    auroc = results[(results["metric"] == "auroc") & (results["label"] == "ad_like_v1")].iloc[0]
    assert float(auroc["ci_low"]) <= float(auroc["value"]) <= float(auroc["ci_high"])
    assert {"hamming_loss", "macro_f1_all_eligible"} <= set(results[results["label"].str.startswith("ALL (eligible")]["metric"])
    held_out = _test_ids(paths)
    for label in builders.PRIMARY_LABELS:
        folder = paths.models / "v1.0" / label
        assert {p.name for p in folder.iterdir()} == {"pipeline.joblib", "calibrator.joblib", "features.json", "config.json",
                                                      "metrics.json", "model_card.md"}
        assert len(json.loads((folder / "config.json").read_text(encoding="utf-8"))["label_card_sha256"]) == 64
        predictions = pd.read_parquet(paths.processed / "final" / f"test_predictions_{label}.parquet")
        assert set(predictions["PATNO"]) <= held_out and len(predictions)
    for path in paths.reports.rglob("*"):
        if path.suffix in (".csv", ".md"):
            assert not any(pid in path.read_text(encoding="utf-8") for pid in held_out), path.name
    lock = json.loads(paths.lock.read_text(encoding="utf-8"))
    assert lock["locked"] and len(lock["runs"]) == 1 and lock["runs"][0]["reviewer"] == "Synthetic Reviewer"
    assert {r["stage"] for r in _rows(paths)} >= {"final"}
    with pytest.raises(final.FinalLockError, match="already run"):
        final.cmd_final(paths, final_flag=True)  # a second run is refused
    with pytest.raises(final.FinalLockError):
        final.cmd_final(paths, final_flag=True, force=True, reason="  ")  # forcing needs a written reason
    assert final.check_unlocked(paths, True, force=True, reason="synthetic rerun")["approved"] is True
    with pytest.raises(Phase3Error, match="already run"):
        commands.cmd_select_final(load_context(paths))  # the selection cannot change after the final evaluation


def _provisional_setup(pipe, tmp_path, phase2):
    paths = phase3_paths(tmp_path / "prov", phase2, **FAST)
    for source, target in ((pipe.processed, paths.processed), (pipe.runs, paths.runs), (pipe.frozen, paths.frozen)):
        shutil.copytree(source, target)
    shutil.copy(pipe.registry, paths.registry)
    paths.config.write_text(pipe.config.read_text(encoding="utf-8"), encoding="utf-8")
    return paths


def test_provisional_labels_keep_final_locked_until_acknowledged(pipe, phase2, tmp_path, monkeypatch):
    monkeypatch.delenv(split.FINAL_EVALUATION_ENV, raising=False)
    paths = _provisional_setup(pipe, tmp_path, phase2)
    selection_file = yaml.safe_load(paths.selected.read_text(encoding="utf-8"))
    for choice in selection_file["labels"].values():
        choice["gates_passed"], choice["failed_gates"] = True, []
    selection_file["labels"]["ad_like_v1"].update(gates_passed=False, failed_gates=["G1 calibration slope"])
    selection_file["labels"]["vascular_v1"].update(gates_passed=False, failed_gates=["G3 beats age + sex (AUPRC)"])
    selection_file["provisional_labels"] = ["ad_like_v1", "vascular_v1"]
    paths.selected.write_text(yaml.safe_dump(selection_file, sort_keys=False), encoding="utf-8")
    base = {"approved": True, "reviewer": "Synthetic Reviewer", "date": "2031-01-01", "selected_models_sha256": sha256(paths.selected)}
    for acknowledge, text in ((None, "ad_like_v1, vascular_v1"), ([], "ad_like_v1, vascular_v1"), (["ad_like_v1"], "vascular_v1"),
                              (["vascular_v1"], "ad_like_v1")):
        paths.approval.write_text(yaml.safe_dump({**base, **({} if acknowledge is None else {"acknowledge_provisional": acknowledge})}),
                                  encoding="utf-8")
        with pytest.raises(final.FinalLockError, match="PROVISIONAL") as caught:
            final.check_unlocked(paths, True)
        assert text in str(caught.value)
    for bad, text in (("ad_like_v1", "must be a list"), (["ad_like_v1", "vascular_v1", "not_a_label"], "not in the selection")):
        paths.approval.write_text(yaml.safe_dump({**base, "acknowledge_provisional": bad}), encoding="utf-8")
        with pytest.raises(final.FinalLockError, match=text):
            final.check_unlocked(paths, True)
    paths.approval.write_text(yaml.safe_dump({**base, "acknowledge_provisional": ["vascular_v1", "ad_like_v1"]}), encoding="utf-8")
    assert final.check_unlocked(paths, True)["approved"] is True  # every provisional label acknowledged
    selection_file["labels"]["ad_like_v1"].update(gates_passed=True, failed_gates=[])
    selection_file["labels"]["vascular_v1"].update(gates_passed=True, failed_gates=[])
    selection_file["provisional_labels"] = []
    paths.selected.write_text(yaml.safe_dump(selection_file, sort_keys=False), encoding="utf-8")
    paths.approval.write_text(yaml.safe_dump({**base, "selected_models_sha256": sha256(paths.selected)}), encoding="utf-8")
    assert final.check_unlocked(paths, True)["approved"] is True  # no provisional label: the acknowledgement is not required


def test_selection_final_explains_why_a_label_is_provisional(pipe, phase2, tmp_path):
    selected = yaml.safe_load(pipe.selected.read_text(encoding="utf-8"))
    assert selected["provisional_labels"] == sorted(l for l, c in selected["labels"].items() if not c["gates_passed"])
    assert selected["provisional_labels"], "the synthetic data are expected to leave at least one label provisional"
    text = (pipe.reports / "selection_final.md").read_text(encoding="utf-8")
    for label in selected["provisional_labels"]:
        assert f"Why `{label}` is PROVISIONAL" in text and "acknowledge_provisional" in text
    assert "Calibration slope (gate: 0.7 to 1.3)" in text and "Gates failed, by number of candidates" in text
    assert "Provisional labels:" in text
    for label, choice in selected["labels"].items():
        if choice["gates_passed"]:
            assert f"Why `{label}` is PROVISIONAL" not in text


def test_cli_final_is_locked_without_loading_anything(monkeypatch, capsys, tmp_path):
    from copath.phase3.core import Paths

    monkeypatch.setattr(final, "load_context", lambda *a, **k: (_ for _ in ()).throw(AssertionError("data was loaded")))
    monkeypatch.setattr(final, "Paths", lambda: Paths(frozen=tmp_path / "frozen"))
    assert main(["final"]) == 5 and "LOCKED" in capsys.readouterr().err
    assert main(["final", "--final"]) == 5  # no selection and no approval file: still locked
    assert not Paths().approval.exists() or Paths().selected.exists()  # this software never writes an approval file


# ------------------------------------------------------- nested CV mechanics

def _toy(n=240, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(n, 6)), columns=["age", "SEX", "a", "b", "c", "d"], index=[f"row{i}" for i in range(n)])
    y = (X["a"] + 0.8 * X["b"] + rng.normal(scale=0.3, size=n) > 0).astype(int).to_numpy()
    X.loc[X.index[::7], "c"] = np.nan
    X.loc[X.index[::5], "a"] = np.nan
    return X, y, np.arange(n) % 5


CFG = {"tuning": {"inner_folds": 3, "trials": {"lr_l2": 2, "lr_enet": 2, "rf": 2, "xgb": 2, "hgb": 2}}, "calibration": {"method": "sigmoid", "cv": 3},
       "hgb": {"max_iter": 20}, "n_jobs": 2}


def test_preprocessing_and_tuning_only_see_training_rows(monkeypatch):
    X, y, folds = _toy()
    seen = []
    real = tuning.tune

    def spy(model, X_train, y_train, seed, cfg):
        seen.append(set(X_train.index))
        return real(model, X_train, y_train, seed, cfg)

    monkeypatch.setattr(tuning, "tune", spy)
    out = train.outer_cv(X, y, folds, X.index.to_numpy(), "lr_enet", 1, CFG, keep_models=True)
    assert len(seen) == 5
    for k in range(5):
        test_rows, train_rows = set(X.index[folds == k]), X[folds != k]
        assert not seen[k] & test_rows and seen[k] == set(train_rows.index)  # tuning never sees the outer-test fold
        pipeline = out["models"][k]
        np.testing.assert_allclose(pipeline.named_steps["impute"].statistics_, train_rows.median().to_numpy())
        imputed = train_rows.fillna(train_rows.median())
        np.testing.assert_allclose(pipeline.named_steps["scale"].mean_, imputed.mean().to_numpy())
        assert not np.allclose(pipeline.named_steps["impute"].statistics_, X.median().to_numpy())  # not the whole-data medians
    oof = out["oof"]
    assert len(oof) == len(X) and oof["PATNO"].is_unique and set(oof.columns) >= {"p_cal", "p_uncal", "p_prev", "threshold", "pred"}
    for k, part in oof.groupby("fold"):
        assert part["p_prev"].nunique() == 1 and part["p_prev"].iloc[0] == pytest.approx(y[folds != k].mean())
        assert part["threshold"].nunique() == 1  # chosen once inside the outer-training set, applied to the test fold
    fixed = {k: out["folds"][k]["params"] for k in range(5)}
    monkeypatch.setattr(tuning, "tune", lambda *a, **k: (_ for _ in ()).throw(AssertionError("re-tuned")))
    again = train.outer_cv(X, y, folds, X.index.to_numpy(), "lr_enet", 1, CFG, fold_params=fixed)  # reuse: no re-tuning
    pd.testing.assert_frame_equal(again["oof"], oof)


def test_every_model_family_trains_and_shap_space_is_verified_not_assumed():
    X, y, folds = _toy(n=400)
    train_rows, test_rows = folds != 0, folds == 0
    spaces, cfg = {}, {**CFG, "tuning": {"inner_folds": 3, "trials": {"lr_l2": 6, "lr_enet": 6, "rf": 4, "xgb": 6, "hgb": 6}}}
    for model in ("lr_l2", "lr_enet", "rf", "xgb", "hgb"):
        out = train.fit_predict(model, X[train_rows], y[train_rows], X[test_rows], 3, cfg)
        assert out["p_cal"].shape == (test_rows.sum(),) and 0 < out["threshold"] < 1 and "class_weight" in out["params"]
        assert metrics.label_metrics(y[test_rows], out["p_cal"], np.full(test_rows.sum(), out["prevalence"]),
                                     out["p_cal"] >= out["threshold"])["auroc"] > 0.7
        steps = [name for name, _ in out["model"].steps]
        assert steps == {"lr_l2": ["drop", "impute", "scale", "model"], "lr_enet": ["drop", "impute", "scale", "model"],
                         "rf": ["drop", "impute", "model"]}.get(model, ["drop", "model"])
        shap = shap_explainer.explain(model, out["model"], X[train_rows], X[test_rows])
        assert shap["values"].shape == (test_rows.sum(), X.shape[1]) and shap["additivity_error"] < 1e-2
        spaces[model] = shap["space"]
        top = shap_explainer.mean_abs(shap["values"], list(X.columns)).sort_values(ascending=False).index[:2]
        assert top[0] in ("a", "b") and set(top) & {"a", "b"}  # the informative features lead the ranking
    assert spaces["rf"].startswith("probability")  # a random forest is NOT explained in log-odds
    assert all(spaces[m].startswith("log-odds") for m in ("lr_l2", "lr_enet", "xgb", "hgb"))
    for name in ("b0a", "b0b", "missingness"):
        out = train.fit_predict(name, X[train_rows], y[train_rows], X[test_rows], 3, CFG)
        assert out["params"] == {} and np.allclose(out["p_cal"], out["p_uncal"])  # baselines: not tuned, not calibrated
    constant = train.fit_predict("b0a", X[train_rows], y[train_rows], X[test_rows], 3, CFG)
    assert np.allclose(constant["p_cal"], y[train_rows].mean())
    with pytest.raises(train.FoldError):
        train.fit_predict("lr_enet", X[train_rows].head(8), np.array([1, 0, 0, 0, 0, 0, 0, 0]), X[test_rows], 3, CFG)
    failed = train.outer_cv(X.head(40), np.r_[np.ones(3), np.zeros(37)].astype(int), folds[:40], X.index[:40].to_numpy(), "hgb", 1, CFG)
    assert all(r["failed"] and r["error"] == "FoldError" for r in failed["folds"]) and failed["oof"].empty


def test_lr_l2_is_a_plain_l2_logistic_regression_tuned_on_c_and_class_weight_only():
    X, y, folds = _toy(n=400)
    pipeline = candidates.build("lr_l2", {"C": 0.5, "class_weight": "balanced"}, y, 1, CFG)
    assert [name for name, _ in pipeline.steps] == ["drop", "impute", "scale", "model"]  # the same fold-safe pipeline as lr_enet
    estimator = pipeline.named_steps["model"]
    assert estimator.C == 0.5 and estimator.class_weight == "balanced" and getattr(estimator, "l1_ratio", None) in (None, 0, 0.0)
    assert candidates.build("lr_l2", {"C": 1.0, "class_weight": "none"}, y, 1, CFG).named_steps["model"].class_weight is None
    fitted = pipeline.fit(X[folds != 0], y[folds != 0])
    assert (fitted.named_steps["model"].coef_ != 0).all()  # no sparsity: every feature keeps a coefficient (no L1 term)
    assert candidates.build("lr_enet", {"C": 1.0, "l1_ratio": 0.5, "class_weight": "none"}, y, 1, CFG).named_steps["model"].solver == "saga"
    assert "lr_l2" not in baselines.BASELINES and set(baselines.BASELINES) == {"b0a", "b0b"}  # baselines are not candidates
    out = train.outer_cv(X, y, folds, X.index.to_numpy(), "lr_l2", 1, CFG)
    assert len(out["oof"]) == len(X) and all(set(r["params"]) == {"C", "class_weight"} for r in out["folds"])


def test_search_spaces_match_the_specification():
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    for model, expected in (("lr_l2", {"C"}), ("lr_enet", {"C", "l1_ratio"}), ("rf", {"n_estimators", "max_depth", "min_samples_leaf", "max_features"}),
                            ("xgb", {"learning_rate", "max_depth", "min_child_weight", "subsample", "colsample_bytree",
                                     "reg_alpha", "reg_lambda", "n_estimators"}),
                            ("hgb", {"learning_rate", "max_depth", "max_leaf_nodes", "l2_regularization", "min_samples_leaf"})):
        study = optuna.create_study(sampler=optuna.samplers.TPESampler(seed=1))
        drawn = [candidates.suggest(study.ask(), model) for _ in range(40)]
        assert set(drawn[0]) == expected | {"class_weight"} and {d["class_weight"] for d in drawn} == {"none", "balanced"}
    cfg = yaml.safe_load(load_cfg().read_text(encoding="utf-8"))
    assert cfg["tuning"] == {"inner_folds": 3, "trials": {"lr_l2": 15, "lr_enet": 15, "rf": 25, "xgb": 25, "hgb": 25}}
    assert cfg["candidates"] == ["lr_l2", "lr_enet", "rf", "xgb", "hgb"] and cfg["selection"]["simplicity"] == [
        "lr_l2", "lr_enet", "hgb", "rf", "xgb"]
    assert candidates.CANDIDATES == tuple(cfg["candidates"]) and candidates.SIMPLICITY == tuple(cfg["selection"]["simplicity"])
    assert cfg["calibration"] == {"method": "sigmoid", "cv": 3} and cfg["main_tier"] == "primary"
    assert cfg["labels"] == builders.PRIMARY_LABELS and cfg["final"]["n_bootstrap"] == 1000 and cfg["robustness"]["n_seeds"] == 3


def load_cfg():
    from copath.phase3.core import Paths

    return Paths().config


# ------------------------------------------------------------------ metrics

def test_metrics():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.02, 0.98, 20000)
    y = (rng.uniform(size=p.size) < p).astype(int)
    prevalence = np.full(p.size, y.mean())
    good = metrics.label_metrics(y, p, prevalence, p >= 0.5)
    assert good["cal_slope"] == pytest.approx(1, abs=0.06) and good["cal_intercept"] == pytest.approx(0, abs=0.06)
    assert good["ece"] < 0.02 and good["bss"] > 0.2 and good["auroc"] > 0.8
    assert metrics.label_metrics(y, prevalence, prevalence, np.ones_like(y))["bss"] == pytest.approx(0)
    overconfident = metrics.label_metrics(y, 1 / (1 + np.exp(-3 * metrics.logit(p))), prevalence, p >= 0.5)
    assert overconfident["cal_slope"] == pytest.approx(1 / 3, abs=0.05) and overconfident["ece"] > good["ece"]
    assert np.isnan(metrics.calibration_slope_intercept(y, prevalence)[0])  # a constant prediction has no slope
    threshold = metrics.best_f1_threshold(np.array([0, 0, 1, 1, 1]), np.array([0.1, 0.4, 0.35, 0.8, 0.9]))
    assert threshold == pytest.approx(0.35)
    assert metrics.threshold_metrics([1, 1, 0, 0], [1, 0, 1, 0]) == {"f1": 0.5, "precision": 0.5, "recall": 0.5}
    oof = pd.DataFrame({"fold": np.arange(p.size) % 5, "y": y, "p_cal": p, "p_prev": prevalence, "pred": (p >= 0.5).astype(int)})
    summary = metrics.summarise(oof)
    assert set(summary) == {"pooled", "folds", "mean", "sd", "se"} and len(summary["folds"]) == 5
    assert summary["se"]["bss"] == pytest.approx(summary["sd"]["bss"] / np.sqrt(5))
    a = pd.DataFrame({"PATNO": list("abcdef"), "fold": [0, 0, 0, 1, 1, 1], "y": [1, 0, 1, 0, 1, 0], "pred": [1, 0, 0, 0, 1, 0]})
    b = pd.DataFrame({"PATNO": list("abcdxy"), "fold": [0, 0, 0, 1, 2, 2], "y": [1, 1, 0, 0, 1, 1], "pred": [1, 1, 0, 1, 1, 1]})
    multi = metrics.multilabel({"one": a, "two": b})
    assert multi["n_all_eligible"] == 4 and multi["hamming_loss"] == pytest.approx(2 / 8)  # only those eligible for both
    ci = metrics.bootstrap_ci(lambda i: {"mean": float(y[i].mean())}, len(y), 200, 1)
    assert ci["mean"][0] < y.mean() < ci["mean"][1]
    jaccard = shap_explainer.stability([pd.Series({"a": 3, "b": 2, "c": 1}), pd.Series({"a": 3, "b": 1, "c": 2})], top_k=2)
    assert jaccard["mean_jaccard"] == pytest.approx(1 / 3) and jaccard["n_rankings"] == 2
    bins = shap_explainer.dependence(pd.Series(np.arange(100.0)), np.arange(100.0), bins=10)
    assert len(bins) == 10 and (bins["n_in_bin"] == 10).all() and set(bins.columns) == {"bin", "n_in_bin", "mean_feature_value", "mean_shap"}
    assert shap_explainer.dependence(pd.Series([0.0] * 3 + [1.0] * 20), np.ones(23)).shape[0] == 1  # a bin of 3 is dropped


# ----------------------------------------------------------- selection rules

def _result(score, se=0.01, slope=1.0, brier=0.10, auprc=0.6, failed=0):
    return {"pooled": {"cal_slope": slope, "brier": brier, "auprc": auprc, "bss": score}, "mean": {"bss": score},
            "se": {"bss": se}, "n_failed_folds": failed}


B0A, B0B = {"pooled": {"brier": 0.20}}, {"pooled": {"auprc": 0.40}}


def test_gates_one_se_rule_and_reporting_of_failed_models():
    results = {"lr_enet": _result(0.300), "hgb": _result(0.305, se=0.02), "rf": _result(0.280), "xgb": _result(0.400, slope=1.5)}
    out = selection.preliminary(results, B0A, B0B, SPEC)
    assert out["best"] == "hgb" and out["tie_set"] == ["hgb", "lr_enet"] and out["gates_passed"]  # rf is more than 1 SE below
    assert "xgb" in out["table"] and out["table"]["xgb"]["gates"]["G1 calibration slope"] is False  # reported, not hidden
    for bad, gate in ((_result(0.5, slope=0.69), 0), (_result(0.5, brier=0.21), 1), (_result(0.5, auprc=0.40), 2),
                      (_result(0.5, failed=1), 3), (_result(0.5, slope=float("nan")), 0)):
        assert selection.gates(bad, B0A, B0B, SPEC)[selection.GATES[gate]] is False
    assert all(selection.gates(_result(0.5, slope=1.3), B0A, B0B, SPEC).values())  # the bounds are inclusive


def test_provisional_fallback_when_no_model_passes_every_gate():
    results = {"lr_enet": _result(0.30, slope=2.0), "hgb": _result(0.35, slope=2.0, auprc=0.3), "rf": _result(0.9, failed=2)}
    out = selection.preliminary(results, B0A, B0B, SPEC)
    assert out["provisional"] and not out["gates_passed"] and out["tie_set"] == ["lr_enet"]  # fewest failed gates; never a failed fold
    nothing = selection.preliminary({"lr_enet": _result(0.3, failed=1)}, B0A, B0B, SPEC)
    assert nothing["best"] is None and nothing["tie_set"] == []


def test_tie_breakers_are_applied_in_the_protocol_order():
    def evidence(slope, jaccard, drop):
        return {"slope_distance": slope, "jaccard": jaccard, "strict_drop": drop}

    assert selection.final_choice(["xgb"], {"xgb": evidence(0.9, 0.1, 0.9)}, SPEC)[0] == "xgb"
    chosen, why = selection.final_choice(["xgb", "lr_enet"], {"xgb": evidence(0.02, 0.2, 0.5), "lr_enet": evidence(0.20, 0.9, 0.0)}, SPEC)
    assert chosen == "xgb" and len(why) == 1 and why[0].startswith("(a)")  # (a) decides alone
    tied = {"xgb": evidence(0.02, 0.80, 0.5), "rf": evidence(0.05, 0.60, 0.0), "lr_enet": evidence(0.30, 0.99, 0.0)}
    chosen, why = selection.final_choice(["xgb", "rf", "lr_enet"], tied, SPEC)
    assert chosen == "xgb" and [w[:3] for w in why] == ["(a)", "(b)"]  # lr leaves at (a); (b) separates xgb and rf
    tied = {"xgb": evidence(0.02, 0.80, 0.005), "rf": evidence(0.05, 0.78, 0.100), "hgb": evidence(0.04, 0.79, 0.006)}
    chosen, why = selection.final_choice(["xgb", "rf", "hgb"], tied, SPEC)
    assert chosen == "hgb" and [w[:3] for w in why] == ["(a)", "(b)", "(c)", "(d)"]  # rf leaves at (c); simplicity decides
    same = {m: evidence(0.1, 0.5, 0.0) for m in ("xgb", "rf", "hgb", "lr_enet", "lr_l2")}
    assert selection.final_choice(["xgb", "rf", "hgb", "lr_enet", "lr_l2"], same, SPEC)[0] == "lr_l2"  # simplest of all
    assert selection.final_choice(["xgb", "rf", "hgb", "lr_enet"], same, SPEC)[0] == "lr_enet"
    assert selection.final_choice(["xgb", "rf", "hgb"], same, SPEC)[0] == "hgb"
    assert selection.final_choice(["xgb", "rf"], same, SPEC)[0] == "rf"


# ------------------------------------------------------------------ privacy

def test_reports_are_aggregate_and_checked_for_identifiers(pipe, phase2, tmp_path):
    ids = set(fx.UNIVERSE_IDS)
    for path in pipe.reports.rglob("*"):
        if path.suffix in (".csv", ".md", ".json"):
            text = path.read_text(encoding="utf-8")
            assert not any(pid in text for pid in ids), path.name
            assert "PATNO" not in text, path.name
    for name in ("candidate_results.csv", "sensitivity_labels.csv", "robustness_tieset.csv"):
        counts = _report(pipe, name)["n_eligible"]
        assert not counts.isin(["1", "2", "3", "4"]).any()
    for label in builders.PRIMARY_LABELS:
        bins = _report(pipe, f"shap_dependence_{label}.csv")
        assert (bins["n_in_bin"].astype(int) >= 5).all()  # binned means only, never a small bin
    for path in (pipe.oof, pipe.shap):
        assert pipe.processed in path.parents  # participant-level outputs live under the git-ignored data/processed
    paths = _paths(tmp_path / "leak", phase2)
    ctx = load_context(paths)
    kept = write_csv(ctx, [{"label": "x", "n_eligible": 480, "auroc": 0.7701}], "fine.csv")
    privacy_check(ctx)  # numbers in count and metric columns are not identifiers
    leaked = write_csv(ctx, [{"label": "x", "note": f"participant {ctx.frame['PATNO'].iloc[0]}"}], "leak.csv")
    with pytest.raises(PrivacyCheckError) as caught:
        privacy_check(ctx)
    assert str(ctx.frame["PATNO"].iloc[0]) not in str(caught.value) and not leaked.exists() and not kept.exists()


# ------------------------------------------- degenerate columns, failed trials, reset-cv

def _degenerate_toy(n=300):
    """The toy data plus an all-missing column, a constant column and one that is constant outside outer fold 0 only."""
    X, y, folds = _toy(n=n)
    X["allnan"] = np.nan
    X["const"] = 1.0
    X["late"] = np.where(folds == 0, np.arange(n) % 3, 0.0)  # constant in the training rows of folds 1-4, varying in fold 0
    return X, y, folds


@pytest.mark.parametrize("model", ["lr_l2", "lr_enet", "rf", "xgb", "hgb"])
def test_every_family_trains_with_all_nan_and_constant_columns_and_logs_the_dropped_ones(model):
    X, y, folds = _degenerate_toy()
    out = train.outer_cv(X, y, folds, X.index.to_numpy(), model, 2, CFG, keep_models=True)
    assert not any(r["failed"] for r in out["folds"]) and len(out["oof"]) == len(X)
    for r in out["folds"]:
        assert {"allnan", "const"} <= set(r["dropped_features"]) and r["n_dropped"] == len(r["dropped_features"])
        # "late" varies only in fold 0: it is constant in the training rows of outer fold 0 (dropped) and varies in the other folds' (kept)
        assert ("late" in r["dropped_features"]) == (r["fold"] == 0)
        assert all(isinstance(name, str) for name in r["dropped_features"])  # names only, no values
    assert out["models"][0].named_steps["drop"].dropped_ == out["folds"][0]["dropped_features"]


def test_the_transformer_is_fitted_on_training_rows_only_and_keeps_the_same_columns_afterwards():
    X, _, folds = _degenerate_toy()
    train_rows, valid_rows = X[folds == 1], X[folds == 0]  # "late" varies in the validation rows, not in the training rows
    assert valid_rows["late"].nunique() > 1 and train_rows["late"].nunique() == 1
    step = DropDegenerateColumns().fit(train_rows)
    assert set(step.dropped_) == {"allnan", "const", "late"}
    out = step.transform(valid_rows)  # still dropped although it varies here
    assert list(out.columns) == step.kept_ == [c for c in X.columns if c not in step.dropped_]
    reordered = step.transform(valid_rows[list(reversed(valid_rows.columns))])
    assert list(reordered.columns) == step.kept_  # by name
    again = DropDegenerateColumns().fit(valid_rows)
    assert "late" in again.kept_ and set(again.dropped_) == {"allnan", "const", "a"}  # ("a" is all missing in fold 0 of the toy data) another training set, another decision
    assert step.transform(valid_rows.to_numpy()).shape[1] == len(step.kept_)  # arrays work too


def test_shap_values_are_mapped_back_to_the_original_features_with_zero_for_dropped_columns():
    X, y, folds = _degenerate_toy(n=400)
    train_rows, test_rows = folds == 1, folds == 0
    for model in ("lr_l2", "rf", "xgb", "hgb"):
        out = train.fit_predict(model, X[train_rows], y[train_rows], X[test_rows], 3, CFG)
        assert {"allnan", "const", "late"} <= set(out["dropped"])
        shap = shap_explainer.explain(model, out["model"], X[train_rows], X[test_rows])
        assert shap["values"].shape == (test_rows.sum(), X.shape[1]) and shap["additivity_error"] < 1e-2
        importance = shap_explainer.mean_abs(shap["values"], list(X.columns))
        assert (importance[["allnan", "const", "late"]] == 0).all()
        assert importance.drop(["allnan", "const", "late"]).idxmax() in ("a", "b")


def test_a_failing_trial_is_counted_and_the_study_goes_on(monkeypatch):
    X, y, _ = _toy()
    real = candidates.build

    def build(model, params, y_train, seed, cfg=None):
        if params["class_weight"] == "balanced":
            raise ValueError("synthetic failure")
        return real(model, params, y_train, seed, cfg)

    monkeypatch.setattr(candidates, "build", build)
    out = tuning.tune("lr_l2", X, y, 1, {"tuning": {"inner_folds": 3, "trials": {"lr_l2": 12}}})
    assert 0 < out["n_failed_trials"] < 12 and out["trial_failures"] == {"ValueError": out["n_failed_trials"]}
    assert out["params"]["class_weight"] == "none"


def test_when_every_trial_fails_the_run_is_registered_as_failed_and_writes_no_metrics(phase2, tmp_path, monkeypatch, capsys):
    paths = _paths(tmp_path, phase2)
    ctx = load_context(paths)
    real = candidates.build

    def build(model, params, y_train, seed, cfg=None):
        if model == "hgb":
            raise ValueError("window shape cannot be larger than input array shape")
        return real(model, params, y_train, seed, cfg)

    monkeypatch.setattr(candidates, "build", build)
    label = builders.PRIMARY_LABELS[0]
    failed = commands.cmd_cv(ctx, [label], ["hgb", "lr_l2"])  # the other model is still run
    assert failed == [f"cv-{label}-primary-hgb-s{ctx.seed}"]
    log = capsys.readouterr().err
    assert f"ERROR {failed[0]} FAILED: label {label}, tier primary, model hgb" in log
    assert "all 2 Optuna trials failed for model hgb" in log and "ValueError x2" in log
    assert "window shape" not in log  # exception text is never logged, only its type
    rows = {r["run_id"]: r for r in _rows(paths)}
    bad, good = rows[failed[0]], rows[f"cv-{label}-primary-lr_l2-s{ctx.seed}"]
    assert bad["status"] == "failed" and bad["n_failed_folds"] == "5" and all(bad[m] == "" for m in registry.METRICS)
    assert good["status"] == "ok" and good["auroc"] != ""
    details = registry.load_details(paths.runs, failed[0])
    assert "summary" not in details and not (paths.oof / f"{failed[0]}.parquet").exists()
    assert (paths.oof / f"{good['run_id']}.parquet").is_file()
    monkeypatch.setattr(candidates, "build", real)  # a failed run is retried (not skipped) the next time
    assert commands.cmd_cv(load_context(paths), [label], ["hgb"]) == []
    assert {r["run_id"]: r["status"] for r in _rows(paths)}[failed[0]] == "ok"


def test_the_command_line_exits_with_4_when_a_cv_run_failed(phase2, tmp_path, monkeypatch):
    from copath.phase3 import __main__ as cli

    paths = _paths(tmp_path, phase2)
    monkeypatch.setattr(cli, "load_context", lambda: load_context(paths))
    monkeypatch.setattr(cli.commands, "cmd_cv", lambda ctx, labels, models: ["cv-x"])
    assert main(["cv"]) == 4


def test_dropped_features_are_reported_by_name_only(pipe):
    table = _report(pipe, "dropped_features.csv")
    assert list(table.columns) == ["label", "tier", "model", "fold", "n_dropped", "features"]
    assert set(table["label"]) == set(builders.PRIMARY_LABELS) and set(table["model"]) == {"lr_l2", "lr_enet", "hgb"}
    assert len(table) == 3 * 3 * 5
    for _, row in table.iterrows():
        listed = [f for f in row["features"].split("; ") if f]
        assert len(listed) == int(row["n_dropped"]) and all(not f.replace(".", "").replace("-", "").isdigit() for f in listed)
    details = registry.load_details(pipe.runs, f"cv-{builders.PRIMARY_LABELS[0]}-primary-lr_l2-s{load_context(pipe).seed}")
    assert all("dropped_features" in r and "n_failed_trials" in r for r in details["folds"])
    assert set(details["library_versions"]) >= {"scikit-learn", "numpy"}


def _cv_only(phase2, work):
    paths = _paths(work, phase2)
    commands.cmd_cv(load_context(paths), [builders.PRIMARY_LABELS[0]], ["b0a", "lr_l2"])
    return paths


def _snapshot(*folders):
    return {str(p): sha256(p) for folder in folders for p in sorted(folder.rglob("*")) if p.is_file()}


def test_reset_cv_removes_only_cv_outputs_and_leaves_phase2_and_the_split_alone(phase2, tmp_path):
    paths = _cv_only(phase2, tmp_path)
    assert (paths.reports / "dropped_features.csv").is_file() and any(paths.oof.iterdir()) and any(paths.runs.glob("cv-*.json"))
    untouched = _snapshot(paths.splits, paths.processed, phase2.reports)
    untouched = {k: v for k, v in untouched.items() if "oof" not in k}  # the oof folder is what gets removed
    with pytest.raises(Phase3Error, match="--confirm"):
        reset.cmd_reset_cv(paths, confirm=False, log=lambda m: None)
    assert registry.read(paths.registry) and any(paths.oof.iterdir())  # nothing is removed without --confirm
    found = reset.cmd_reset_cv(paths, confirm=True, log=lambda m: None)
    assert found["registry_rows"] == 2 and found["files"]
    assert registry.read(paths.registry) == [] and paths.registry.read_text(encoding="utf-8").strip().split(",") == registry.COLUMNS
    assert not list(paths.runs.glob("cv-*.json")) and not any(paths.oof.iterdir())
    for name in ("baseline_results.csv", "candidate_results.csv", "leakage_checks.csv", "dropped_features.csv"):
        assert not (paths.reports / name).exists()
    assert not list((paths.reports / "figures").glob("cv_curves_*.png"))
    now = {k: v for k, v in _snapshot(paths.splits, paths.processed, phase2.reports).items() if "oof" not in k}
    assert now == untouched  # Phase 2 outputs, the split and the Lumipulse threshold are byte-for-byte the same
    commands.cmd_cv(load_context(paths), [builders.PRIMARY_LABELS[0]], ["b0a"])  # and cv can be started again
    assert [r["status"] for r in registry.read(paths.registry)] == ["ok"]


def test_reset_cv_keeps_other_rows_but_refuses_when_derived_or_final_results_exist(phase2, tmp_path):
    paths = _cv_only(phase2, tmp_path)
    cv_rows = registry.read(paths.registry)
    registry.append(paths.registry, {"run_id": "robustness-x", "stage": "robustness", "label": "x", "status": "ok"})
    with pytest.raises(Phase3Error, match="derived from the cv runs"):
        reset.cmd_reset_cv(paths, confirm=True, log=lambda m: None)
    assert len(registry.read(paths.registry)) == len(cv_rows) + 1 and any(paths.oof.iterdir())  # nothing changed
    paths.registry.write_text(",".join(registry.COLUMNS) + "\n", encoding="utf-8")  # back to the cv rows only
    for row in cv_rows:
        registry.append(paths.registry, row)
    paths.frozen.mkdir(parents=True, exist_ok=True)
    paths.lock.write_text("{}", encoding="utf-8")
    with pytest.raises(Phase3Error, match="refused: the final evaluation has run"):
        reset.cmd_reset_cv(paths, confirm=True, log=lambda m: None)
    assert registry.read(paths.registry) == cv_rows and any(paths.oof.iterdir())
    paths.lock.unlink()
    registry.append(paths.registry, {"run_id": "final-x", "stage": "final", "label": "x", "status": "ok"})
    with pytest.raises(Phase3Error, match="refused: the final evaluation has run"):
        reset.cmd_reset_cv(paths, confirm=True, log=lambda m: None)
    assert len(registry.read(paths.registry)) == len(cv_rows) + 1 and any(paths.oof.iterdir())


def test_reset_cv_command_line_and_the_pipeline_version_in_the_configuration(phase2, tmp_path, monkeypatch):
    paths = _cv_only(phase2, tmp_path)
    monkeypatch.setattr(reset, "Paths", lambda: paths)
    assert main(["reset-cv"]) == 1 and registry.read(paths.registry)  # no --confirm: nothing removed
    assert main(["reset-cv", "--confirm"]) == 0 and registry.read(paths.registry) == []
    assert yaml.safe_load(load_cfg().read_text(encoding="utf-8"))["pipeline_version"] == 2  # old-pipeline runs are never reused
