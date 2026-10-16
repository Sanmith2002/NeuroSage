"""Tests for Phase 2: cohort, labels, leakage matrix and frozen split.

Everything runs on synthetic data (``tests/fixtures/build_phase2_fixtures.py``
or small hand-made frames). No test reads PPMI data.
"""

from __future__ import annotations

import copy
import json
import re

import numpy as np
import pandas as pd
import pytest
import yaml

from copath.data import cohort, medications, split
from copath.data.merge import JoinError, left_join
from copath.data.sources import SourceError, SourceLoader
from copath.features import leakage_guard
from copath.phase2 import Paths, main, run_phase2
from copath.targets import builders

from .conftest_phase2 import isolated_paths
from .fixtures import build_phase2_fixtures as fx

CARDS = builders.load_cards(Paths().targets)
MATRIX = leakage_guard.load_matrix()
RULES = medications.DrugRules.from_yaml(Paths().drug_classes)
MED_CFG = yaml.safe_load(Paths().config.read_text(encoding="utf-8"))["sources"]["medications"]
L = builders.label_column


@pytest.fixture(scope="session")
def data_root(tmp_path_factory):
    return fx.build(tmp_path_factory.mktemp("phase2_data") / "download")


@pytest.fixture(scope="session")
def run(data_root, tmp_path_factory):
    """One full Phase 2 run on the synthetic download."""
    work = tmp_path_factory.mktemp("phase2_run")
    paths = isolated_paths(work)
    result = run_phase2(data_root, paths)
    frame = pd.read_parquet(paths.processed / "analytic_bl_v1.parquet")
    return {"paths": paths, "result": result, "frame": frame.set_index("PATNO", drop=False), "work": work}


def row(run, i: int) -> pd.Series:
    return run["frame"].loc[fx.pid(i)]


def report(run, name: str) -> pd.DataFrame:
    return pd.read_csv(run["paths"].reports / name, dtype=str, keep_default_na=False)


# ----------------------------------------------------------------- cohort

def test_one_row_per_participant_and_no_added_participants(run):
    frame = run["frame"]
    assert len(frame) == fx.N and frame["PATNO"].is_unique
    assert set(frame["PATNO"]) == set(fx.UNIVERSE_IDS)  # ids that exist only in source tables never enter
    assert not set(frame["PATNO"]) & set(fx.OUTSIDE_IDS)
    flow = (run["paths"].reports / "cohort_flow.md").read_text(encoding="utf-8")
    assert flow.count("| 600 | 600 |") == 8  # backbone and seven joins, none changing the count
    dev = pd.read_parquet(run["paths"].processed / "analytic_bl_v1_dev.parquet")
    assert len(dev) == 480 and "fold" in dev.columns and set(dev["fold"]) == {0, 1, 2, 3, 4}


def test_join_refuses_duplicate_keys_and_new_participants():
    base = pd.DataFrame({"PATNO": ["1", "2", "3"], "x": [1, 2, 3]})
    many = pd.DataFrame({"PATNO": ["1", "1", "2"], "y": [1, 2, 3]})
    with pytest.raises(JoinError):
        left_join(base, many, "many-to-one source", [])
    with pytest.raises(JoinError):
        left_join(pd.concat([base, base]), pd.DataFrame({"PATNO": ["1"], "y": [1]}), "duplicated backbone", [])
    with pytest.raises(JoinError):
        left_join(base, pd.DataFrame({"PATNO": ["1"], "x": [9]}), "clashing column", [])
    flow: list = []
    out = left_join(base, pd.DataFrame({"PATNO": ["2", "9"], "y": [5, 6]}), "extra participant in source", flow)
    assert list(out["PATNO"]) == ["1", "2", "3"] and out["y"].tolist()[1] == 5 and np.isnan(out["y"].tolist()[0])
    assert flow[0]["n_participants_after"] == 3 and flow[0]["n_matched_in_universe"] == 1


def test_pilot_and_deprecated_tables_are_never_read(data_root, run):
    loader = SourceLoader(data_root)
    with pytest.raises(SourceError):
        loader.find(["Pilot_Biospecimen_Analysis_Results*"])
    with pytest.raises(SourceError):
        loader.find(["*Biospecimen_Analysis_Results*"])  # a loose pattern still cannot reach the Pilot table
    assert run["frame"]["lumi_abeta42"].max() < 5000  # the Pilot file holds 999999
    used = json.loads((run["paths"].reports / "phase2_manifest.json").read_text(encoding="utf-8"))["source_tables"]
    assert used["lumipulse"]["table"] == "Current_Biospecimen_Analysis_Results_01Jun2024"
    assert not any("Pilot" in v["table"] or "Deprecated" in v["table"] for v in used.values())


def test_lumipulse_uses_project_283_csf_at_baseline_only(run):
    assert int(run["frame"]["lumi_abeta42"].notna().sum()) == 400
    values = run["frame"]["lumi_abeta42"].dropna()
    assert values.min() > 100  # not the V04 (1.0), plasma (2.0) or project 125 (3.0) rows
    assert np.isnan(row(run, 1)["lumi_abeta42"])


def test_drift_guard_stops_the_build(data_root, tmp_path):
    wrong = dict(fx.COUNTS, PD=249, HC=121)
    paths = isolated_paths(tmp_path, expected_counts=wrong)
    with pytest.raises(cohort.DriftError):
        run_phase2(data_root, paths)
    text = (paths.reports / "drift_report.md").read_text(encoding="utf-8")
    assert "Nothing was built" in text and "| PD | 249 | 250 |" in text
    assert not paths.processed.exists() and not paths.splits.exists()
    assert [p.name for p in paths.reports.iterdir()] == ["drift_report.md"]


def test_supine_bp_baseline_mean_and_screening_fallback(run):
    assert row(run, 3)["bp_source"] == "BL" and row(run, 3)["sup_sbp"] == 120 + 3 % 5 * 8  # the SC row (200) is ignored
    assert row(run, 7)["sup_sbp"] == 120 + 7 % 5 * 8 + 5  # two baseline readings: their mean
    assert row(run, 40)["bp_source"] == "SC_fallback" and row(run, 40)["sup_sbp"] == 120
    assert row(run, 20)["bp_source"] == "missing" and np.isnan(row(run, 20)["sup_sbp"])
    assert set(run["frame"]["bp_source"]) == {"BL", "SC_fallback", "missing"}


# ------------------------------------------------------------ target cards

def test_cards_are_complete_and_masked_differs_from_negative():
    assert set(CARDS) == set(builders.CARD_FILES)
    for name, card in CARDS.items():
        assert card["rule"]["masked"] != card["rule"]["negative"], name
    broken = copy.deepcopy(CARDS["pd_type_v1"])
    broken["rule"]["masked"] = broken["rule"]["negative"]
    with pytest.raises(builders.CardError):
        builders.validate_card(broken, "pd_type_v1")
    incomplete = copy.deepcopy(CARDS["vascular_v1"])
    del incomplete["eligible_population"]
    with pytest.raises(builders.CardError):
        builders.validate_card(incomplete, "vascular_v1")


def test_labels_keep_masked_distinct_from_negative(run):
    frame = run["frame"]
    for column in [c for c in frame.columns if c.startswith("label_")]:
        assert set(frame[column].dropna().unique()) <= {0.0, 1.0}, column
        assert frame[column].isna().any(), column  # every label has masked participants in the fixture
    pd_label = frame[L("pd_type_v1")]
    assert (pd_label[frame["cohort"] == "PD"] == 1).all() and (pd_label[frame["cohort"] == "HC"] == 0).all()
    assert pd_label[frame["cohort"].isin(["Prodromal", "SWEDD"])].isna().all()  # masked, never negative


def test_saa_conflicts_and_inconclusive_are_masked(run):
    table = pd.DataFrame({"PATNO": ["a", "a", "b", "b", "c", "d", "e", "e"],
                          "EV": ["BL", "BL", "BL", "BL", "BL", "V04", "BL", "V04"],
                          "ST": ["Positive", "Negative", "Positive", "Positive", "Inconclusive", "Positive", "Negative", "Positive"]})
    status = builders.saa_status_at_baseline(table, "EV", "ST", "BL").set_index("PATNO")["saa_status_bl"]
    assert status.to_dict() == {"a": "Conflicting", "b": "Positive", "c": "Inconclusive", "e": "Negative"}
    label = builders.pd_type_saa(status.reindex(["a", "b", "c", "d", "e"]), CARDS["pd_type_saa_v1"])
    assert np.isnan(label["a"]) and label["b"] == 1 and np.isnan(label["c"]) and np.isnan(label["d"]) and label["e"] == 0
    # in the full run: conflicting at BL -> masked; a later-visit result never decides the label
    assert row(run, 47)["saa_status_bl"] == "Conflicting" and np.isnan(row(run, 47)[L("pd_type_saa_v1")])
    assert row(run, 37)["saa_status_bl"] == "Inconclusive" and np.isnan(row(run, 37)[L("pd_type_saa_v1")])
    assert row(run, 31)["saa_n_results_bl"] == 2 and row(run, 31)[L("pd_type_saa_v1")] in (0, 1)
    assert np.isnan(row(run, 5)[L("pd_type_saa_v1")])  # no SAA at all


# ----------------------------------------------------------------- AD-like

def _elecsys(abeta, ptau, llod=(), ulod=(), pllod=()):
    n = len(abeta)
    return pd.DataFrame({"abeta": pd.Series(abeta, dtype=object), "ptau": pd.Series(ptau, dtype=object),
                         "abeta_LLOD": [int(i in llod) for i in range(n)], "abeta_ULOD": [int(i in ulod) for i in range(n)],
                         "ptau_LLOD": [int(i in pllod) for i in range(n)]})


def test_ad_like_formula_and_cutoff_come_from_the_card():
    assert CARDS["ad_like_v1"]["version"] == "v1.1" and builders.card_label(CARDS["ad_like_v1"]) == "ad_like_v1"
    params = builders.ad_like_parameters(CARDS["ad_like_v1"])
    assert (params["abeta_floor"], params["abeta_cap"], params["ptau_floor"], params["cutoff"]) == (200.0, 1475.4, 8.0, 0.025)
    assert params["abeta_flags"] == {"abeta_ULOD": 1475.4, "abeta_LLOD": 200.0} and params["ptau_flags"] == {"ptau_LLOD": 8.0}
    frame = _elecsys([1000.0, 1000.0], [24.0, 26.0])
    assert builders.ad_like(frame, CARDS["ad_like_v1"])["ad_like_v1"].tolist() == [0.0, 1.0]
    moved = copy.deepcopy(CARDS["ad_like_v1"])
    moved["rule"]["cutoff"] = 0.020  # the label follows the card, not a constant in the code
    assert builders.ad_like(frame, moved)["ad_like_v1"].tolist() == [1.0, 1.0]
    for section, key in (("rule", "cutoff"), ("preprocessing", "derived_value"), ("preprocessing", "abeta_used"),
                         ("preprocessing", "ptau_used")):
        broken = copy.deepcopy(CARDS["ad_like_v1"])
        del broken[section][key]
        with pytest.raises(builders.CardError, match=key):
            builders.ad_like(frame, broken)
    for key, value in (("abeta_cap", 1500), ("abeta_used", "min(abeta, 1700)")):
        inconsistent = copy.deepcopy(CARDS["ad_like_v1"])
        inconsistent["preprocessing"][key] = value
        with pytest.raises(builders.CardError):
            builders.ad_like_parameters(inconsistent)
    with pytest.raises(builders.CardError, match="abeta_LLOD"):
        builders.ad_like(frame.drop(columns="abeta_LLOD"), CARDS["ad_like_v1"])  # a flag the card names must exist


def test_ad_like_flag_based_limits_censoring_and_variants():
    card = CARDS["ad_like_v1"]
    frame = _elecsys(
        [None, None, 1000.0, None, 1000.0, 1000.0, 900.0, "bad", 1600.0, 0.0, None, 1000.0],
        [30.0, 20.0, None, 20.0, 25.0, 25.5, None, 20.0, 38.0, 20.0, None, 30.0],
        llod={1}, ulod={0, 10, 11}, pllod={2, 10})
    values = builders.ad_like_values(frame, builders.ad_like_parameters(card))
    assert values["abeta_used"][0] == 1475.4 and values["abeta_used"][1] == 200 and values["ptau_used"][2] == 8
    assert values["ratio"][0] == pytest.approx(30 / 1475.4) and values["ratio"][10] == pytest.approx(8 / 1475.4)
    assert values["abeta_used"][8] == 1475.4  # a numeric value beyond the limit is clamped
    assert values["abeta_used"][11] == 1000  # a measured value wins over a flag
    assert values["valid"].tolist() == [True, True, True, False, True, True, False, False, True, False, True, True]
    assert values["censored"].tolist() == [True, True, True, False, False, False, False, False, True, False, True, False]
    labels = builders.ad_like(frame, card)
    primary = labels["ad_like_v1"]
    assert primary[0] == 0  # flagged high ABeta42: amyloid-negative, no longer masked
    assert primary[1] == 1 and primary[2] == 0 and primary[10] == 0 and primary[11] == 1
    assert primary[[3, 6, 7, 9]].isna().all()  # no flag, non-numeric or <= 0: masked, never negative
    assert primary[4] == 0 and primary[5] == 1  # 0.025 is not above the cut-off; 0.0255 is
    assert set(labels) == {"ad_like_v1", "ad_like_v1_cut028", "ad_like_v1_cut022", "ad_like_v1_greyzone",
                           "ad_like_v1_uncensored", "ad_like_v1_amyloid_only"}
    uncensored = labels["ad_like_v1_uncensored"]
    assert uncensored[[0, 1, 2, 8, 10]].isna().all() and uncensored[[4, 5, 11]].tolist() == [0.0, 1.0, 1.0]
    assert labels["ad_like_v1_cut028"][8] == 0 and primary[8] == 1  # every variant uses the same limit rules
    assert labels["ad_like_v1_cut022"][0] == 0 and labels["ad_like_v1_cut022"][4] == 1
    assert np.isnan(labels["ad_like_v1_greyzone"][4]) and np.isnan(labels["ad_like_v1_greyzone"][5])  # inside +/-5%
    amyloid = labels["ad_like_v1_amyloid_only"]
    assert amyloid[0] == 0 and amyloid[1] == 1 and amyloid[6] == 1 and np.isnan(amyloid[3])
    counts = builders.ad_like_limit_counts(frame, card)
    assert counts["eligible: abeta boundary substitution 1475.4 from flag abeta_ULOD"] == 2
    assert counts["eligible: abeta boundary substitution 200 from flag abeta_LLOD"] == 1
    assert counts["eligible: ptau boundary substitution 8 from flag ptau_LLOD"] == 2
    assert counts["eligible: abeta numeric value at or beyond a limit (clamped)"] == 1
    assert counts["eligible: abeta or ptau is a boundary substitution (ad_like_v1_censored = 1)"] == 5
    assert counts["eligible: both abeta and ptau are boundary substitutions"] == 1


def test_ad_like_limits_in_the_full_run(run):
    frame = run["frame"]
    assert np.isnan(row(run, 20)["abeta"]) and row(run, 20)["abeta_ULOD"] == 1
    assert row(run, 20)["elecsys_ptau_abeta_ratio"] == pytest.approx(row(run, 20)["ptau"] / 1475.4)
    assert row(run, 20)[L("ad_like_v1")] == 0 and row(run, 20)["ad_like_v1_censored"] == 1
    assert row(run, 6)["elecsys_ptau_abeta_ratio"] == pytest.approx(8 / row(run, 6)["abeta"])
    assert row(run, 46)["elecsys_ptau_abeta_ratio"] == pytest.approx(8 / 200) and row(run, 46)[L("ad_like_v1")] == 1
    for masked in (1, 60, 80, 90):  # no CSF; 0; non-numeric; missing without a flag
        assert np.isnan(row(run, masked)[L("ad_like_v1")]) and row(run, masked)["ad_like_v1_censored"] == 0
    censored = frame["ad_like_v1_censored"] == 1
    assert censored.sum() > 20 and frame.loc[censored, L("ad_like_v1")].notna().all()
    assert frame.loc[censored, L("ad_like_v1_uncensored")].isna().all()
    assert frame.loc[~censored, L("ad_like_v1_uncensored")].equals(frame.loc[~censored, L("ad_like_v1")])
    text = (run["paths"].reports / "cohort_flow.md").read_text(encoding="utf-8")
    assert "boundary substitution" in text and "not the participant's true value" in " ".join(text.split())


# ------------------------------------------------------------ medications

def _dates(values):
    return medications.parse_partial_date(pd.Series(values))


def test_partial_dates():
    got = _dates(["03/2031", "2031-03-15", "3/15/2031", "Mar2031", "2031", "", "sometime", "13/2031"])
    assert got["kind"].tolist() == ["month", "month", "month", "month", "year", "missing", "unparseable", "unparseable"]
    assert got["month"].tolist()[:4] == [3, 3, 3, 3] and got["year"].tolist()[:5] == [2031] * 5


def _ongoing(start, stop, bl=(2031, 6)):
    n = len(start)
    out = medications.ongoing_at_baseline(_dates(start), _dates(stop), pd.Series([bl[0]] * n, dtype=float),
                                          pd.Series([bl[1]] * n, dtype=float))
    return out["ongoing"].tolist(), out["reason"].tolist()


def test_ongoing_at_baseline_rule():
    ongoing, reason = _ongoing(["06/2031", "07/2031", "01/2030", "01/2030", "01/2030", "01/2030"],
                               ["", "", "06/2031", "05/2031", "2031", "2030"])
    assert ongoing == [True, False, True, False, True, False]
    assert reason[1] == "started after baseline" and reason[3] == "stopped before baseline"
    assert reason[5] == "stopped before baseline"  # year-only stop before the baseline year


def test_year_only_and_ambiguous_dates():
    ongoing, reason = _ongoing(["2030", "2031", "2032", "", "sometime", "01/2030"], ["", "", "", "", "", "garbled"])
    assert ongoing == [True, False, False, False, False, False]
    assert reason[1] == "start year-only in the baseline year (ambiguous)"
    assert reason[2] == "started after baseline"
    assert reason[3] == reason[4] == "start date missing or unparseable"
    assert reason[5] == "stop date unparseable"
    ongoing, _ = _ongoing(["01/2030"], ["2031"])
    assert ongoing == [True]  # a year-only stop in the baseline year counts as ongoing


def _evidence(records):
    meds = pd.DataFrame(records, columns=["PATNO", "CMTRT", "WHODRUG", "STARTDT", "STOPDT", "CMINDC", "CMINDC_TEXT"]).astype(str)
    ids = sorted(set(meds["PATNO"]) | {"none"})
    baseline = pd.DataFrame({"PATNO": ids, "bl_year": 2031.0, "bl_month": 6.0})
    out, counts = medications.medication_evidence(meds, baseline, RULES, MED_CFG)
    return out.set_index("PATNO"), counts


def test_definite_conditional_and_excluded_drugs():
    out, counts = _evidence([
        ["definite", "LISINOPRIL 10 mg", "", "01/2030", "", "", ""],
        ["who", "tablet", "Amlodipine besylate", "01/2030", "", "", ""],          # named only in WHODRUG
        ["bb_tremor", "propranolol", "", "01/2030", "", "", "essential tremor"],
        ["bb_text", "Propranolol", "", "01/2030", "", "", "for hypertension"],
        ["bb_code", "metoprolol", "", "01/2030", "", "14", ""],
        ["bb_stopped", "metoprolol", "", "01/2030", "01/2031", "14", ""],
        ["alpha_htn", "doxazosin", "", "01/2030", "", "", "high blood pressure"],
        ["tamsulosin", "tamsulosin", "", "01/2030", "", "14", "hypertension"],
        ["silodosin", "Rapaflo", "", "01/2030", "", "14", "hypertension"],
        ["pressor", "midodrine", "", "01/2030", "", "14", "hypertension"],
        ["pressor2", "droxidopa and fludrocortisone", "", "01/2030", "", "14", "hypertension"],
        ["loop", "furosemide", "", "01/2030", "", "", "leg oedema"],
        ["clonidine", "clonidine", "", "01/2030", "", "", "HTN"],
        ["eye", "timolol propranolol", "", "01/2030", "", "", "ocular hypertension"],
        ["partial", "lisinoprilat research compound", "", "01/2030", "", "", ""],  # not a whole-word match
        ["statin", "Lipitor", "", "01/2030", "", "", ""],
        ["dm", "metformin", "", "01/2030", "", "", ""],
    ])
    definite, conditional = out["htn_med_definite"], out["htn_med_conditional"]
    assert definite["definite"] and definite["who"]
    assert not conditional["bb_tremor"] and conditional["bb_text"] and conditional["bb_code"]
    assert not conditional["bb_stopped"] and conditional["alpha_htn"] and conditional["clonidine"]
    for never in ("tamsulosin", "silodosin", "pressor", "pressor2", "loop", "eye", "partial"):
        assert not definite[never] and not conditional[never], never
    assert out.loc["statin", "dyslipid_med"] and out.loc["dm", "dm_med"]
    assert not out.loc["none", ["htn_med_definite", "htn_med_conditional", "dm_med", "dyslipid_med"]].any()
    assert not out.loc["none", "med_record_any"] and out.loc["definite", "med_record_any"]
    assert counts["conditional antihypertensive records ongoing without a hypertension indication (not counted)"] == 3


def test_drug_lists_have_explicit_include_conditional_exclude():
    raw = RULES.raw["components"]
    for component in ("htn", "dm", "dyslip"):
        assert set(raw[component]) == {"include", "conditional", "exclude"}
    assert {"tamsulosin", "silodosin", "midodrine", "fludrocortisone", "droxidopa"} == set(RULES.names("htn", "exclude"))
    conditional = set(RULES.names("htn", "conditional"))
    assert {"propranolol", "doxazosin", "furosemide", "clonidine"} <= conditional
    assert not conditional & {"tamsulosin", "silodosin"} and not set(RULES.names("htn", "include")) & conditional
    assert {"spironolactone", "triamterene", "hydralazine", "lisinopril", "losartan", "amlodipine",
            "hydrochlorothiazide", "eplerenone", "methyldopa", "aliskiren", "diltiazem", "verapamil"} <= set(
                RULES.names("htn", "include"))
    out, _ = _evidence([["a", "Inspra 25 mg", "", "01/2030", "", "", ""], ["b", "methyldopa", "", "01/2030", "", "", ""],
                        ["c", "ALISKIREN", "", "01/2030", "", "", "leg oedema"]])
    assert out.loc[["a", "b", "c"], "htn_med_definite"].all()  # definite: no indication needed


def test_medication_rules_in_the_full_run(run):
    assert row(run, 6)["htn_med_definite"] and row(run, 18)["dyslipid_med"] and row(run, 15)["dm_med"]
    assert not row(run, 11)["htn_med_conditional"]  # propranolol for tremor
    assert row(run, 22)["htn_med_conditional"]  # beta-blocker with the hypertension code
    assert not row(run, 26)["htn_med_definite"] and not row(run, 26)["htn_med_conditional"]  # tamsulosin
    assert not row(run, 23)["htn_med_definite"] and not row(run, 23)["htn_med_conditional"]  # midodrine
    assert not row(run, 34)["htn_med_definite"]  # year-only start in the baseline year
    assert not row(run, 19)["htn_med_definite"]  # stopped before baseline
    assert not row(run, 58)["dyslipid_med"] and not row(run, 82)["dm_med"]  # started after baseline; unparseable start
    assert not row(run, 1)["med_record_any"] and not row(run, 1)["htn_med_definite"]
    text = (run["paths"].reports / "cohort_flow.md").read_text(encoding="utf-8")
    assert "start year-only in the baseline year (ambiguous)" in text


# ---------------------------------------------------------------- vascular

def test_vascular_masking_only_when_htn_could_change_the_result():
    frame = pd.DataFrame({
        "sup_sbp": [150, 120, np.nan, np.nan, np.nan, np.nan, 120, np.nan],
        "sup_dbp": [80, 70, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        "htn_med_definite": [False, False, False, False, True, False, False, False],
        "htn_med_conditional": [False] * 8,
        "dm_med": [False, False, True, True, False, False, False, False],
        "dyslipid_med": [False, True, True, False, False, False, False, True],
    })
    out = medications.vascular_components(frame, 140, 90)
    assert out["htn_bp"].tolist()[:2] == [1.0, 0.0] and out["htn_bp"][2:6].isna().all() and np.isnan(out["htn_bp"][7])
    assert out["htn_bp"][6] == 0  # measured and below the threshold: 0, not missing
    assert out["htn_evaluable"].tolist() == [True, True, False, False, True, False, True, False]
    v1 = builders.vascular(out["vascular_component_count"], out["htn_evaluable"], CARDS["vascular_v1"])
    v2 = builders.vascular(out["vascular_component_count"], out["htn_evaluable"], CARDS["vascular_v2"])
    assert v1[0] == 0 and v2[0] == 1  # HTN only
    assert v1[1] == 0 and v2[1] == 1  # dyslipidaemia only, normal BP
    assert v1[2] == 1 and v2[2] == 1  # DM + DYSLIP = 2 without any BP: positive
    assert np.isnan(v1[3]) and v2[3] == 1  # DM + DYSLIP = 1, HTN unknown: v1 could go either way
    assert v1[4] == 0 and v2[4] == 1  # antihypertensive ongoing makes HTN evaluable without BP
    assert v1[5] == 0 and np.isnan(v2[5])  # DM + DYSLIP = 0, HTN unknown: v1 cannot reach 2; v2 undecidable
    assert v1[6] == 0 and v2[6] == 0  # one normal reading, nothing else
    assert np.isnan(v1[7]) and v2[7] == 1


def test_vascular_labels_in_the_full_run(run):
    frame = run["frame"]
    unknown, count = ~frame["htn_evaluable"], frame["vascular_component_count"]
    v1, v2 = frame[L("vascular_v1")], frame[L("vascular_v2")]
    assert unknown.sum() and v1[unknown & (count == 1)].isna().all() and (v1[unknown & (count == 0)] == 0).all()
    assert v1.isna().sum() == (unknown & (count == 1)).sum() and v2.isna().sum() == (unknown & (count == 0)).sum()
    assert np.isnan(row(run, 20)[L("vascular_v1")]) and row(run, 20)[L("vascular_v2")] == 1  # a statin, no BP
    assert (frame.loc[count >= 2, L("vascular_v1")] == 1).all() and (frame.loc[count >= 1, L("vascular_v2")] == 1).all()
    assert frame.loc[frame["sup_sbp"].notna(), "htn_bp"].notna().all() and frame.loc[frame["bp_source"] == "missing", "htn_bp"].isna().all()
    prevalence = report(run, "vascular_component_prevalence.csv")
    assert {"ALL", "PD", "HC", "Prodromal", "SWEDD"} == set(prevalence["cohort"])
    no_record = prevalence[(prevalence["measure"] == "no medication-log record, by vascular_v1") & (prevalence["cohort"] == "ALL")]
    assert set(no_record["value"]) == {"positive", "negative", "masked"} and set(no_record["n_in_group"]) == {"150"}


# ---------------------------------------------------------------- leakage

NEVER_EVERYWHERE = ["COHORT", "subgroup", "analytic_subgroup", "enroll_phase", "enroll_source", "PRIMDIAG", "NSD_Status",
                    "NSD_STAGE", "Clinical_Stage", "Stage_S", "CGI", "PGI", "LEDD", "PDTRTMNT", "duration", "agediag",
                    "ageonset", "sym_tremor", "sym_rigid", "td_pigd", "pm_any", "pm_cog_any", "study_status",
                    "Death_Status", "Death_Date", "age_death", "SITE", "visit_date", "YEAR", "EVENT_ID", "PATNO", "cohort",
                    "bl_year", "bl_month", "bp_source", "med_record_any", "fold"]
DEFINING = {
    "ad_like_v1": ["abeta", "tau", "ptau", "IU_ABeta42_CSF",
                   "IU_ABeta40_CSF", "IU_pTau181_CSF", "C2N_AB40", "C2N_AB42", "C2N_AB4240", "MTBR_TAU243",
                   "lumi_abeta42", "lumi_ratio_4240", "elecsys_ptau_abeta_ratio"],
    "ad_like_lumipulse_v1": ["abeta", "ptau", "IU_ABeta42_CSF", "lumi_abeta42", "lumi_abeta40", "lumi_ratio_4240"],
    "pd_type_saa_v1": ["CSFSAA", "asyn", "saa_status_bl"],
    "vascular_v1": ["orthostasis", "sup_sbp", "sup_dbp", "htn_bp", "htn_med_definite", "htn_med_conditional", "dm_med",
                    "dyslipid_med", "htn_evaluable", "comp_htn", "comp_dm", "comp_dyslip", "vascular_component_count"],
    "vascular_v2": ["orthostasis", "sup_sbp", "htn_bp", "dm_med", "dyslipid_med", "comp_htn"],
}
NEAR_PROXY = {
    "pd_type_v1": ["MIA_PUTAMEN_L", "MIA_CAUDATE_R", "MIA_STRIATUM_BILAT", "updrs3_score", "hy", "NHY",
                   "CSFSAA", "asyn", "saa_status_bl"],
    "pd_type_saa_v1": ["MIA_PUTAMEN_L", "updrs3_score", "hy"],
    "ad_like_v1": ["ptau217_plasma", "bd_tau_plasma", "Lilly_ptau217p"],
    "ad_like_lumipulse_v1": ["ptau217_plasma", "bd_tau_plasma"],
}


def test_assay_limit_flags_and_censoring_indicator_are_never_predictors_for_any_label():
    flags = ["abeta_LLOD", "abeta_ULOD", "ptau_LLOD", "tau_LLOD", "ad_like_v1_censored"]
    index = MATRIX.set_index("feature")
    for label in leakage_guard.labels(MATRIX):
        for feature in flags:
            assert index.loc[feature, label] == "never", (label, feature)
        for tier in leakage_guard.TIERS:
            assert not set(flags) & set(leakage_guard.tier_features(MATRIX, label, tier)), (label, tier)
    for label in leakage_guard.labels(MATRIX):  # the files the models read agree with the matrix
        for tier in leakage_guard.TIERS:
            listed = yaml.safe_load((leakage_guard.FEATURE_SETS_DIR / f"{label}_{tier}.yaml").read_text(encoding="utf-8"))["features"]
            assert not set(flags) & set(listed), (label, tier)
    assert leakage_guard.out_of_sync() == []
    with pytest.raises(leakage_guard.LeakageError):
        leakage_guard.assert_allowed(["age", "abeta_ULOD"], MATRIX, "pd_type_v1", "primary")


def test_the_limit_flags_still_build_the_ad_like_label_internally(run):
    frame = run["frame"]
    assert {"abeta_LLOD", "abeta_ULOD", "ptau_LLOD"} <= set(frame.columns)  # kept in the analytic table for the label
    assert row(run, 20)["abeta_ULOD"] == 1 and row(run, 20)[L("ad_like_v1")] == 0 and row(run, 20)["ad_like_v1_censored"] == 1


def test_defining_and_never_features_are_in_no_tier():
    labels = leakage_guard.labels(MATRIX)
    assert set(labels) == set(CARDS)
    for label in labels:
        blocked = set(MATRIX.loc[MATRIX[label].isin(["defining", "never"]), "feature"])
        for tier in leakage_guard.TIERS:
            chosen = set(leakage_guard.tier_features(MATRIX, label, tier))
            assert not chosen & blocked, (label, tier)
            assert not chosen & set(NEVER_EVERYWHERE), (label, tier)
            assert not any(f.startswith("label_") for f in chosen), (label, tier)
            assert not any(leakage_guard.MISSINGNESS_RE.search(f) for f in chosen), (label, tier)
        for feature in DEFINING.get(label, []):
            assert MATRIX.set_index("feature").loc[feature, label] == "defining", (label, feature)
    for feature in NEVER_EVERYWHERE:
        assert set(MATRIX.set_index("feature").loc[feature, labels]) <= {"never", "defining"}, feature


def test_near_proxies_are_absent_from_strict_and_tiers_follow_the_frozen_rules():
    index = MATRIX.set_index("feature")
    for label, features in NEAR_PROXY.items():
        strict = set(leakage_guard.tier_features(MATRIX, label, "strict"))
        for feature in features:
            assert index.loc[feature, label] == "near_proxy" and feature not in strict, (label, feature)
    assert leakage_guard.TIERS == ("primary", "strict")  # the full tier was dropped in Phase 2.1
    with pytest.raises(leakage_guard.LeakageError):
        leakage_guard.tier_features(MATRIX, "pd_type_v1", "full")
    assert {p.stem.rsplit("_", 1)[1] for p in leakage_guard.FEATURE_SETS_DIR.glob("*.yaml")} == {"primary", "strict"}
    for label in leakage_guard.labels(MATRIX):
        strict, primary = (leakage_guard.tier_features(MATRIX, label, t) for t in ("strict", "primary"))
        near = set(MATRIX.loc[MATRIX[label] == "near_proxy", "feature"])
        blocked = set(MATRIX.loc[MATRIX[label].isin(["defining", "never"]), "feature"])
        assert set(primary) == set(MATRIX["feature"]) - blocked  # primary = all minus defining and never
        assert set(strict) == set(primary) - near  # strict = primary minus near-proxies
    assert {"CSFSAA", "asyn"} <= set(leakage_guard.tier_features(MATRIX, "pd_type_v1", "primary"))


def test_leakage_guard_rejects_blocked_unknown_and_missingness_features():
    parents = builders.variant_parents(CARDS)
    assert parents["ad_like_v1_cut028"] == "ad_like_v1" and parents["vascular_v2"] == "vascular_v2"
    leakage_guard.assert_allowed(["age", "moca"], MATRIX, "ad_like_v1", "strict", parents)
    for features, label, tier in ((["age", "abeta"], "ad_like_v1", "primary"), (["COHORT"], "pd_type_v1", "primary"),
                                  (["CSFSAA"], "pd_type_v1", "strict"), (["ad_like_v1_censored"], "ad_like_v1", "primary"),
                                  (["ptau217_plasma"], "ad_like_v1_cut028", "strict"), (["sup_sbp"], "vascular_v2", "primary"),
                                  (["made_up_column"], "pd_type_v1", "primary"), (["moca_missing"], "pd_type_v1", "primary")):
        with pytest.raises(leakage_guard.LeakageError):
            leakage_guard.assert_allowed(features, MATRIX, label, tier, parents)
    leakage_guard.assert_allowed(["ptau217_plasma"], MATRIX, "ad_like_v1_cut028", "primary", parents)
    with pytest.raises(leakage_guard.LeakageError):
        leakage_guard.assert_columns_classified(MATRIX, ["age", "brand_new_column"])


def test_generated_leakage_files_match_the_matrix(tmp_path):
    assert leakage_guard.out_of_sync() == []  # docs/leakage_matrix.md and configs/feature_sets/ are generated, not edited
    for name in ("pd_type_v1_strict.yaml", "ad_like_v1_primary.yaml", "vascular_v2_strict.yaml"):
        text = (leakage_guard.FEATURE_SETS_DIR / name).read_text(encoding="utf-8")
        assert text.startswith(leakage_guard.GENERATED_HEADER)
        listed = yaml.safe_load(text)
        assert listed["features"] == leakage_guard.tier_features(MATRIX, listed["label"], listed["tier"])
    edited = tmp_path / "leakage_matrix.csv"
    MATRIX.assign(ad_like_v1=MATRIX["ad_like_v1"].where(MATRIX["feature"] != "moca", "never")).to_csv(edited, index=False)
    assert "ad_like_v1_strict.yaml" in leakage_guard.out_of_sync(edited)
    bad = tmp_path / "bad.csv"
    pd.concat([MATRIX, MATRIX.tail(1).assign(feature="moca_missing", pd_type_v1="safe")]).to_csv(bad, index=False)
    with pytest.raises(leakage_guard.LeakageError):
        leakage_guard.load_matrix(bad)


def test_every_analytic_column_is_classified(run):
    leakage_guard.assert_columns_classified(MATRIX, list(run["frame"].columns))
    summary = report(run, "feature_set_summary.csv")
    assert set(summary["tier"]) == set(leakage_guard.TIERS) and set(summary["label"]) == set(CARDS)
    strict = summary[(summary["label"] == "pd_type_v1") & (summary["modality"] == "ALL")].set_index("tier")
    assert int(strict.loc["strict", "n_features_in_dataset"]) < int(strict.loc["primary", "n_features_in_dataset"])


# ------------------------------------------------------------------ split

def test_split_has_no_overlap_and_is_stratified(run):
    splits = run["paths"].splits
    dev = set(split.load_ids(splits, "dev"))
    test_ids = set(pd.read_csv(splits / "split_v1_test_ids.csv", dtype=str)["PATNO"])
    assert not dev & test_ids and dev | test_ids == set(fx.UNIVERSE_IDS)
    assert len(dev) == 480 and len(test_ids) == 120
    folds = split.load_folds(splits)
    sizes = folds["fold"].value_counts()
    assert set(folds["PATNO"]) == dev and len(sizes) == 5 and sizes.max() - sizes.min() <= 2
    frame = run["frame"]
    in_test = frame["PATNO"].isin(test_ids)
    for cohort_name, share in frame["cohort"].value_counts(normalize=True).items():
        assert abs((frame.loc[in_test, "cohort"] == cohort_name).mean() - share) < 0.01
    for label in builders.PRIMARY_LABELS:
        overall = (frame[L(label)] == 1).mean()
        assert abs((frame.loc[in_test, L(label)] == 1).mean() - overall) < 0.02, label
    meta = json.loads((splits / "split_v1.json").read_text(encoding="utf-8"))
    used = " ".join(meta["stratification_indicators"])
    assert "pd_type_v1" in used and "ad_like_v1" in used and "vascular_v1" in used
    for sensitivity in ("saa", "lumipulse", "cut028", "cut022", "greyzone", "amyloid", "vascular_v2"):
        assert sensitivity not in used  # sensitivity labels never shape the split


def test_split_is_deterministic_and_frozen(run, data_root, tmp_path):
    again = isolated_paths(tmp_path / "again")
    run_phase2(data_root, again)
    for name in ("split_v1_dev_ids.csv", "split_v1_test_ids.csv", "split_v1_dev_folds.csv"):
        assert (again.splits / name).read_bytes() == (run["paths"].splits / name).read_bytes(), name
    assert pd.read_parquet(again.processed / "analytic_bl_v1.parquet").equals(run["frame"].reset_index(drop=True))
    first = json.loads((run["paths"].frozen / "lumipulse_gmm_v1.json").read_text(encoding="utf-8"))
    second = json.loads((again.frozen / "lumipulse_gmm_v1.json").read_text(encoding="utf-8"))
    assert first == second
    run_phase2(data_root, again)  # a second run against the frozen split verifies it and succeeds
    cfg = yaml.safe_load(again.config.read_text(encoding="utf-8"))
    cfg["seed"] = cfg["seed"] + 1
    again.config.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(split.SplitError):
        run_phase2(data_root, again)  # a different split is refused, not silently written
    run_phase2(data_root, again, refreeze=True)  # allowed while no model has been trained
    again.registry.parent.mkdir(parents=True, exist_ok=True)
    again.registry.write_text("run_id,stage\n", encoding="utf-8")
    run_phase2(data_root, again, refreeze=True)  # a registry without runs does not block
    again.registry.write_text("run_id,stage\ncv-pd_type_v1-primary-lr-s1,cv\n", encoding="utf-8")
    with pytest.raises(split.SplitError, match="refreeze refused"):
        run_phase2(data_root, again, refreeze=True)  # once a Phase 3 run exists, never again


def test_iterative_stratification_balances_every_indicator():
    rng = np.random.default_rng(0)
    y = np.column_stack([rng.random(1000) < p for p in (0.5, 0.2, 0.05, 0.02)])
    part = split.iterative_stratification(y, [0.8, 0.2], seed=1)
    assert abs((part == 1).mean() - 0.2) < 0.005
    for k in range(y.shape[1]):
        assert abs(y[part == 1, k].sum() - 0.2 * y[:, k].sum()) <= 1.0
    assert (part == split.iterative_stratification(y, [0.8, 0.2], seed=1)).all()
    assert (part != split.iterative_stratification(y, [0.8, 0.2], seed=2)).any()


def test_rare_strata_are_merged_not_left_as_singletons():
    n = 300
    ids = pd.Series([f"p{i:04d}" for i in range(n)])
    indicators = pd.DataFrame({
        "cohort_PD": [i < 200 for i in range(n)], "cohort_HC": [200 <= i < 293 for i in range(n)],
        "cohort_SWEDD": [293 <= i < 297 for i in range(n)], "cohort_Other": [i >= 297 for i in range(n)],
        "available_label_x": [True] * n, "positive_label_x": [i in (5, 150) for i in range(n)],
    })
    merged, notes = split.merge_sparse(indicators, 10)
    assert "cohort_other" in merged and int(merged["cohort_other"].sum()) == 7
    assert "cohort_SWEDD" not in merged and "positive_label_x" not in merged and len(notes) >= 2
    result = split.make_split(ids, indicators, seed=3)
    assert len(result["test_ids"]) == 60 and not set(result["dev_ids"]) & set(result["test_ids"])
    assert any("cohort_other" in note for note in result["notes"])
    rare = set(ids[293:])
    assert 0 < len(rare & set(result["test_ids"])) < len(rare)  # the merged stratum is shared between the parts
    shuffled = indicators.sample(frac=1, random_state=1)
    again = split.make_split(ids[shuffled.index], shuffled, seed=3)
    assert again["test_ids"] == result["test_ids"]  # independent of input row order


def test_test_set_access_guard(run, monkeypatch):
    paths = run["paths"]
    monkeypatch.delenv(split.FINAL_EVALUATION_ENV, raising=False)
    with pytest.raises(split.TestSetAccessError):
        split.load_ids(paths.splits, "test")
    with pytest.raises(split.TestSetAccessError):
        split.load_ids(paths.splits, "test", final_evaluation=True)  # the flag alone is not enough
    with pytest.raises(split.TestSetAccessError):
        split.load_analytic(paths.processed, paths.splits, "test")
    dev = split.load_analytic(paths.processed, paths.splits)
    assert len(dev) == 480 and set(dev["PATNO"]) == set(split.load_ids(paths.splits))
    monkeypatch.setenv(split.FINAL_EVALUATION_ENV, "1")
    with pytest.raises(split.TestSetAccessError):
        split.load_ids(paths.splits, "test")  # the environment alone is not enough either
    held_out = split.load_analytic(paths.processed, paths.splits, "test", final_evaluation=True)
    assert len(held_out) == 120 and not set(held_out["PATNO"]) & set(dev["PATNO"])


# -------------------------------------------------------------- Lumipulse

def test_lumipulse_threshold_fitted_on_development_only_and_direction(run):
    frame, paths = run["frame"], run["paths"]
    frozen = json.loads((paths.frozen / "lumipulse_gmm_v1.json").read_text(encoding="utf-8"))
    dev = frame["PATNO"].isin(split.load_ids(paths.splits))
    assert frozen["n_development_participants"] == int(frame.loc[dev, "lumi_ratio_4240"].notna().sum())
    assert 0.05 < frozen["threshold_ratio"] < 0.10  # between the two synthetic modes
    refit = builders.fit_lumipulse_threshold(frame.loc[dev, "lumi_ratio_4240"], frozen["seed"])
    assert refit["threshold_ratio"] == pytest.approx(frozen["threshold_ratio"])
    everyone = builders.fit_lumipulse_threshold(frame["lumi_ratio_4240"], frozen["seed"])
    assert everyone["threshold_ratio"] != pytest.approx(frozen["threshold_ratio"], rel=1e-9)  # test rows were not used
    label, ratio = frame[L("ad_like_lumipulse_v1")], frame["lumi_ratio_4240"]
    assert (label[ratio < frozen["threshold_ratio"]] == 1).all() and (label[ratio >= frozen["threshold_ratio"]] == 0).all()
    assert label[ratio.isna()].isna().all()
    assert ratio[label == 1].max() < ratio[label == 0].min()  # low ABeta42/ABeta40 = positive
    assert (frame.loc[~dev, L("ad_like_lumipulse_v1")].notna()).any()  # the frozen threshold was applied to the test set
    with pytest.raises(builders.CardError):
        builders.fit_lumipulse_threshold(ratio.dropna().head(10), 1)


# ------------------------------------------------------- reports, privacy

def test_reports_are_aggregate_and_suppressed(run):
    reports = run["paths"].reports
    names = {p.name for p in reports.iterdir()}
    assert names == {"cohort_flow.md", "label_prevalence_by_cohort.csv", "label_cooccurrence.csv", "split_balance.csv",
                     "feature_set_summary.csv", "vascular_component_prevalence.csv", "construct_check.csv",
                     "phase2_manifest.json"}
    ids = set(fx.UNIVERSE_IDS) | set(fx.OUTSIDE_IDS)
    for path in reports.iterdir():
        text = path.read_text(encoding="utf-8")
        assert not any(pid in text for pid in ids), path.name
        assert fx.FREE_TEXT_MARKER not in text and "/2031" not in text, path.name
    for name in names:
        if name.endswith(".csv"):
            frame = report(run, name)
            for column in [c for c in frame.columns if re.match(r"^n_(participants|eligible|masked|positive|negative|with|both|1|0)", c)]:
                assert not frame[column].isin(["1", "2", "3", "4"]).any(), (name, column)
    prevalence = report(run, "label_prevalence_by_cohort.csv")
    assert set(prevalence["split"]) == {"all", "development", "test"}
    assert {"pd_type_v1", "pd_type_saa_v1", "ad_like_v1", "ad_like_v1_cut028", "ad_like_v1_cut022", "ad_like_v1_greyzone",
            "ad_like_v1_uncensored", "ad_like_v1_amyloid_only", "ad_like_lumipulse_v1", "vascular_v1",
            "vascular_v2"} == set(prevalence["label"])
    one = prevalence[(prevalence["label"] == "pd_type_v1") & (prevalence["split"] == "all")].set_index("cohort")
    assert one.loc["ALL", "n_eligible"] == "370" and one.loc["ALL", "n_positive"] == "250"
    assert one.loc["Prodromal", "n_eligible"] == "0" and one.loc["Prodromal", "n_masked"] == "200"
    assert ("<5" in prevalence.to_csv()) or ("suppressed" in prevalence.to_csv())
    checks = report(run, "construct_check.csv")
    assert set(checks["computed_on"]) == {"development set only"} and len(checks) == 10
    assert len(report(run, "label_cooccurrence.csv")) == 15


def test_small_cells_are_suppressed_consistently():
    from copath import phase2

    assert phase2.S(3) == "<5" and phase2.S(0) == 0 and phase2.S(12) == 12
    assert phase2.part_of(48, 50) == "suppressed" and phase2.part_of(2, 50) == "<5" and phase2.part_of(20, 50) == 20
    frame = pd.DataFrame({"cohort": ["PD"] * 8 + ["HC"] * 8,
                          "label_a": [1, 1, 1, 0, 0, 0, 0, np.nan] * 2, "label_b": [1, 1, 1, 0, 0, 0, 0, 0] * 2})
    table = phase2.label_prevalence(frame, ["PD", "HC"], pd.Series([True] * 16))
    pd_row = table[(table["label"] == "a") & (table["cohort"] == "PD") & (table["split"] == "all")].iloc[0]
    # 3 positive and 4 negative of 7 eligible: each would reveal the other, so both are withheld
    assert pd_row["n_positive"] == "suppressed" and pd_row["n_negative"] == "suppressed" and pd_row["n_masked"] == "<5"
    assert pd_row["n_eligible"] == "suppressed" and pd_row["pct_positive_of_eligible"] == "suppressed"
    pairs = phase2.label_cooccurrence(frame, ["a", "b"])
    assert pairs.iloc[0]["n_11"] == 6 and pairs.iloc[0]["n_10"] == 0
    frame.loc[0, "label_b"] = 0
    assert set(phase2.label_cooccurrence(frame, ["a", "b"]).iloc[0][["n_11", "n_10", "n_01", "n_00"]]) == {"suppressed"}


def test_privacy_self_check_deletes_reports(data_root, tmp_path, monkeypatch):
    from copath import phase2

    def leaking(observed, flow, notes, limits, frame, lumipulse_note):
        return f"participant `{frame['PATNO'].iloc[0]}` leaked\n"

    monkeypatch.setattr(phase2, "cohort_flow_md", leaking)
    paths = isolated_paths(tmp_path)
    with pytest.raises(phase2.PrivacyCheckError) as caught:
        run_phase2(data_root, paths)
    assert fx.pid(1) not in str(caught.value)
    assert not [p for p in paths.reports.iterdir() if p.is_file()]


def test_cli_reports_drift_and_missing_data_root(tmp_path, monkeypatch, capsys, data_root):
    monkeypatch.delenv("PPMI_DATA_ROOT", raising=False)
    assert main([]) == 2 and "PPMI_DATA_ROOT" in capsys.readouterr().err
    # with the real frozen counts, the synthetic download is (correctly) reported as drift
    monkeypatch.setattr("copath.phase2.Paths", lambda: isolated_paths(tmp_path, expected_counts={"ALL": 5019, "PD": 1684,
                        "HC": 336, "Prodromal": 2935, "SWEDD": 64}))
    assert main(["--data-root", str(data_root)]) == 4
    assert "DRIFT" in capsys.readouterr().err


def test_real_configuration_carries_the_frozen_universe():
    cfg = yaml.safe_load(Paths().config.read_text(encoding="utf-8"))
    assert cfg["universe"]["expected_counts"] == {"ALL": 5019, "PD": 1684, "HC": 336, "Prodromal": 2935, "SWEDD": 64}
    assert cfg["forbidden_tables"] == ["Pilot_*", "Deprecated_*"] and cfg["sources"]["lumipulse"]["project"] == "283"
    assert CARDS["vascular_v1"]["rule"]["min_components"] == 2 and CARDS["vascular_v2"]["rule"]["min_components"] == 1
    assert "complete list of current medications" in " ".join(CARDS["vascular_v1"]["preprocessing"]["assumption"].split())


# ---------------------------------------------------- frozen GMM traceability

def test_frozen_gmm_hash_is_recorded_verified_and_never_regenerated_silently(data_root, tmp_path):
    from copath import phase2

    paths = isolated_paths(tmp_path)
    gmm, manifest_path = paths.frozen / phase2.GMM_FILE, paths.reports / phase2.MANIFEST_FILE

    def manifest() -> dict:
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def save(content: dict) -> None:
        manifest_path.write_text(json.dumps(content, indent=2, sort_keys=True), encoding="utf-8")

    run_phase2(data_root, paths)  # the very first freeze creates the file and records its hash
    original = gmm.read_bytes()
    assert manifest()[phase2.GMM_HASH_KEY] == phase2._sha256(gmm)
    first = manifest()[phase2.GMM_HASH_KEY]
    run_phase2(data_root, paths)  # successful verification of an existing, matching file
    assert gmm.read_bytes() == original and manifest()[phase2.GMM_HASH_KEY] == first

    gmm.write_bytes(original + b" \n")  # hash mismatch: the file was changed after the manifest recorded it
    with pytest.raises(split.SplitError, match="does not match") as caught:
        run_phase2(data_root, paths)
    assert "--refreeze" in str(caught.value) and gmm.read_bytes() == original + b" \n"  # nothing overwritten
    assert manifest()[phase2.GMM_HASH_KEY] == first
    gmm.write_bytes(original)

    gmm.unlink()  # missing file: not regenerated
    with pytest.raises(split.SplitError, match="missing") as caught:
        run_phase2(data_root, paths)
    assert "--refreeze" in str(caught.value) and not gmm.exists() and manifest()[phase2.GMM_HASH_KEY] == first
    gmm.write_bytes(original)
    run_phase2(data_root, paths)

    old = manifest()
    del old[phase2.GMM_HASH_KEY]  # a manifest written before this check
    save(old)
    with pytest.raises(split.SplitError, match="no recorded hash") as caught:
        run_phase2(data_root, paths)
    assert "--refreeze" in str(caught.value) and gmm.read_bytes() == original

    changed = json.loads(original)  # a different frozen file whose hash the manifest does record
    changed["threshold_ratio"] *= 1.5
    gmm.write_text(json.dumps(changed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    save({**old, phase2.GMM_HASH_KEY: phase2._sha256(gmm)})
    with pytest.raises(split.SplitError, match="differs from the frozen one"):
        run_phase2(data_root, paths)  # verification passes; the refitted threshold does not agree
    assert phase2._sha256(gmm) == manifest()[phase2.GMM_HASH_KEY] != first

    run_phase2(data_root, paths, refreeze=True)  # --refreeze refits, saves and records the new hash
    assert gmm.read_bytes() == original and manifest()[phase2.GMM_HASH_KEY] == first == phase2._sha256(gmm)
    gmm.unlink()
    save({k: v for k, v in manifest().items() if k != phase2.GMM_HASH_KEY})
    run_phase2(data_root, paths, refreeze=True)  # --refreeze also repairs a missing file and a missing hash
    assert gmm.is_file() and manifest()[phase2.GMM_HASH_KEY] == phase2._sha256(gmm)
    run_phase2(data_root, paths)


def test_cli_reports_a_missing_frozen_gmm_with_the_refreeze_instruction(data_root, tmp_path, monkeypatch, capsys):
    from copath import phase2

    paths = isolated_paths(tmp_path)
    run_phase2(data_root, paths)
    (paths.frozen / phase2.GMM_FILE).unlink()
    monkeypatch.setattr("copath.phase2.Paths", lambda: paths)
    assert main(["--data-root", str(data_root)]) == 1
    assert "--refreeze" in capsys.readouterr().err
