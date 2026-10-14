"""Shared machinery of the Phase 3 commands: paths, data access, one registered run, report helpers.

Data access rules enforced here:

* every command except an approved ``final`` loads development rows only
  (:func:`copath.data.split.load_analytic` with its default ``part="dev"``);
* a model sees eligible (non-masked) participants of its label only;
* features come from ``configs/feature_sets/<label>_<tier>.yaml`` and are
  checked against the leakage matrix before use;
* participant-level outputs go to git-ignored folders; everything under
  ``reports/phase3`` is aggregate and is scanned for identifiers.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import sys
import time
import warnings
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..data import split as split_mod
from ..data.load import COMPONENT_DIR
from ..data.privacy import scan_reports_for_ids, suppress
from ..evaluation import metrics
from ..explain import shap_explainer
from ..features import leakage_guard
from ..models import baselines, candidates
from ..targets import builders
from ..training import registry, train

KEY = "PATNO"
THRESHOLD = 5
PHASE3_VERSION = "1.0.0"


class Phase3Error(RuntimeError):
    """A rule of the Phase 3 workflow was violated (the message never contains data)."""


class PrivacyCheckError(RuntimeError):
    """A participant identifier was found in a generated report."""


@dataclass
class Paths:
    config: Path = COMPONENT_DIR / "configs" / "phase3.yaml"
    expected: Path = COMPONENT_DIR / "configs" / "expected_features.yaml"
    leakage_matrix: Path = leakage_guard.MATRIX_PATH
    feature_sets: Path = leakage_guard.FEATURE_SETS_DIR
    targets: Path = COMPONENT_DIR / "targets"
    frozen: Path = COMPONENT_DIR / "configs" / "frozen"
    processed: Path = COMPONENT_DIR / "data" / "processed"
    splits: Path = COMPONENT_DIR / "data" / "splits"
    reports: Path = COMPONENT_DIR / "reports" / "phase3"
    phase2_reports: Path = COMPONENT_DIR / "reports" / "phase2"
    registry: Path = COMPONENT_DIR / "experiments" / "registry.csv"
    runs: Path = COMPONENT_DIR / "experiments" / "phase3"
    models: Path = COMPONENT_DIR / "models" / "final"

    @property
    def oof(self) -> Path:  # participant level, git-ignored
        return self.processed / "oof"

    @property
    def shap(self) -> Path:  # participant level, git-ignored
        return self.processed / "shap"

    @property
    def selected(self) -> Path:
        return self.frozen / "selected_models_v1.yaml"

    @property
    def approval(self) -> Path:
        return self.frozen / "final_approval.yaml"

    @property
    def lock(self) -> Path:
        return self.frozen / "final_evaluation_lock.json"


@dataclass
class Context:
    paths: Paths
    cfg: dict
    frame: pd.DataFrame  # development rows only
    matrix: pd.DataFrame
    parents: dict
    hashes: dict
    seed: int
    started: float = field(default_factory=time.time)
    written: list = field(default_factory=list)

    def log(self, message: str) -> None:
        elapsed = time.time() - self.started
        print(f"[{int(elapsed // 60):3d}m{int(elapsed % 60):02d}s] {message}", file=sys.stderr, flush=True)


def sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(1024 * 1024):
            sha.update(block)
    return sha.hexdigest()


def library_versions() -> dict[str, str]:
    """Installed versions of the libraries that decide how a model is fitted (recorded with every run)."""
    return {name: importlib.metadata.version(name) for name in ("scikit-learn", "numpy", "xgboost", "optuna", "shap")}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def S(n: int) -> int | str:
    return suppress(int(n), THRESHOLD)


def load_context(paths: Paths | None = None) -> Context:
    """Configuration, leakage matrix and the development rows. The test set is not touched."""
    paths = paths or Paths()
    warnings.simplefilter("ignore")  # library warnings can quote values
    cfg = yaml.safe_load(Path(paths.config).read_text(encoding="utf-8"))
    dev_file = paths.processed / "analytic_bl_v1_dev.parquet"
    if not dev_file.is_file():
        raise Phase3Error("data/processed/analytic_bl_v1_dev.parquet not found: run `python -m copath.phase2 --refreeze` first")
    frame = split_mod.load_analytic(paths.processed, paths.splits)  # development rows only
    if "fold" not in frame.columns:
        raise Phase3Error("the development file has no `fold` column")
    matrix = leakage_guard.load_matrix(paths.leakage_matrix)
    stale = leakage_guard.out_of_sync(paths.leakage_matrix, sets_dir=paths.feature_sets)
    if [name for name in stale if name.endswith(".yaml")]:
        raise Phase3Error("configs/feature_sets is out of date; run `python -m copath.features.leakage_guard`")
    parents = builders.variant_parents(builders.load_cards(paths.targets))
    folds = hashlib.sha256("\n".join(sorted(f"{p}:{f}" for p, f in zip(frame[KEY].astype(str), frame["fold"]))).encode()).hexdigest()
    config_files = [paths.config, paths.leakage_matrix] + sorted(Path(paths.feature_sets).glob("*.yaml"))
    hashes = {"fold_scheme_sha256": folds, "dataset_sha256": sha256(dev_file),
              "config_sha256": hashlib.sha256("".join(sha256(p) for p in config_files).encode()).hexdigest()}
    return Context(paths, cfg, frame, matrix, parents, hashes, int(cfg["seed"]))


# --------------------------------------------------------------------------
# features and eligible rows
# --------------------------------------------------------------------------

def tier_features(ctx: Context, label: str, tier: str, frame: pd.DataFrame | None = None) -> tuple[list[str], list[str]]:
    """Numeric features of the label's tier that exist in the dataset, and the tier features left out as non-numeric."""
    frame = ctx.frame if frame is None else frame
    parent = ctx.parents.get(label, label)
    listed = yaml.safe_load((ctx.paths.feature_sets / f"{parent}_{tier}.yaml").read_text(encoding="utf-8"))["features"]
    leakage_guard.assert_allowed(listed, ctx.matrix, label, tier, ctx.parents)
    present = [f for f in listed if f in frame.columns]
    numeric = [f for f in present if pd.api.types.is_numeric_dtype(frame[f]) or pd.api.types.is_bool_dtype(frame[f])]
    return numeric, [f for f in present if f not in numeric]


def modality_of(ctx: Context) -> dict[str, str]:
    return dict(zip(ctx.matrix["feature"], ctx.matrix["modality"]))


def prepare(ctx: Context, label: str, tier: str, features: list[str] | None = None, frame: pd.DataFrame | None = None,
            restrict: pd.Series | None = None) -> dict:
    """Eligible rows of a label: features, outcome, folds and identifiers. Masked participants are dropped here."""
    frame = ctx.frame if frame is None else frame
    column = builders.label_column(label)
    if column not in frame.columns:
        raise Phase3Error(f"label column not in the dataset: {column}")
    eligible = frame[column].notna()
    if restrict is not None:
        eligible &= restrict.reindex(frame.index).fillna(False).astype(bool)
    part = frame[eligible]
    dropped: list[str] = []
    if features is None:
        features, dropped = tier_features(ctx, label, tier, frame)
        features = [f for f in features if part[f].notna().any()]  # a feature nobody eligible has cannot be used
    leakage_guard.assert_allowed(features, ctx.matrix, label, tier, ctx.parents)
    X = part[features].astype(float).reset_index(drop=True)
    return {"X": X, "y": part[column].astype(int).to_numpy(), "ids": part[KEY].astype(str).to_numpy(),
            "folds": part["fold"].to_numpy() if "fold" in part.columns else None, "features": features,
            "nonnumeric": dropped}


# --------------------------------------------------------------------------
# one registered run
# --------------------------------------------------------------------------

def find_run(ctx: Context, rid: str) -> dict | None:
    """Details of a finished run under the current dataset, folds and configuration, or None."""
    if registry.find(ctx.paths.registry, rid, ctx.hashes) is None or not (ctx.paths.runs / f"{rid}.json").is_file():
        return None
    return registry.load_details(ctx.paths.runs, rid)


def load_oof(ctx: Context, rid: str) -> pd.DataFrame:
    return pd.read_parquet(ctx.paths.oof / f"{rid}.parquet")


def fold_params(details: dict) -> dict[int, dict]:
    return {int(r["fold"]): r["params"] for r in details["folds"] if not r.get("failed")}


def run(ctx: Context, stage: str, label: str, tier: str, model: str, seed: int, variant: str = "",
        params: dict | None = None, calibration: str | None = None, shap_rows: int = 0, features: list[str] | None = None,
        restrict: pd.Series | None = None, select=None) -> dict:
    """One outer-CV run, registered. Skipped (and its stored details returned) when it already exists."""
    rid = registry.run_id(stage, label, tier, model, seed, variant)
    done = find_run(ctx, rid)
    if done is not None:
        ctx.log(f"{rid}: already in the registry, reused")
        return done
    started_at, t0 = now(), time.time()
    data = prepare(ctx, label, tier, features=features, restrict=restrict)
    details = {"run_id": rid, "stage": stage, "label": label, "tier": tier, "model": model, "seed": seed, "variant": variant,
               "n_eligible": int(len(data["y"])), "n_features": len(data["features"]), "features": data["features"],
               "nonnumeric_tier_features_not_used": data["nonnumeric"], "library_versions": library_versions(), **ctx.hashes}
    if select is not None:
        details["column_rule"] = str(select)
    y = data["y"]
    minimum = int(ctx.cfg.get("min_eligible", 50))
    if len(y) < minimum or min((y == 0).sum(), (y == 1).sum()) < 10 or not data["features"]:
        details.update(status="skipped", reason="too few eligible participants, too few of one class, or no feature")
        ctx.log(f"{rid}: skipped (too few eligible participants or no feature)")
    else:
        ctx.log(f"{rid}: {S(len(y))} eligible, {len(data['features'])} features")
        out = train.outer_cv(data["X"], y, data["folds"], data["ids"], model, seed, ctx.cfg, fold_params=params,
                             calibration=calibration, keep_models=shap_rows > 0, log=lambda m: ctx.log(f"  {rid}: {m}"),
                             select=select)
        failed = sum(r["failed"] for r in out["folds"])
        details.update(folds=out["folds"], n_failed_folds=failed, status="ok" if len(out["oof"]) else "failed",
                       n_failed_trials=int(sum(r.get("n_failed_trials", 0) for r in out["folds"])))
        if not len(out["oof"]):  # nothing to score: no metrics, no out-of-fold file; the run is registered as failed
            reasons = Counter(r.get("error_detail") or r.get("error", "unknown") for r in out["folds"] if r["failed"])
            details["failure_reasons"] = dict(reasons)
            ctx.log(f"ERROR {rid} FAILED: label {label}, tier {tier}, model {model}: every outer fold failed "
                    f"({'; '.join(f'{k} [{v} folds]' for k, v in reasons.items())}). No metrics are written; the run continues "
                    "with the next one and is retried when the command is run again.")
        if len(out["oof"]):
            ctx.paths.oof.mkdir(parents=True, exist_ok=True)
            out["oof"].to_parquet(ctx.paths.oof / f"{rid}.parquet", index=False)
            details["summary"] = metrics.summarise(out["oof"])
            uncal = metrics.summarise(out["oof"], prob="p_uncal")["pooled"]
            details["uncalibrated_pooled"] = {k: v for k, v in uncal.items() if k not in ("f1", "precision", "recall")}
        if shap_rows and out["models"]:
            details["shap"] = fold_shap(ctx, model, data, out["models"], seed, shap_rows)
    details.update(started_at=started_at, finished_at=now(), seconds=round(time.time() - t0, 1))
    registry.save_details(ctx.paths.runs, rid, details)
    pooled, se = (details.get("summary") or {}).get("pooled", {}), (details.get("summary") or {}).get("se", {})
    registry.append(ctx.paths.registry, {**details, **{k: _round(pooled.get(k)) for k in registry.METRICS},
                                         "se_bss": _round(se.get("bss"))})
    return registry.load_details(ctx.paths.runs, rid)  # the stored form, identical for a fresh and a reused run


def fold_shap(ctx: Context, model: str, data: dict, models: dict, seed: int, max_rows: int) -> dict:
    """Mean |SHAP| per feature on (a seeded sample of) each outer fold's test rows. Aggregate only."""
    out = {"folds": {}, "space": None, "explainer": None}
    for k, pipeline in models.items():
        test = np.flatnonzero(data["folds"] == k)
        rng = np.random.default_rng(seed + int(k))
        rows = np.sort(rng.choice(test, min(max_rows, len(test)), replace=False))
        result = shap_explainer.explain(model, pipeline, data["X"][data["folds"] != k], data["X"].iloc[rows])
        out["folds"][str(k)] = shap_explainer.mean_abs(result["values"], data["features"]).round(8).to_dict()
        out["space"], out["explainer"] = result["space"], result["explainer"]
    return out


# --------------------------------------------------------------------------
# reports
# --------------------------------------------------------------------------

def _round(value, digits: int = 4):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return ""
    return round(float(value), digits)


def metric_rows(details: dict, extra: dict | None = None, scopes: tuple[str, ...] = ("pooled", "mean", "sd", "se", "folds")) -> list[dict]:
    """Report rows of one run: pooled, mean / SD / SE across folds, and each fold."""
    base = {"label": details["label"], "tier": details["tier"], "model": details["model"], **(extra or {}),
            "n_eligible": S(details["n_eligible"]), "n_features": details["n_features"],
            "n_failed_folds": details.get("n_failed_folds", "")}
    summary = details.get("summary")
    if not summary:
        return [{**base, "scope": details.get("status", "failed")}]
    rows = []
    for scope in scopes:
        if scope == "folds":
            rows += [{**base, "scope": f"fold {k}", **{m: _round(v.get(m)) for m in metrics.LABEL_METRICS}}
                     for k, v in sorted(summary["folds"].items(), key=lambda kv: int(kv[0]))]
        else:
            rows.append({**base, "scope": scope, **{m: _round(summary[scope].get(m)) for m in metrics.LABEL_METRICS}})
    return rows


def write_csv(ctx: Context, rows: list[dict] | pd.DataFrame, name: str) -> Path:
    path = ctx.paths.reports / name
    path.parent.mkdir(parents=True, exist_ok=True)
    table = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows, dtype=object)
    table.astype(object).where(table.notna(), "").to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
    ctx.written.append(path)
    return path


def write_text(ctx: Context, text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    ctx.written.append(path)
    return path


# Aggregate numeric columns of reports, beyond the generic n_* / pct_* / metric names (see data.privacy.scan_reports_for_ids).
# They hold computed metrics, confidence bounds or counts only; a number in them is never compared with an identifier.
AGGREGATE_COLUMNS = {
    "dev_vs_test.csv": {"dev_oof_pooled", "heldout", "heldout_ci_low", "heldout_ci_high"},
    "final_test_results.csv": {"value", "ci_low", "ci_high"},
    "final_test_supplementary.csv": {"value"},
}


def privacy_check(ctx: Context, extra_ids: list[str] | None = None) -> int:
    """Scan every Phase 3 report for participant identifiers; delete this command's reports if one is found."""
    ids = set(ctx.frame[KEY].astype(str)) | set(extra_ids or [])
    findings = scan_reports_for_ids(ctx.paths.reports, ids, declared=AGGREGATE_COLUMNS) if ctx.paths.reports.is_dir() else []
    if findings:
        for path in ctx.written:
            Path(path).unlink(missing_ok=True)
        detail = "; ".join(f"{f['file']} [{f['location']}] x{f['n_matches']}" for f in findings[:20])
        raise PrivacyCheckError("Privacy self-check failed: a participant identifier appears in a Phase 3 report. "
                                f"The reports written by this command were deleted. Locations: {detail}")
    ctx.log(f"privacy self-check passed ({len(ids)} identifiers checked)")
    return len(ids)


# --------------------------------------------------------------------------
# runtime estimates (rough, printed before a command starts)
# --------------------------------------------------------------------------

# seconds per fit at about 3,000 eligible participants x 350 features, measured on random data on the development laptop
_SECONDS_PER_FIT = {"lr_l2": 0.3, "lr_enet": 0.7, "rf": 10.0, "xgb": 6.0, "hgb": 8.5, "b0a": 0.02, "b0b": 0.05, "missingness": 0.5}
_PARALLEL_GAIN = {"lr_l2": 3.0, "lr_enet": 3.0, "xgb": 1.5, "hgb": 2.0}  # measured gain from training the outer folds at the same time


def fits_per_fold(ctx: Context, model: str, tuned: bool) -> int:
    cal = int((ctx.cfg.get("calibration") or {}).get("cv", 3))
    if model not in candidates.CANDIDATES:
        return 1 + cal
    spec = ctx.cfg.get("tuning") or {}
    tuning_fits = int((spec.get("trials") or {}).get(model, 25)) * int(spec.get("inner_folds", 3)) if tuned else 0
    return tuning_fits + 1 + cal


def estimate(ctx: Context, plan: list[tuple[str, str, bool]], n_folds: int = 5) -> float:
    """Rough seconds for a list of (label, model, tuned) runs; scales with rows and features."""
    total = 0.0
    for label, model, tuned in plan:
        column = builders.label_column(label)
        n = int(ctx.frame[column].notna().sum()) if column in ctx.frame.columns else 0
        size = (n / 3000) * (len(tier_features(ctx, label, "primary")[0]) / 350)
        gain = _PARALLEL_GAIN.get(model, 1.0) if train.outer_jobs(ctx.cfg, model, n_folds) > 1 else 1.0
        total += n_folds * fits_per_fold(ctx, model, tuned) * _SECONDS_PER_FIT.get(model, 2.0) * max(size, 0.02) / gain
    return total


def announce(ctx: Context, command: str, seconds: float) -> None:
    low, high = seconds * 0.6 / 60, seconds * 1.8 / 60
    ctx.log(f"{command}: estimated runtime {low:.0f}-{high:.0f} min on a laptop (rough; runs already in the registry are skipped)")


ALL_MODELS = (*baselines.BASELINES, baselines.LEAKAGE_CHECK, *candidates.CANDIDATES)
