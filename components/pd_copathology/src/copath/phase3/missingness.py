"""``missingness-audit``: how differently PD and HC participants have each pd_type_v1 feature available.

Writes, for ``pd_type_v1`` only,

* ``reports/phase3/pd_missingness_audit.csv`` - per feature, the % of PD and of HC development participants with the
  feature available, and the absolute difference in percentage points, largest first (feature names and percentages only);
* ``reports/phase3/pd_low_missingness_run.csv`` - one extra nested-CV run on the strict tier, using the selected PD-type
  model family with its per-fold hyperparameters, restricted in every outer fold to the features whose availability
  differs by less than ``MAX_GAP_PP`` points between PD and HC **in that fold's training rows**.

Development rows only. The extra run is registered as an ``extras`` run, so a restart reuses it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..targets import builders
from . import commands
from .core import Context, Phase3Error, S, _round, find_run, fold_params, metric_rows, modality_of, prepare, privacy_check, run, \
    tier_features, write_csv

LABEL = "pd_type_v1"
MAX_GAP_PP = 10.0
VARIANT = "low_missingness_lt10pp"


def availability(X: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    """% of positive (PD) and negative (HC) rows with each column available, and the absolute difference."""
    y = np.asarray(y, dtype=int)
    pd_pct, hc_pct = 100 * X[y == 1].notna().mean(), 100 * X[y == 0].notna().mean()
    return pd.DataFrame({"feature": X.columns, "pct_available_pd": pd_pct.to_numpy(), "pct_available_hc": hc_pct.to_numpy(),
                         "abs_diff_pp": (pd_pct - hc_pct).abs().to_numpy()})


@dataclass(frozen=True)
class AvailabilityGap:
    """Column rule: keep the columns whose availability differs by less than ``max_gap_pp`` points between PD and HC (training rows)."""

    max_gap_pp: float = MAX_GAP_PP

    def __call__(self, X: pd.DataFrame, y: np.ndarray) -> list[str]:
        table = availability(X, y)
        return list(table.loc[table["abs_diff_pp"] < self.max_gap_pp, "feature"])

    def __str__(self) -> str:
        return f"availability differs by < {self.max_gap_pp:g} percentage points between PD and HC in the training rows"


def audit_rows(ctx: Context) -> pd.DataFrame:
    if LABEL not in ctx.cfg["labels"]:
        raise Phase3Error(f"{LABEL} is not a label of this configuration")
    numeric, other = tier_features(ctx, LABEL, "primary")
    strict = set(tier_features(ctx, LABEL, "strict")[0])
    data = prepare(ctx, LABEL, "primary", features=numeric)
    n_pd, n_hc = int((data["y"] == 1).sum()), int((data["y"] == 0).sum())
    if min(n_pd, n_hc) < 5:
        raise Phase3Error("too few PD or HC development participants to report availability percentages")
    table = availability(data["X"], data["y"])
    extra = [f for f in other if f in ctx.frame.columns]  # non-numeric tier features: availability is still defined
    if extra:
        eligible = ctx.frame[builders.label_column(LABEL)].notna()
        part, y = ctx.frame[eligible], ctx.frame.loc[eligible, builders.label_column(LABEL)].astype(int).to_numpy()
        table = pd.concat([table, availability(part[extra].reset_index(drop=True), y)], ignore_index=True)
    modality = modality_of(ctx)
    table["modality"] = table["feature"].map(lambda f: modality.get(f, ""))
    table["in_strict_tier"] = table["feature"].isin(strict)
    table["gap_below_threshold"] = table["abs_diff_pp"] < MAX_GAP_PP
    table = table.sort_values(["abs_diff_pp", "feature"], ascending=[False, True], kind="mergesort")
    for column in ("pct_available_pd", "pct_available_hc", "abs_diff_pp"):
        table[column] = table[column].round(2)
    return table[["feature", "modality", "pct_available_pd", "pct_available_hc", "abs_diff_pp", "in_strict_tier", "gap_below_threshold"]]


def cmd_missingness_audit(ctx: Context) -> None:
    table = audit_rows(ctx)
    write_csv(ctx, table, "pd_missingness_audit.csv")
    ctx.log(f"missingness-audit: {len(table)} features; {int((~table['gap_below_threshold']).sum())} differ by >= {MAX_GAP_PP:g} points")
    privacy_check(ctx)
    low_missingness_run(ctx)
    privacy_check(ctx)


def low_missingness_run(ctx: Context) -> None:
    selected = commands.load_selected(ctx)  # raises with the instruction to run `select --stage final` when there is none
    if LABEL not in selected:
        raise Phase3Error(f"the frozen selection has no model for {LABEL}; the audit table was written, the extra run was not")
    model, strict = selected[LABEL]["model"], ctx.cfg.get("robustness_tier", "strict")
    base = commands._cv(ctx, LABEL, model)
    rule = AvailabilityGap(MAX_GAP_PP)
    details = run(ctx, "extras", LABEL, strict, model, ctx.seed, variant=VARIANT, params=fold_params(base), select=rule)
    reference = find_run(ctx, f"robustness-{LABEL}-{strict}-{model}-s{ctx.seed}")
    rows = []
    for name, found in (("primary tier, all features (cv, reference)", base),
                        ("strict tier, all features (robustness, base seed, reference)", reference),
                        (f"strict tier, features with availability gap < {MAX_GAP_PP:g} points (this run)", details)):
        if not found or not found.get("summary"):
            rows.append({"label": LABEL, "model": model, "analysis": name, "scope": (found or {}).get("status", "not run")})
            continue
        for row in metric_rows(found, scopes=("pooled", "mean", "sd")):
            rows.append({"analysis": name, **row})
        if found is details:
            deltas = commands._deltas(base, details)
            rows[-3].update(deltas)  # on the pooled row: mean / SD over folds of (this run - primary cv)
            for record in sorted(found["folds"], key=lambda r: r["fold"]):
                if not record.get("failed"):
                    fold = found["summary"]["folds"][str(record["fold"])]
                    rows.append({"analysis": name, "label": LABEL, "tier": strict, "model": model, "scope": f"fold {record['fold']}",
                                 "n_features": record["n_selected"], "auroc": _round(fold["auroc"]), "auprc": _round(fold["auprc"]),
                                 "bss": _round(fold["bss"])})
    selected_counts = [r["n_selected"] for r in (details.get("folds") or []) if not r.get("failed")]
    ctx.log(f"low-missingness run: {model}; features kept per fold (of {details['n_features']}): {selected_counts}")
    write_csv(ctx, rows, "pd_low_missingness_run.csv")
