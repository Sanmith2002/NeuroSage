"""Analytic baseline cohort: the curated-cut backbone plus the approved sources.

Backbone: PPMI Curated Data Cut, baseline visit, exactly one row per
participant. Every added source is first brought to participant level and then
left-joined with :func:`copath.data.merge.left_join`, which refuses any join
that would add rows or participants.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from ..targets import builders
from . import medications
from .merge import KEY, JoinError, assert_one_row_per_participant, left_join
from .sources import SourceLoader, find_column, to_number


class DriftError(RuntimeError):
    """The baseline universe differs from the frozen one."""

    def __init__(self, expected: dict, observed: dict) -> None:
        super().__init__("the baseline universe differs from the frozen universe")
        self.expected, self.observed = expected, observed


def _code(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.replace(r"\.0+$", "", regex=True)


def backbone(loader: SourceLoader, cfg: dict) -> pd.DataFrame:
    """Baseline rows of the curated cut, one per participant, with the cohort name added."""
    u = cfg["universe"]
    curated = loader.read("curated_cut", u["curated_table"], sheet_requires=[KEY, u["event_column"]])
    event = find_column(curated.columns, u["event_column"])
    frame = curated[curated[event] == u["baseline_event"]].reset_index(drop=True)
    assert_one_row_per_participant(frame, "curated cut at baseline")
    cohort_col = find_column(frame.columns, u["cohort_column"])
    frame["cohort"] = _code(frame[cohort_col]).map({str(k): v for k, v in u["cohort_codes"].items()}).fillna("UNKNOWN")
    return frame


def universe_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = {"ALL": int(len(frame))}
    counts.update({str(k): int(v) for k, v in frame["cohort"].value_counts().items()})
    return counts


def check_drift(frame: pd.DataFrame, cfg: dict) -> dict[str, int]:
    """Raise :class:`DriftError` unless the universe equals the frozen counts."""
    expected = {str(k): int(v) for k, v in cfg["universe"]["expected_counts"].items()}
    observed = universe_counts(frame)
    names = set(expected) | set(observed)
    if any(expected.get(n, 0) != observed.get(n, 0) for n in names):
        raise DriftError(expected, observed)
    return observed


def type_backbone(frame: pd.DataFrame, feature_columns: set[str]) -> tuple[pd.DataFrame, dict[str, int]]:
    """Make feature columns numeric; report how many non-numeric cells became missing (aggregate)."""
    out, coerced = frame.copy(), {}
    for column in frame.columns:
        if column in (KEY, "cohort"):
            continue
        text = frame[column].astype(str).str.strip()
        number = to_number(text)
        lost = int(((text != "") & number.isna()).sum())
        if column in feature_columns:
            out[column] = number
            if lost:
                coerced[column] = lost
        elif lost == 0:
            out[column] = number
        else:
            out[column] = text.replace("", None)
    return out, coerced


def _at_event(table: pd.DataFrame, event_column: str | None, event: str) -> pd.DataFrame:
    column = find_column(table.columns, event_column) if event_column else None
    return table if column is None else table[table[column] == event].drop(columns=[column])


def add_fs7(frame: pd.DataFrame, loader: SourceLoader, key: str, spec: dict, baseline_event: str, flow: list) -> pd.DataFrame:
    table = _at_event(loader.read(key, spec["table"]), spec.get("event_column"), baseline_event)
    values = table.drop(columns=[KEY]).apply(to_number)
    values.columns = [spec["prefix"] + re.sub(r"\W+", "_", c).strip("_") for c in values.columns]
    values.insert(0, KEY, table[KEY].to_numpy())
    return left_join(frame, values.reset_index(drop=True), key, flow)


def add_genetics(frame: pd.DataFrame, loader: SourceLoader, spec: dict, flow: list) -> pd.DataFrame:
    columns = list(spec["carrier_columns"])
    table = loader.read("genetics", spec["table"], columns=[KEY] + columns)
    out = table[[KEY]].copy()
    absent = {str(v).upper() for v in spec.get("missing_values", [""])}
    normal = {str(v).upper() for v in spec.get("non_carrier_values", ["0"])}
    for source, name in spec["carrier_columns"].items():
        value = table[source].astype(str).str.strip().str.upper()
        out[name] = np.where(value.isin(absent), np.nan, np.where(value.isin(normal), 0.0, 1.0))
    return left_join(frame, out, "genetics", flow)


def add_saa(frame: pd.DataFrame, loader: SourceLoader, spec: dict, baseline_event: str, flow: list) -> pd.DataFrame:
    table = loader.read("saa", spec["table"], columns=[KEY, spec["event_column"], spec["status_column"]])
    status = builders.saa_status_at_baseline(table, spec["event_column"], spec["status_column"], baseline_event)
    return left_join(frame, status, "saa", flow)


def add_lumipulse(frame: pd.DataFrame, loader: SourceLoader, spec: dict, baseline_event: str, flow: list,
                  notes: dict) -> pd.DataFrame:
    tests = {str(k): v for k, v in spec["tests"].items()}
    matrix = re.compile(spec["matrix_regex"])

    def keep(chunk: pd.DataFrame) -> pd.Series:
        return (
            (_code(chunk[spec["project_column"]]) == str(spec["project"]))
            & (chunk[spec["event_column"]] == baseline_event)
            & chunk[spec["test_column"]].isin(tests)
            & chunk[spec["matrix_column"]].map(lambda v: bool(matrix.search(v)))
        )

    needed = [KEY, spec["project_column"], spec["event_column"], spec["matrix_column"], spec["test_column"], spec["value_column"]]
    rows = loader.read("lumipulse", spec["table"], exclude=spec.get("exclude"), columns=needed, row_filter=keep)
    rows = rows.assign(value=to_number(rows[spec["value_column"]]), name=rows[spec["test_column"]].map(tests))
    notes["lumipulse BL results read (project 283, CSF)"] = int(len(rows))
    notes["lumipulse results not numeric (masked)"] = int(rows["value"].isna().sum())
    repeats = rows.dropna(subset=["value"]).groupby([KEY, "name"]).size()
    notes["participant-test pairs with more than one BL result (mean used)"] = int((repeats > 1).sum())
    wide = rows.groupby([KEY, "name"])["value"].mean().unstack("name")
    wide = wide.reindex(columns=list(tests.values())).reset_index()
    wide["lumi_ratio_4240"] = builders.lumipulse_ratio(wide["lumi_abeta42"], wide["lumi_abeta40"])
    return left_join(frame, wide, "lumipulse", flow)


def add_vascular_evidence(frame: pd.DataFrame, loader: SourceLoader, cfg: dict, rules: medications.DrugRules,
                          thresholds: dict, flow: list, notes: dict) -> pd.DataFrame:
    u, vit, med = cfg["universe"], cfg["sources"]["vital_signs"], cfg["sources"]["medications"]
    vitals = loader.read("vital_signs", vit["table"], columns=[KEY, vit["event_column"], vit["sbp"], vit["dbp"]])
    frame = left_join(frame, medications.supine_bp(vitals, frame[KEY], vit, u["baseline_event"]), "vital_signs", flow)
    meds = loader.read("medications", med["table"],
                       columns=[KEY, *med["name_columns"], med["start"], med["stop"], med["indication_code"], med["indication_text"]])
    evidence, counts = medications.medication_evidence(meds, frame[[KEY, "bl_year", "bl_month"]], rules, med)
    notes.update({f"medication log: {k}": v for k, v in counts.items()})
    frame = left_join(frame, evidence, "medications", flow)
    return medications.vascular_components(frame, float(thresholds["sbp"]), float(thresholds["dbp"]))


def build(loader: SourceLoader, cfg: dict, cards: dict, rules: medications.DrugRules, feature_columns: set[str],
          frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], dict]:
    """Add every approved source to the (already drift-checked) backbone."""
    u, sources = cfg["universe"], cfg["sources"]
    flow: list[dict] = [{"step": "backbone: curated cut at baseline", "n_participants_before": len(frame),
                         "n_participants_after": len(frame), "n_source_participants": len(frame),
                         "n_matched_in_universe": len(frame), "n_columns_added": len(frame.columns) - 1}]
    notes: dict = {}
    frame, coerced = type_backbone(frame, feature_columns)
    notes["curated-cut feature columns with non-numeric cells set to missing"] = len(coerced)
    notes["curated-cut non-numeric cells set to missing"] = int(sum(coerced.values()))
    when = medications.parse_partial_date(frame[find_column(frame.columns, u["baseline_date_column"])].fillna("").astype(str))
    frame["bl_year"], frame["bl_month"] = when["year"].to_numpy(), when["month"].to_numpy()
    notes["participants without a usable baseline visit month"] = int(frame["bl_month"].isna().sum())
    if frame["bl_month"].isna().mean() > 0.05:
        # Without the baseline month no medication can be placed in time; stop rather than report "no drugs".
        raise JoinError("the baseline visit month could not be read for more than 5% of participants")

    frame = add_fs7(frame, loader, "fs7_aseg", sources["fs7_aseg"], u["baseline_event"], flow)
    frame = add_fs7(frame, loader, "fs7_aparc", sources["fs7_aparc"], u["baseline_event"], flow)
    frame = add_genetics(frame, loader, sources["genetics"], flow)
    frame = add_saa(frame, loader, sources["saa"], u["baseline_event"], flow)
    frame = add_lumipulse(frame, loader, sources["lumipulse"], u["baseline_event"], flow, notes)
    frame = add_vascular_evidence(frame, loader, cfg, rules, cards["vascular_v1"]["rule"]["bp_thresholds"], flow, notes)
    if len(frame) != flow[0]["n_participants_before"]:
        raise JoinError("the participant count changed while building the cohort")
    assert_one_row_per_participant(frame, "analytic cohort")
    return frame, flow, notes


def add_labels(frame: pd.DataFrame, cards: dict) -> tuple[pd.DataFrame, dict]:
    """Every label that does not depend on the split (the Lumipulse label is added after it)."""
    out = frame.copy()
    out[builders.label_column("pd_type_v1")] = builders.pd_type(out["cohort"], cards["pd_type_v1"]).to_numpy()
    out[builders.label_column("pd_type_saa_v1")] = builders.pd_type_saa(out["saa_status_bl"], cards["pd_type_saa_v1"]).to_numpy()
    card = cards["ad_like_v1"]
    values = builders.ad_like_values(out, builders.ad_like_parameters(card))
    out["elecsys_ptau_abeta_ratio"] = values["ratio"].to_numpy()
    out["ad_like_v1_censored"] = values["censored"].astype(int).to_numpy()
    for name, labels in builders.ad_like(out, card).items():
        out[builders.label_column(name)] = labels.to_numpy()
    for name in ("vascular_v1", "vascular_v2"):
        out[builders.label_column(name)] = builders.vascular(
            out["vascular_component_count"], out["htn_evaluable"], cards[name]).to_numpy()
    return out, builders.ad_like_limit_counts(frame, card)
