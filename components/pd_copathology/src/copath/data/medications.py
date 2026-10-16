"""Baseline vascular evidence: medications ongoing at baseline and supine blood pressure.

Implements the frozen rules of ``docs/phase1_final_decisions_v1.md`` section
5.2 with the drug lists in ``configs/drug_classes.yaml``. Everything returned
is at participant level; the counts returned alongside are aggregates for the
reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

KEY = "PATNO"
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


# --------------------------------------------------------------------------
# partial dates
# --------------------------------------------------------------------------

def parse_partial_date(values: pd.Series) -> pd.DataFrame:
    """Split dates into ``year``, ``month`` and ``kind``.

    ``kind`` is ``month`` (full date or month/year), ``year`` (year only),
    ``missing`` (blank) or ``unparseable``. Nothing finer than the month is kept.
    """
    text = values.astype(str).str.strip()
    year = pd.Series(np.nan, index=text.index, dtype="float64")
    month = pd.Series(np.nan, index=text.index, dtype="float64")
    for pattern in (
        r"^(?P<m>\d{1,2})/(?P<y>\d{4})$",
        r"^(?P<y>\d{4})-(?P<m>\d{1,2})(?:-\d{1,2})?(?:[ T].*)?$",
        r"^(?P<m>\d{1,2})/\d{1,2}/(?P<y>\d{4})(?:[ T].*)?$",
    ):
        found = text.str.extract(pattern)
        y, m = pd.to_numeric(found["y"], errors="coerce"), pd.to_numeric(found["m"], errors="coerce")
        ok = year.isna() & y.notna() & m.between(1, 12)
        year, month = year.where(~ok, y), month.where(~ok, m)
    named = text.str.extract(r"^(?P<mon>[A-Za-z]{3})[A-Za-z]*[ /-]?(?P<y>\d{4})$")
    y, m = pd.to_numeric(named["y"], errors="coerce"), named["mon"].str.lower().map(_MONTHS)
    ok = year.isna() & y.notna() & m.notna()
    year, month = year.where(~ok, y), month.where(~ok, m)
    only = pd.to_numeric(text.str.extract(r"^(?P<y>\d{4})(?:\.0+)?$")["y"], errors="coerce")
    year = year.where(~(year.isna() & only.notna()), only)
    kind = np.where(text == "", "missing",
                    np.where(year.isna(), "unparseable", np.where(month.isna(), "year", "month")))
    return pd.DataFrame({"year": year, "month": month, "kind": kind}, index=text.index)


def ongoing_at_baseline(start: pd.DataFrame, stop: pd.DataFrame, bl_year: pd.Series, bl_month: pd.Series) -> pd.DataFrame:
    """Apply the frozen "ongoing at BL" rule to medication records.

    * start: month <= BL month. A year-only start counts when the year is
      before the BL year, is **ambiguous** (not counted) in the BL year, and
      does not count after it. A missing or unparseable start is not counted.
    * stop: missing = ongoing; month >= BL month = ongoing; a year-only stop in
      the BL year or later = ongoing. An unparseable stop cannot be placed, so
      the record is not counted.

    Returns ``ongoing`` plus a ``reason`` for every record that is not ongoing.
    """
    bl = bl_year * 12 + bl_month
    s_month, s_year = start["kind"] == "month", start["kind"] == "year"
    started = (s_month & (start["year"] * 12 + start["month"] <= bl)) | (s_year & (start["year"] < bl_year))
    ambiguous = s_year & (start["year"] == bl_year)
    e_month, e_year = stop["kind"] == "month", stop["kind"] == "year"
    not_stopped = (
        (stop["kind"] == "missing")
        | (e_month & (stop["year"] * 12 + stop["month"] >= bl))
        | (e_year & (stop["year"] >= bl_year))
    )
    reason = np.select(
        [bl.isna(), start["kind"].isin(["missing", "unparseable"]), ambiguous, ~started,
         stop["kind"] == "unparseable", ~not_stopped],
        ["no baseline date", "start date missing or unparseable", "start year-only in the baseline year (ambiguous)",
         "started after baseline", "stop date unparseable", "stopped before baseline"],
        default="",
    )
    return pd.DataFrame({"ongoing": reason == "", "reason": reason}, index=start.index)


# --------------------------------------------------------------------------
# drug rules
# --------------------------------------------------------------------------

@dataclass
class DrugRules:
    """Compiled include / conditional / exclude patterns per vascular component."""

    raw: dict

    @classmethod
    def from_yaml(cls, path: Path) -> "DrugRules":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        for component in ("htn", "dm", "dyslip"):
            section = (raw.get("components") or {}).get(component)
            if not section or any(k not in section for k in ("include", "conditional", "exclude")):
                raise ValueError(f"drug_classes.yaml: component {component} needs include, conditional and exclude lists")
        return cls(raw)

    def names(self, component: str, kind: str) -> dict[str, list[str]]:
        """Generic name -> spellings, for one component and one of include/conditional/exclude."""
        out: dict[str, list[str]] = {}
        for drugs in (self.raw["components"][component].get(kind) or {}).values():
            for generic, aliases in (drugs or {}).items():
                out[str(generic)] = [str(a) for a in (aliases or [generic])]
        return out

    def pattern(self, component: str, kind: str) -> str | None:
        words = sorted({a.lower() for aliases in self.names(component, kind).values() for a in aliases})
        return r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b" if words else None

    @property
    def indication(self) -> dict:
        return self.raw.get("hypertension_indication") or {}


def _matches(text: pd.Series, pattern: str | None) -> pd.Series:
    if not pattern:
        return pd.Series(False, index=text.index)
    return text.str.contains(pattern, regex=True)


def medication_evidence(meds: pd.DataFrame, baseline: pd.DataFrame, rules: DrugRules, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Participant-level drug evidence ongoing at baseline, and aggregate record counts.

    ``baseline`` has one row per universe participant with ``bl_year`` and
    ``bl_month``. Participants without any medication record get ``False`` for
    every flag: the log is treated as a complete list of current medications.
    """
    meds = meds[meds[KEY].isin(set(baseline[KEY]))].reset_index(drop=True)
    names = meds[list(cfg["name_columns"])].astype(str).agg(" | ".join, axis=1).str.lower()
    bl = baseline.set_index(KEY)
    rule = ongoing_at_baseline(
        parse_partial_date(meds[cfg["start"]]), parse_partial_date(meds[cfg["stop"]]),
        meds[KEY].map(bl["bl_year"]), meds[KEY].map(bl["bl_month"]),
    )
    ongoing = rule["ongoing"]

    indication = rules.indication
    text = meds[cfg["indication_text"]].astype(str).str.lower()
    code = meds[cfg["indication_code"]].astype(str).str.replace(r"\.0+$", "", regex=True)
    by_text = _matches(text, indication.get("text"))
    if indication.get("text_exclude"):
        by_text &= ~_matches(text, indication["text_exclude"])
    for_htn = by_text | code.isin([str(c) for c in indication.get("codes") or []])

    excluded = _matches(names, rules.pattern("htn", "exclude"))
    definite = _matches(names, rules.pattern("htn", "include"))
    conditional = _matches(names, rules.pattern("htn", "conditional")) & for_htn
    record = pd.DataFrame({
        KEY: meds[KEY],
        "htn_med_definite": ongoing & definite,
        "htn_med_conditional": ongoing & conditional,
        "dm_med": ongoing & _matches(names, rules.pattern("dm", "include")),
        "dyslipid_med": ongoing & _matches(names, rules.pattern("dyslip", "include")),
    })
    flags = ["htn_med_definite", "htn_med_conditional", "dm_med", "dyslipid_med"]
    per = record.groupby(KEY)[flags].any()
    out = baseline[[KEY]].merge(per, left_on=KEY, right_index=True, how="left")
    out["med_record_any"] = out[KEY].isin(set(meds[KEY]))
    for flag in flags:
        out[flag] = out[flag].fillna(False).astype(bool)

    relevant = definite | _matches(names, rules.pattern("htn", "conditional")) | record["dm_med"] | record["dyslipid_med"] \
        | _matches(names, rules.pattern("dm", "include")) | _matches(names, rules.pattern("dyslip", "include"))
    counts = {"records of baseline-universe participants": int(len(meds)),
              "records ongoing at baseline": int(ongoing.sum())}
    for reason, n in rule.loc[~ongoing, "reason"].value_counts().items():
        counts[f"not counted: {reason}"] = int(n)
    counts["vascular-drug records not counted: start year-only in the baseline year (ambiguous)"] = int(
        (relevant & (rule["reason"] == "start year-only in the baseline year (ambiguous)")).sum())
    counts["conditional antihypertensive records ongoing without a hypertension indication (not counted)"] = int(
        (ongoing & _matches(names, rules.pattern("htn", "conditional")) & ~for_htn).sum())
    counts["never-counted drug records ongoing (prostate-selective alpha-blocker or pressor)"] = int((ongoing & excluded).sum())
    return out, counts


# --------------------------------------------------------------------------
# blood pressure and components
# --------------------------------------------------------------------------

def supine_bp(vitals: pd.DataFrame, universe: pd.Series, cfg: dict, baseline_event: str) -> pd.DataFrame:
    """Supine SBP/DBP per participant: baseline, or screening only when baseline has none.

    If a visit has more than one record the mean of the readings is used.
    """
    frame = pd.DataFrame({
        KEY: vitals[KEY], "event": vitals[cfg["event_column"]],
        "sup_sbp": pd.to_numeric(vitals[cfg["sbp"]].replace("", np.nan), errors="coerce"),
        "sup_dbp": pd.to_numeric(vitals[cfg["dbp"]].replace("", np.nan), errors="coerce"),
    })
    frame = frame[frame["sup_sbp"].notna() | frame["sup_dbp"].notna()]

    def at(event: str) -> pd.DataFrame:
        return frame[frame["event"] == event].groupby(KEY)[["sup_sbp", "sup_dbp"]].mean()

    at_bl, at_sc = at(baseline_event), at(cfg["screening_event"])
    at_sc = at_sc[~at_sc.index.isin(at_bl.index)]
    at_bl["bp_source"], at_sc["bp_source"] = "BL", "SC_fallback"
    out = pd.DataFrame({KEY: universe}).merge(pd.concat([at_bl, at_sc]), left_on=KEY, right_index=True, how="left")
    out["bp_source"] = out["bp_source"].fillna("missing")
    return out


def vascular_components(frame: pd.DataFrame, sbp_threshold: float, dbp_threshold: float) -> pd.DataFrame:
    """Add ``htn_bp``, ``htn_evaluable`` and the three components to the analytic frame.

    ``htn_bp`` is 1 when either reading reaches its threshold, 0 when blood
    pressure was measured and is below the thresholds, and missing only when
    there is no baseline or screening reading at all.
    """
    out = frame.copy()
    high = (out["sup_sbp"] >= sbp_threshold) | (out["sup_dbp"] >= dbp_threshold)
    measured = out["sup_sbp"].notna() | out["sup_dbp"].notna()
    out["htn_bp"] = np.where(high, 1.0, np.where(measured, 0.0, np.nan))
    on_drug = out["htn_med_definite"] | out["htn_med_conditional"]
    out["htn_evaluable"] = out["htn_bp"].notna() | on_drug
    out["comp_htn"] = (on_drug | (out["htn_bp"] == 1)).astype(int)
    out["comp_dm"] = out["dm_med"].astype(int)
    out["comp_dyslip"] = out["dyslipid_med"].astype(int)
    out["vascular_component_count"] = out[["comp_htn", "comp_dm", "comp_dyslip"]].sum(axis=1)
    return out
