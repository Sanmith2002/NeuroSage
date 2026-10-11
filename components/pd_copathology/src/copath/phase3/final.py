"""Command 7: the single final evaluation on the frozen test set. Locked until a human approves it.

``final`` runs only when ALL of these hold:

* the ``--final`` flag is given;
* ``configs/frozen/final_approval.yaml`` exists, written by the reviewer, with
  ``approved: true``, ``reviewer``, ``date`` and ``selected_models_sha256``
  equal to the SHA-256 of ``configs/frozen/selected_models_v1.yaml``;
* every PROVISIONAL label of the selection (a label whose selected model did
  not pass every gate) is listed in ``acknowledge_provisional`` of the
  approval file;
* no lock file from an earlier final run exists (or the run is forced with a
  written reason, which is logged).

This module never creates the approval file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

from ..data import split as split_mod
from ..evaluation import metrics
from ..training import registry, train
from .commands import _tier, load_selected
from .core import (KEY, Context, Paths, Phase3Error, S, _round, announce, estimate, load_context, now, prepare, privacy_check,
                   sha256, write_csv)


class FinalLockError(Phase3Error):
    """The final evaluation is locked."""


def check_unlocked(paths: Paths, final_flag: bool, force: bool = False, reason: str = "") -> dict:
    """Raise unless the final evaluation may run. Returns the approval record."""
    if not final_flag:
        raise FinalLockError("the final evaluation is locked: it needs the --final flag and a human approval file")
    if not paths.selected.is_file():
        raise FinalLockError("configs/frozen/selected_models_v1.yaml not found: run `select --stage final` first")
    if not paths.approval.is_file():
        raise FinalLockError("the final evaluation is locked: configs/frozen/final_approval.yaml does not exist. It is "
                             "written by the reviewer after reading reports/phase3, never by this software.")
    approval = yaml.safe_load(paths.approval.read_text(encoding="utf-8")) or {}
    if approval.get("approved") is not True:
        raise FinalLockError("final_approval.yaml does not contain `approved: true`")
    missing = [k for k in ("reviewer", "date", "selected_models_sha256") if not str(approval.get(k) or "").strip()]
    if missing:
        raise FinalLockError(f"final_approval.yaml lacks: {', '.join(missing)}")
    if str(approval["selected_models_sha256"]).strip().lower() != sha256(paths.selected):
        raise FinalLockError("final_approval.yaml approves a different selected_models_v1.yaml (the hash does not match)")
    chosen = (yaml.safe_load(paths.selected.read_text(encoding="utf-8")) or {}).get("labels") or {}
    provisional = sorted(label for label, choice in chosen.items() if not choice.get("gates_passed"))
    acknowledged = approval.get("acknowledge_provisional") or []
    if not isinstance(acknowledged, list):
        raise FinalLockError("`acknowledge_provisional` in final_approval.yaml must be a list of label ids")
    unknown = sorted(str(a) for a in acknowledged if str(a) not in chosen)
    if unknown:
        raise FinalLockError(f"`acknowledge_provisional` names labels that are not in the selection: {', '.join(unknown)}")
    missing_ack = [label for label in provisional if label not in {str(a) for a in acknowledged}]
    if missing_ack:
        raise FinalLockError("the final evaluation stays locked: the selection is PROVISIONAL for "
                             f"{', '.join(missing_ack)} (no model passed every gate). The reviewer must list every "
                             "provisional label in `acknowledge_provisional: [...]` in final_approval.yaml.")
    if paths.lock.is_file() and not (force and reason.strip()):
        raise FinalLockError("the final evaluation has already run (lock file present). A second run needs "
                             "--force and --reason \"...\"; the reason is logged.")
    return approval


def cmd_final(paths: Paths | None = None, final_flag: bool = False, force: bool = False, reason: str = "") -> dict:
    paths = paths or Paths()
    approval = check_unlocked(paths, final_flag, force, reason)  # before anything is loaded
    ctx = load_context(paths)
    selected = load_selected(ctx)
    announce(ctx, "final", 1.3 * estimate(ctx, [(label, s["model"], True) for label, s in selected.items()], n_folds=1) + 60)
    previous = os.environ.get(split_mod.FINAL_EVALUATION_ENV)
    os.environ[split_mod.FINAL_EVALUATION_ENV] = "1"
    try:
        test = split_mod.load_analytic(paths.processed, paths.splits, "test", final_evaluation=True)
    finally:
        if previous is None:
            os.environ.pop(split_mod.FINAL_EVALUATION_ENV, None)
        else:
            os.environ[split_mod.FINAL_EVALUATION_ENV] = previous
    if set(test[KEY].astype(str)) & set(ctx.frame[KEY].astype(str)):
        raise Phase3Error("development and test participants overlap")
    spec = ctx.cfg["final"]
    n_boot, version = int(spec["n_bootstrap"]), str(spec["version"])
    rows, tables = [], {}
    for label, choice in selected.items():
        model, started = choice["model"], now()
        dev = prepare(ctx, label, _tier(ctx))
        held = prepare(ctx, label, _tier(ctx), features=dev["features"], frame=test)
        ctx.log(f"final: {label} / {model}: tuning and refitting on the whole development set")
        out = train.fit_predict(model, dev["X"], dev["y"], held["X"], ctx.seed, ctx.cfg)  # tunes, calibrates, sets the threshold
        y, p = held["y"], out["p_cal"]
        pred, p_ref = (p >= out["threshold"]).astype(int), np.full(len(y), out["prevalence"])
        point = metrics.label_metrics(y, p, p_ref, pred)
        ci = metrics.bootstrap_ci(lambda i: metrics.label_metrics(y[i], p[i], p_ref[i], pred[i]) if len(np.unique(y[i])) == 2 else {},
                                  len(y), n_boot, ctx.seed)
        tables[label] = pd.DataFrame({KEY: held["ids"], "fold": 0, "y": y, "p_cal": p, "p_uncal": out["p_uncal"], "pred": pred})
        for name, value in point.items():
            low, high = ci.get(name, (float("nan"), float("nan")))
            rows.append({"label": label, "model": model, "tier": _tier(ctx), "metric": name, "value": _round(value),
                         "ci_low": _round(low), "ci_high": _round(high), "n_test_eligible": S(len(y)),
                         "n_development_eligible": S(len(dev["y"])), "n_bootstrap": n_boot})
        folder = paths.models / version / label
        folder.mkdir(parents=True, exist_ok=True)
        joblib.dump(out["model"], folder / "pipeline.joblib")
        joblib.dump(out["calibrated"], folder / "calibrator.joblib")
        (folder / "features.json").write_text(json.dumps(dev["features"], indent=1) + "\n", encoding="utf-8")
        parent = ctx.parents.get(label, label)
        config = {"label": label, "model": model, "tier": _tier(ctx), "seed": ctx.seed, "hyperparameters": out["params"],
                  "threshold": out["threshold"], "calibration": ctx.cfg["calibration"], "development_prevalence": out["prevalence"],
                  "label_card_sha256": sha256(paths.targets / f"{parent}.yaml"),
                  "selected_models_sha256": sha256(paths.selected), "phase3_config": ctx.cfg, **ctx.hashes}
        (folder / "config.json").write_text(json.dumps(config, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
        (folder / "metrics.json").write_text(json.dumps({"test": point, "ci95": ci, "n_bootstrap": n_boot}, indent=1, sort_keys=True) + "\n",
                                             encoding="utf-8")
        (folder / "model_card.md").write_text(_model_card(label, choice, config, point, ci, len(dev["y"]), len(y)), encoding="utf-8")
        registry.append(paths.registry, {"run_id": registry.run_id("final", label, _tier(ctx), model, ctx.seed, "forced" if force else ""),
                                         "stage": "final", "label": label, "tier": _tier(ctx), "model": model, "seed": ctx.seed,
                                         "variant": "forced" if force else "", **ctx.hashes, "status": "ok", "n_failed_folds": 0,
                                         **{k: _round(point.get(k)) for k in registry.METRICS}, "started_at": started, "finished_at": now()})
    if len(tables) > 1:
        merged = None
        for label, table in tables.items():
            part = table[[KEY, "y", "pred"]].rename(columns={"y": f"y_{label}", "pred": f"pred_{label}"})
            merged = part if merged is None else merged.merge(part, on=KEY, how="inner")

        def system(index: np.ndarray) -> dict:
            part = merged.iloc[index]
            wrong = [(part[f"y_{name}"] != part[f"pred_{name}"]).mean() for name in tables]
            f1 = [metrics.threshold_metrics(part[f"y_{name}"], part[f"pred_{name}"])["f1"] for name in tables]
            return {"hamming_loss": float(np.mean(wrong)), "macro_f1_all_eligible": float(np.mean(f1))}

        if len(merged) >= 10:
            point, ci = system(np.arange(len(merged))), metrics.bootstrap_ci(system, len(merged), n_boot, ctx.seed)
            for name, value in point.items():
                rows.append({"label": "ALL (eligible for every label)", "model": "selected system", "tier": _tier(ctx), "metric": name,
                             "value": _round(value), "ci_low": _round(ci.get(name, (np.nan,) * 2)[0]),
                             "ci_high": _round(ci.get(name, (np.nan,) * 2)[1]), "n_test_eligible": S(len(merged)), "n_bootstrap": n_boot})
        for name in ("auroc", "auprc", "bss", "f1"):
            values = [float(r["value"]) for r in rows if r["metric"] == name and r["label"] in tables and r["value"] != ""]
            if len(values) == len(tables):
                rows.append({"label": "ALL (macro over labels)", "model": "selected system", "tier": _tier(ctx), "metric": name,
                             "value": _round(np.mean(values)), "n_bootstrap": ""})
    out_dir = paths.processed / "final"  # participant level, git-ignored
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, table in tables.items():
        table.drop(columns="fold").to_parquet(out_dir / f"test_predictions_{label}.parquet", index=False)
    write_csv(ctx, rows, "final_test_results.csv")
    history = json.loads(paths.lock.read_text(encoding="utf-8")).get("runs", []) if paths.lock.is_file() else []
    history.append({"finished_at": now(), "reviewer": str(approval["reviewer"]), "approval_date": str(approval["date"]),
                    "selected_models_sha256": sha256(paths.selected), "forced": bool(force), "reason": reason, **ctx.hashes})
    paths.lock.write_text(json.dumps({"locked": True, "runs": history}, indent=1) + "\n", encoding="utf-8")
    privacy_check(ctx, extra_ids=list(test[KEY].astype(str)))
    ctx.log(f"final evaluation finished; models in {paths.models / version}; lock written")
    return {"results": paths.reports / "final_test_results.csv", "models": paths.models / version}


def _model_card(label: str, choice: dict, config: dict, point: dict, ci: dict, n_dev: int, n_test: int) -> str:
    lines = [f"# Model card: {label} ({config['model']}, {config['tier']} tier)", "",
             "Research proxy signal, **not a clinical diagnosis**. Trained on PPMI baseline data; no external validation.", "",
             f"- Label card SHA-256: {config['label_card_sha256']}",
             f"- Development participants (eligible): {S(n_dev)}; test participants (eligible): {S(n_test)}",
             f"- Selection: tie set {', '.join(choice['tie_set'])}; gates passed: {choice['gates_passed']}; "
             f"leakage flag: {choice['leakage_flag']}",
             f"- Calibration: {config['calibration']['method']} (cv = {config['calibration']['cv']}); decision threshold "
             f"{config['threshold']:.4f} (chosen on the development set)",
             f"- Seed: {config['seed']}", "", "## Test-set metrics (single evaluation, 95% bootstrap interval)", "",
             "| Metric | Value | 95% CI |", "|---|---|---|"]
    for name, value in point.items():
        low, high = ci.get(name, (float("nan"), float("nan")))
        lines.append(f"| {name} | {value:.4f} | {low:.4f} to {high:.4f} |")
    lines += ["", "Files: `pipeline.joblib` (uncalibrated pipeline with preprocessing), `calibrator.joblib` (calibrated model used "
              "for probabilities), `features.json`, `config.json`, `metrics.json`.", ""]
    return "\n".join(lines) + "\n"
