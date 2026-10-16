"""``report-final``: READ-ONLY aggregate reporting of the one-time held-out evaluation (Phase 3b).

Reads only artifacts that ``final`` and ``cv`` already saved:

* ``data/processed/final/test_predictions_<label>.parquet`` (PATNO, y, p_cal, p_uncal, pred), written by ``final``;
* ``reports/phase3/final_test_results.csv`` (held-out metrics and bootstrap CIs), written by ``final``;
* ``models/final/<version>/<label>/config.json`` (frozen decision threshold and development prevalence), written by ``final``;
* ``data/processed/oof/<cv run>.parquet`` and the cv run details (development out-of-fold predictions and metrics).

It never loads a model, never calls predict, fit, tune or calibrate, never recomputes or optimises a threshold, fits no
baseline, and writes only aggregate files under ``reports/phase3`` (nothing under data/, models/ or configs/frozen/).
If an expected artifact is missing it stops and names it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..evaluation import metrics
from . import commands, figures
from .core import KEY, Context, Phase3Error, S, _round, privacy_check, write_csv, write_text

UNIT_INTERVAL = {"auroc", "auprc", "brier", "ece", "f1", "precision", "recall"}  # bounded in [0, 1]
FINITE_ONLY = {"cal_slope", "cal_intercept"}  # any finite number
AT_MOST_ONE = {"bss"}  # <= 1, negative values are allowed
CI_TOLERANCE = 1e-9

SUPPLEMENTARY = "SUPPLEMENTARY / NOT PART OF THE PRE-SPECIFIED SELECTION PROTOCOL"
REPORTED = ["auroc", "auprc", "brier", "bss", "cal_slope", "cal_intercept", "ece", "f1", "precision", "recall"]
SUPPRESS_BELOW = 5


def expected_artifacts(ctx: Context, selected: dict) -> dict[str, list]:
    """Every artifact report-final needs, as {description: path}; the caller checks that each exists."""
    version = str(ctx.cfg["final"]["version"])
    found = {"final-evaluation lock file (final has not run?)": ctx.paths.lock,
             "held-out results reports/phase3/final_test_results.csv": ctx.paths.reports / "final_test_results.csv"}
    for label, choice in selected.items():
        found[f"held-out predictions for {label} (data/processed/final/test_predictions_{label}.parquet)"] = \
            ctx.paths.processed / "final" / f"test_predictions_{label}.parquet"
        found[f"frozen final-bundle config for {label} (models/final/{version}/{label}/config.json)"] = \
            ctx.paths.models / version / label / "config.json"
        found[f"development out-of-fold predictions for {label} ({choice['cv_run_id']})"] = ctx.paths.oof / f"{choice['cv_run_id']}.parquet"
        found[f"cv run details for {label} ({choice['cv_run_id']})"] = ctx.paths.runs / f"{choice['cv_run_id']}.json"
    return found


def validate_metric_rows(rows: list[dict]) -> list[str]:
    """Metric-specific sanity checks of the report rows. Raises Phase3Error naming label, metric and check (never a value).

    Returns non-fatal notes: a percentile bootstrap interval may legitimately exclude the original point estimate.
    """
    notes: list[str] = []
    def number(value) -> float:
        return float("nan") if value in ("", None) else float(value)

    for row in rows:
        name = row["metric"]
        where = f"{row['label']} / {name}"
        for column in ("dev_oof_pooled", "heldout", "heldout_ci_low", "heldout_ci_high"):
            value = number(row[column])
            if not np.isfinite(value):
                if name in FINITE_ONLY and value == value:  # an infinite slope or intercept
                    raise Phase3Error(f"report-final stopped: {where} ({column}) is not finite")
                continue  # not available (blank) is allowed
            if name in UNIT_INTERVAL and not 0.0 <= value <= 1.0:
                raise Phase3Error(f"report-final stopped: {where} ({column}) is outside [0, 1]")
            if name in AT_MOST_ONE and value > 1.0:
                raise Phase3Error(f"report-final stopped: {where} ({column}) is above 1")
        estimate, low, high = number(row["heldout"]), number(row["heldout_ci_low"]), number(row["heldout_ci_high"])
        if np.isfinite(low) and np.isfinite(high) and low > high + CI_TOLERANCE:
            raise Phase3Error(f"report-final stopped: {where}: CI lower bound is above the upper bound")
        if np.isfinite(estimate) and np.isfinite(low) and np.isfinite(high) and not low - CI_TOLERANCE <= estimate <= high + CI_TOLERANCE:
            notes.append(f"{where}: the held-out estimate lies outside its own percentile-bootstrap interval (this can happen "
                         "legitimately when the metric is unstable; not an error)")
    for row in rows:
        for column in ("n_dev_eligible", "n_test_eligible"):
            value = row[column]
            if isinstance(value, str) and value.startswith("<"):
                continue  # suppressed
            if not isinstance(value, (int, np.integer)) or value < 0:
                raise Phase3Error(f"report-final stopped: {row['label']}: {column} is not a non-negative integer")
    return notes


def confusion_cells(y: np.ndarray, pred: np.ndarray) -> dict[str, int | str]:
    """TP / FP / FN / TN of the already-saved predictions. Counts below 5 are suppressed, plus the smallest remaining
    non-zero cell when exactly one cell is suppressed, so that it cannot be recovered from the published sample size."""
    y, pred = np.asarray(y, dtype=int), np.asarray(pred, dtype=int)
    raw = {"tp": int(((pred == 1) & (y == 1)).sum()), "fp": int(((pred == 1) & (y == 0)).sum()),
           "fn": int(((pred == 0) & (y == 1)).sum()), "tn": int(((pred == 0) & (y == 0)).sum())}
    shown = {k: S(v) for k, v in raw.items()}
    hidden = [k for k, v in shown.items() if isinstance(v, str)]
    if len(hidden) == 1:
        rest = {k: v for k, v in raw.items() if k not in hidden and v > 0}
        if rest:
            shown[min(rest, key=rest.get)] = f"<{SUPPRESS_BELOW}"
    return shown


def _frozen(ctx: Context, label: str) -> dict:
    import json

    path = ctx.paths.models / str(ctx.cfg["final"]["version"]) / label / "config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _saved_results(ctx: Context) -> pd.DataFrame:
    table = pd.read_csv(ctx.paths.reports / "final_test_results.csv", dtype=str, keep_default_na=False)
    return table[table["metric"].isin(REPORTED)]


def _number(text) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def cmd_report_final(ctx: Context) -> dict:
    selected = commands.load_selected(ctx)
    missing = [f"{what}: {path.name}" for what, path in expected_artifacts(ctx, selected).items() if not path.is_file()]
    if missing:
        raise Phase3Error("report-final stopped: expected saved artifact(s) missing, nothing was regenerated and no prediction "
                          "was made. Missing: " + "; ".join(missing))
    saved, version = _saved_results(ctx), str(ctx.cfg["final"]["version"])
    rows, supplementary, test_ids = [], [], []
    for label, choice in selected.items():
        model = choice["model"]
        test = pd.read_parquet(ctx.paths.processed / "final" / f"test_predictions_{label}.parquet")
        if not {KEY, "y", "p_cal", "pred"} <= set(test.columns):
            raise Phase3Error(f"the saved held-out predictions for {label} lack one of PATNO, y, p_cal, pred")
        test_ids += list(test[KEY].astype(str))
        dev_details, dev = commands._cv(ctx, label, model), commands.load_oof(ctx, choice["cv_run_id"])
        frozen = _frozen(ctx, label)
        if frozen.get("development_prevalence") is None:
            raise Phase3Error(f"the frozen config of {label} has no development_prevalence (needed to verify the Brier Skill Score)")
        y, p, pred = test["y"].to_numpy(int), test["p_cal"].to_numpy(float), test["pred"].to_numpy(int)
        threshold = frozen.get("threshold")
        if threshold is not None and not np.array_equal(pred, (p >= float(threshold)).astype(int)):
            raise Phase3Error(f"the saved predictions of {label} do not match the frozen threshold in the final bundle")
        again = metrics.label_metrics(y, p, np.full(len(y), float(frozen["development_prevalence"])), pred)
        mine = saved[(saved["label"] == label)].set_index("metric")
        for name in REPORTED:
            if name not in mine.index:
                raise Phase3Error(f"final_test_results.csv has no {name} for {label}")
            value = _number(mine.loc[name, "value"])
            if np.isfinite(value) and np.isfinite(again[name]) and not np.isclose(again[name], value, rtol=1e-3, atol=2e-4):
                raise Phase3Error(f"the saved held-out predictions of {label} do not reproduce the saved {name}: the files do not belong together")
            rows.append({"label": label, "model": model, "metric": name,
                         "dev_oof_pooled": _round(dev_details["summary"]["pooled"][name]), "heldout": _round(value),
                         "heldout_ci_low": _round(_number(mine.loc[name, "ci_low"])), "heldout_ci_high": _round(_number(mine.loc[name, "ci_high"])),
                         "n_dev_eligible": S(len(dev)), "n_test_eligible": S(len(test))})
        figures.final_curves(test, dev, label, model, ctx.paths.reports / "figures")
        if threshold is None:
            supplementary.append({"section": SUPPLEMENTARY, "label": label, "model": model, "item": "confusion counts",
                                  "value": "", "note": "not written: no frozen threshold is persisted in the final bundle for this signal; "
                                                       "no threshold was recomputed or inferred"})
        else:
            supplementary.append({"section": SUPPLEMENTARY, "label": label, "model": model, "item": "frozen decision threshold (from the final bundle)",
                                  "value": _round(float(threshold), 6), "note": ""})
            for cell, count in confusion_cells(y, pred).items():
                supplementary.append({"section": SUPPLEMENTARY, "label": label, "model": model, "item": f"confusion count {cell.upper()} at the frozen threshold",
                                      "value": count, "note": f"counts below {SUPPRESS_BELOW} are suppressed"})
    supplementary.append({"section": SUPPLEMENTARY, "label": "ALL", "model": "", "item": "held-out baseline comparison", "value": "",
                          "note": "The held-out comparison with the prevalence reference is given by the Brier Skill Score. The age + sex "
                                  "baseline is reported from the pre-specified development CV. No new held-out baseline was fitted after "
                                  "test access; `final` did not save held-out baseline predictions."})
    notes = validate_metric_rows(rows)  # before anything is written; the notes are not errors
    table = pd.DataFrame(rows)
    write_csv(ctx, table, "dev_vs_test.csv")
    write_csv(ctx, supplementary, "final_test_supplementary.csv")
    figures.final_summary(table, ctx.paths.reports / "figures")
    ctx.written += [ctx.paths.reports / "figures" / name for name in
                    ["final_test_summary.png", *(f"final_test_curves_{label}.png" for label in selected)]]  # deleted too on a failed privacy check
    write_text(ctx, "\n".join([
        "# Held-out reporting (read-only)", "",
        f"Bundle version {version}. Built from predictions and metrics that `final` saved; no model was loaded, no prediction "
        "was made, no threshold was recomputed.", "",
        "- `dev_vs_test.csv`: development pooled out-of-fold metric versus held-out metric (saved bootstrap 95% CI) per selected signal.",
        "- `final_test_supplementary.csv`: " + SUPPLEMENTARY + ".",
        "- `figures/final_test_curves_<label>.png`, `figures/final_test_summary.png`.", "",
        *(["## Notes", "", *[f"- {n}" for n in notes], ""] if notes else [])]) + "\n", ctx.paths.reports / "final_report_notes.md")
    privacy_check(ctx, extra_ids=test_ids)
    return {"dev_vs_test": ctx.paths.reports / "dev_vs_test.csv", "supplementary": ctx.paths.reports / "final_test_supplementary.csv"}
