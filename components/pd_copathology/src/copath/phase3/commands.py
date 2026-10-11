"""Phase 3 commands 1-6: cv, select, robustness, extras, explain. Development data only."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..evaluation import metrics, selection
from ..explain import shap_explainer
from ..models import baselines, candidates
from ..targets import builders
from ..training import registry
from . import figures
from .core import (KEY, Context, Phase3Error, S, _round, announce, estimate, find_run, fold_params, load_oof, metric_rows,
                   modality_of, prepare, privacy_check, run, sha256, tier_features, write_csv, write_text)


def _labels(ctx: Context) -> list[str]:
    return list(ctx.cfg["labels"])


def _tier(ctx: Context) -> str:
    return ctx.cfg.get("main_tier", "primary")


def _cv_id(ctx: Context, label: str, model: str) -> str:
    return registry.run_id("cv", label, _tier(ctx), model, ctx.seed)


def _cv(ctx: Context, label: str, model: str, required: bool = True) -> dict | None:
    details = find_run(ctx, _cv_id(ctx, label, model))
    if details is None and required:
        raise Phase3Error(f"no cv result for {label} / {model} under the current data and configuration: run `cv` first")
    return details


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


# --------------------------------------------------------------------------
# 1. cv
# --------------------------------------------------------------------------

def cmd_cv(ctx: Context, labels: list[str] | None = None, models: list[str] | None = None) -> None:
    """Baselines, the missingness-only check and every candidate on the primary tier, nested CV."""
    wanted_models = [m for m in (*ctx.cfg["baselines"], baselines.LEAKAGE_CHECK, *ctx.cfg["candidates"])
                     if not models or m in models]
    wanted_labels = [name for name in _labels(ctx) if not labels or name in labels]
    todo = [(name, m) for name in wanted_labels for m in wanted_models if find_run(ctx, _cv_id(ctx, name, m)) is None]
    announce(ctx, "cv", estimate(ctx, [(name, m, True) for name, m in todo]))
    for i, (label, model) in enumerate(todo, start=1):
        ctx.log(f"cv run {i}/{len(todo)}: {label} / {model}")
        run(ctx, "cv", label, _tier(ctx), model, ctx.seed)
    cv_reports(ctx)
    privacy_check(ctx)


def cv_reports(ctx: Context) -> None:
    base_rows, cand_rows, leak_rows, curves = [], [], [], {}
    flag_at = float(ctx.cfg["leakage_checks"]["missingness_auroc_flag"])
    preds: dict[str, dict[str, pd.DataFrame]] = {}
    for label in _labels(ctx):
        floor = _cv(ctx, label, "b0b", required=False)
        for model in ctx.cfg["baselines"]:
            details = _cv(ctx, label, model, required=False)
            if details:
                base_rows += metric_rows(details)
        check = _cv(ctx, label, baselines.LEAKAGE_CHECK, required=False)
        if check and check.get("summary"):
            auroc = check["summary"]["pooled"]["auroc"]
            leak_rows.append({"label": label, "check": "missingness-only model (AUROC)", "model": baselines.LEAKAGE_CHECK,
                              "auroc": _round(auroc), "mean_auroc": _round(check["summary"]["mean"]["auroc"]),
                              "sd_auroc": _round(check["summary"]["sd"]["auroc"]), "auprc": _round(check["summary"]["pooled"]["auprc"]),
                              "threshold": flag_at, "flagged": bool(auroc > flag_at),
                              "note": "which measurements exist predicts the label" if auroc > flag_at else ""})
        for model in ctx.cfg["candidates"]:
            details = _cv(ctx, label, model, required=False)
            if not details:
                continue
            cand_rows += metric_rows(details)
            if details.get("summary"):
                oof = load_oof(ctx, details["run_id"])
                curves.setdefault(label, {})[model] = oof
                preds.setdefault(model, {})[label] = oof
                if floor and floor.get("summary"):
                    mine, theirs = details["summary"]["pooled"]["auprc"], floor["summary"]["pooled"]["auprc"]
                    leak_rows.append({"label": label, "check": "age + sex floor (AUPRC)", "model": model, "auprc": _round(mine),
                                      "threshold": _round(theirs), "flagged": bool(not mine > theirs),
                                      "note": "" if mine > theirs else "does not beat the age + sex baseline"})
    for model, by_label in preds.items():  # system-level rows: one model family across the three labels
        if set(by_label) != set(_labels(ctx)):
            continue
        pooled = [_cv(ctx, name, model)["summary"]["pooled"] for name in _labels(ctx)]
        multi = metrics.multilabel(by_label)
        cand_rows.append({"label": "ALL (macro over labels)", "tier": _tier(ctx), "model": model, "scope": "pooled",
                          **{m: _round(np.mean([p[m] for p in pooled])) for m in ("auroc", "auprc", "bss", "f1")},
                          "n_all_eligible": S(multi["n_all_eligible"]),
                          **{k: _round(v) for k, v in multi.items() if k not in ("n_all_eligible", "folds")}})
    if base_rows:
        write_csv(ctx, base_rows, "baseline_results.csv")
    if cand_rows:
        write_csv(ctx, cand_rows, "candidate_results.csv")
    if leak_rows:
        write_csv(ctx, leak_rows, "leakage_checks.csv")
    for label, by_model in curves.items():
        figures.curves(by_model, label, ctx.paths.reports / "figures")


# --------------------------------------------------------------------------
# 2. select --stage preliminary
# --------------------------------------------------------------------------

def _preliminary_path(ctx: Context) -> Path:
    return ctx.paths.runs / "selection_preliminary.json"


def cmd_select_preliminary(ctx: Context) -> dict:
    spec, flag_at = ctx.cfg["selection"], float(ctx.cfg["leakage_checks"]["missingness_auroc_flag"])
    out = {"hashes": ctx.hashes, "labels": {}}
    lines = ["# Preliminary model selection (stage 1)", "",
             "Protocol: `docs/selection_protocol.md`, sections 4.1-4.4. Development set, primary tier, calibrated "
             "out-of-fold predictions. Score = mean Brier Skill Score over the five outer folds; the tie set is every "
             "eligible model within one standard error of the best. Failed models are listed, not hidden.", ""]
    for label in _labels(ctx):
        results = {m: _cv(ctx, label, m) for m in ctx.cfg["candidates"]}
        b0a, b0b, check = _cv(ctx, label, "b0a"), _cv(ctx, label, "b0b"), _cv(ctx, label, baselines.LEAKAGE_CHECK)
        usable = {m: d for m, d in results.items() if d.get("summary")}
        for m, d in usable.items():
            d.update(pooled=d["summary"]["pooled"], mean=d["summary"]["mean"], se=d["summary"]["se"])
        base = [{"pooled": d["summary"]["pooled"]} for d in (b0a, b0b)]
        stage1 = selection.preliminary(usable, base[0], base[1], spec)
        leak_auroc = check["summary"]["pooled"]["auroc"] if check.get("summary") else float("nan")
        stage1["leakage_flag"] = bool(leak_auroc > flag_at)
        stage1["missingness_auroc"] = leak_auroc
        out["labels"][label] = stage1
        lines += [f"## {label}", "", f"Eligible development participants: {S(b0a['n_eligible'])}; features: {results[ctx.cfg['candidates'][0]]['n_features']}.",
                  f"Baselines (pooled): prevalence Brier {b0a['summary']['pooled']['brier']:.4f}; age + sex AUPRC "
                  f"{b0b['summary']['pooled']['auprc']:.4f}, AUROC {b0b['summary']['pooled']['auroc']:.4f}.",
                  f"Leakage check: missingness-only AUROC {leak_auroc:.3f} "
                  + (f"- **FLAGGED** (above {flag_at:g}): which measurements exist predicts this label; address in the review."
                     if stage1["leakage_flag"] else f"(not above {flag_at:g})."), "",
                  "| Model | Score (mean fold BSS) | SE | Pooled BSS | Slope | AUROC | AUPRC | " + " | ".join(g.split()[0] for g in selection.GATES) + " |",
                  "|---|---|---|---|---|---|---|" + "---|" * len(selection.GATES)]
        for model in ctx.cfg["candidates"]:
            row = stage1["table"].get(model)
            if row is None:
                lines.append(f"| {model} | every fold failed | | | | | | " + " | ".join(["fail"] * len(selection.GATES)) + " |")
                continue
            pooled = usable[model]["pooled"]
            lines.append(f"| {model} | {row['score']:.4f} | {row['se']:.4f} | {pooled['bss']:.4f} | {pooled['cal_slope']:.3f} "
                         f"| {pooled['auroc']:.4f} | {pooled['auprc']:.4f} | "
                         + " | ".join("pass" if row["gates"][g] else "**fail**" for g in selection.GATES) + " |")
        lines += ["", "Gates: " + "; ".join(selection.GATES) + ".", ""]
        if stage1["best"] is None:
            lines += ["**No model can be ranked for this label (every candidate has a failed fold). Nothing is selected.**", ""]
        else:
            status = ("all gates passed" if stage1["gates_passed"] else
                      "**PROVISIONAL - no model passed every gate** (protocol 4.4); needs an explicit decision in the review")
            lines += [f"Best: **{stage1['best']}**. Tie set (within 1 SE): **{', '.join(stage1['tie_set'])}**. Status: {status}.", ""]
    families = {}
    for model in ctx.cfg["candidates"]:
        scores = [out["labels"][name]["table"].get(model, {}).get("score") for name in _labels(ctx)]
        if all(s is not None for s in scores):
            families[model] = float(np.mean(scores))
    best = [out["labels"][name]["table"][out["labels"][name]["best"]]["score"] for name in _labels(ctx) if out["labels"][name]["best"]]
    lines += ["## System level (macro Brier Skill Score over the three labels)", "", "| System | Macro BSS |", "|---|---|"]
    lines += [f"| {model} for every label | {value:.4f} |" for model, value in families.items()]
    if len(best) == len(_labels(ctx)):
        lines.append(f"| best model per label | {float(np.mean(best)):.4f} |")
    lines += ["", "Next: `python -m copath.phase3 robustness`, then `python -m copath.phase3 select --stage final`.", ""]
    write_text(ctx, "\n".join(lines) + "\n", ctx.paths.reports / "selection_preliminary.md")
    _preliminary_path(ctx).parent.mkdir(parents=True, exist_ok=True)
    _preliminary_path(ctx).write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    privacy_check(ctx)
    return out


def _preliminary(ctx: Context) -> dict:
    path = _preliminary_path(ctx)
    if not path.is_file():
        raise Phase3Error("no preliminary selection found: run `select --stage preliminary` first")
    stored = json.loads(path.read_text(encoding="utf-8"))
    if stored["hashes"] != ctx.hashes:
        raise Phase3Error("the preliminary selection belongs to other data or another configuration: run it again")
    return stored["labels"]


# --------------------------------------------------------------------------
# 3. robustness
# --------------------------------------------------------------------------

def _robustness_runs(ctx: Context, label: str, model: str) -> list[tuple[str, int]]:
    seeds = [ctx.seed + i for i in range(int(ctx.cfg["robustness"]["n_seeds"]))]
    return [(ctx.cfg.get("robustness_tier", "strict"), ctx.seed)] + [(_tier(ctx), s) for s in seeds]


def cmd_robustness(ctx: Context) -> None:
    """Strict tier, three seeds and SHAP stability for every tie-set model; hyperparameters reused from cv."""
    stage1 = _preliminary(ctx)
    pairs = [(label, model) for label in _labels(ctx) for model in stage1[label]["tie_set"]]
    announce(ctx, "robustness", (1 + int(ctx.cfg["robustness"]["n_seeds"])) * 1.3 * estimate(ctx, [(label, model, False) for label, model in pairs]))
    rows_per_fold = int(ctx.cfg["robustness"]["shap_rows_per_fold"])
    for label, model in pairs:
        params = fold_params(_cv(ctx, label, model))
        for tier, seed in _robustness_runs(ctx, label, model):
            run(ctx, "robustness", label, tier, model, seed, params=params, shap_rows=rows_per_fold)
    robustness_reports(ctx, pairs)
    privacy_check(ctx)


def _robustness_evidence(ctx: Context, label: str, model: str) -> dict:
    """Everything stage 2 needs for one tie-set model. Raises when a robustness run is missing."""
    cv, top_k = _cv(ctx, label, model), int(ctx.cfg["robustness"]["top_k"])
    runs = {}
    for tier, seed in _robustness_runs(ctx, label, model):
        details = find_run(ctx, registry.run_id("robustness", label, tier, model, seed))
        if details is None or not details.get("summary") or not details.get("shap"):
            raise Phase3Error(f"robustness results are missing for {label} / {model} ({tier}, seed {seed}): run `robustness` first")
        runs[(tier, seed)] = details
    strict_tier = ctx.cfg.get("robustness_tier", "strict")
    rankings = {tier: [pd.Series(v) for (t, _), d in runs.items() if t == tier for v in d["shap"]["folds"].values()]
                for tier in (_tier(ctx), strict_tier)}
    strict = runs[(strict_tier, ctx.seed)]
    by_fold = {int(k): v["bss"] for k, v in cv["summary"]["folds"].items()}
    differences = [v["bss"] - by_fold[int(k)] for k, v in strict["summary"]["folds"].items() if int(k) in by_fold]
    return {"runs": runs, "stability": {tier: shap_explainer.stability(r, top_k) for tier, r in rankings.items()},
            "slope_distance": abs(cv["summary"]["pooled"]["cal_slope"] - 1), "slope": cv["summary"]["pooled"]["cal_slope"],
            "jaccard": shap_explainer.stability(rankings[_tier(ctx)], top_k)["mean_jaccard"],
            "strict_drop": cv["summary"]["mean"]["bss"] - strict["summary"]["mean"]["bss"],
            "sd_strict_difference": float(np.std(differences, ddof=1)) if len(differences) > 1 else float("nan"),
            "space": strict["shap"]["space"], "explainer": strict["shap"]["explainer"],
            "n_features_strict": strict["n_features"], "n_features_primary": cv["n_features"]}


def robustness_reports(ctx: Context, pairs: list[tuple[str, str]]) -> None:
    rows, stability_rows = [], []
    for label, model in pairs:
        evidence = _robustness_evidence(ctx, label, model)
        for (tier, seed), details in evidence["runs"].items():
            summary = details["summary"]
            row = {"label": label, "model": model, "tier": tier, "seed": seed, "n_eligible": S(details["n_eligible"]),
                   "n_features": details["n_features"], "n_failed_folds": details["n_failed_folds"],
                   **{m: _round(summary["pooled"][m]) for m in metrics.LABEL_METRICS},
                   "mean_bss": _round(summary["mean"]["bss"]), "sd_bss": _round(summary["sd"]["bss"]),
                   "delta_bss_vs_primary_cv": "", "sd_delta_bss_vs_primary_cv": ""}
            if tier != _tier(ctx):
                row["delta_bss_vs_primary_cv"] = _round(-evidence["strict_drop"])
                row["sd_delta_bss_vs_primary_cv"] = _round(evidence["sd_strict_difference"])
            rows.append(row)
        seeds = int(ctx.cfg["robustness"]["n_seeds"])
        for tier, text in ((_tier(ctx), f"5 outer folds x {seeds} seeds"), (ctx.cfg.get("robustness_tier", "strict"), "5 outer folds, base seed")):
            found = evidence["stability"][tier]
            stability_rows.append({"label": label, "model": model, "tier": tier, "rankings": text, "n_rankings": found["n_rankings"],
                                   "mean_jaccard_top10": _round(found["mean_jaccard"]), "mean_kendall_tau": _round(found["mean_kendall_tau"]),
                                   "explainer": evidence["explainer"], "shap_space": evidence["space"]})
    write_csv(ctx, rows, "robustness_tieset.csv")
    write_csv(ctx, stability_rows, "shap_stability_tieset.csv")


# --------------------------------------------------------------------------
# 4. select --stage final
# --------------------------------------------------------------------------

def cmd_select_final(ctx: Context) -> dict:
    if ctx.paths.lock.is_file():
        raise Phase3Error("the final evaluation has already run; the selection can no longer be changed")
    stage1 = _preliminary(ctx)
    evidence = {(label, model): _robustness_evidence(ctx, label, model)  # raises if anything is missing
                for label in _labels(ctx) for model in stage1[label]["tie_set"]}
    spec = ctx.cfg["selection"]
    selected = {"version": "v1", "created": date.today().isoformat(), "protocol": "docs/selection_protocol.md",
                "tier": _tier(ctx), **ctx.hashes, "labels": {}}
    lines = ["# Final model selection (stage 2)", "",
             "Protocol: `docs/selection_protocol.md`, section 6. Tie-breakers are applied in order inside each tie set; "
             "after each one only the models within the stated tolerance of the best remain.", ""]
    preds = {}
    for label in _labels(ctx):
        info, tie_set = stage1[label], stage1[label]["tie_set"]
        lines += [f"## {label}", ""]
        if not tie_set:
            lines += ["**Nothing selected: no candidate could be ranked (see the preliminary report).**", ""]
            continue
        chosen, reasoning = selection.final_choice(tie_set, {m: evidence[(label, m)] for m in tie_set}, spec)
        failed = [g for g, ok in info["table"][chosen]["gates"].items() if not ok]
        cv = _cv(ctx, label, chosen)
        selected["labels"][label] = {
            "model": chosen, "tier": _tier(ctx), "tie_set": list(tie_set), "gates_passed": bool(info["gates_passed"]),
            "failed_gates": failed, "leakage_flag": bool(info["leakage_flag"]), "cv_run_id": cv["run_id"],
            "hyperparameters": "per outer fold from the cv run (experiments/phase3/<cv_run_id>.json); "
                               "the final refit re-tunes on the whole development set"}
        preds[label] = load_oof(ctx, cv["run_id"])
        lines += [f"Tie set from stage 1: {', '.join(tie_set)}.", "",
                  "| Model | Score (mean fold BSS) | Slope | abs(slope - 1) | SHAP top-10 Jaccard | Kendall tau | Strict-tier BSS | Drop primary -> strict | SHAP space |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for model in tie_set:
            e = evidence[(label, model)]
            strict = e["runs"][(ctx.cfg.get("robustness_tier", "strict"), ctx.seed)]["summary"]["mean"]["bss"]
            lines.append(f"| {model} | {info['table'][model]['score']:.4f} | {e['slope']:.3f} | {e['slope_distance']:.3f} "
                         f"| {e['jaccard']:.3f} | {e['stability'][_tier(ctx)]['mean_kendall_tau']:.3f} | {strict:.4f} "
                         f"| {e['strict_drop']:.4f} | {e['space']} |")
        lines += ["", "Reasoning:", ""] + [f"- {step}" for step in reasoning] + ["", f"**Selected: {chosen}** (primary tier)."]
        if not info["gates_passed"]:
            lines.append(f"**PROVISIONAL: failed gate(s): {'; '.join(failed)}. The reviewer must accept or reject this selection explicitly.**")
        if info["leakage_flag"]:
            lines.append(f"**Leakage flag: the missingness-only model reaches AUROC {info['missingness_auroc']:.3f} for this label.**")
        e = evidence[(label, chosen)]
        if e["n_features_strict"] == e["n_features_primary"]:
            lines.append("Note: this label has no near-proxy feature, so the strict and primary feature sets are the same.")
        lines.append("")
    if len(preds) == len(_labels(ctx)):
        multi = metrics.multilabel(preds)
        scores = [stage1[name]["table"][selected["labels"][name]["model"]]["score"] for name in _labels(ctx)]
        lines += ["## Selected system (development set, out-of-fold)", "",
                  f"- Macro Brier Skill Score over the three labels: {float(np.mean(scores)):.4f}",
                  f"- Participants eligible for all three labels: {S(multi['n_all_eligible'])}",
                  f"- Hamming loss: {multi['hamming_loss']:.4f}; macro-F1: {multi['macro_f1_all_eligible']:.4f}", ""]
    ctx.paths.frozen.mkdir(parents=True, exist_ok=True)
    ctx.paths.selected.write_text(yaml.safe_dump(selected, sort_keys=False, width=120), encoding="utf-8")
    digest = sha256(ctx.paths.selected)
    lines += ["## Frozen selection", "", "Written to `configs/frozen/selected_models_v1.yaml`.", "",
              f"SHA-256 of that file (needed in `configs/frozen/final_approval.yaml`): {digest}", "",
              "Next: `python -m copath.phase3 extras`, `python -m copath.phase3 explain`, then human review. "
              "The final evaluation stays locked until the approval file exists.", ""]
    write_text(ctx, "\n".join(lines) + "\n", ctx.paths.reports / "selection_final.md")
    ctx.log(f"selected_models_v1.yaml sha256: {digest}")
    privacy_check(ctx)
    return selected


def load_selected(ctx: Context) -> dict:
    if not ctx.paths.selected.is_file():
        raise Phase3Error("configs/frozen/selected_models_v1.yaml not found: run `select --stage final` first")
    selected = yaml.safe_load(ctx.paths.selected.read_text(encoding="utf-8"))
    if any(selected.get(k) != v for k, v in ctx.hashes.items()):
        raise Phase3Error("the frozen selection belongs to other data or another configuration")
    return selected["labels"]


# --------------------------------------------------------------------------
# 5. extras
# --------------------------------------------------------------------------

def _deltas(base: dict, other: dict) -> dict:
    """Mean and SD over outer folds of (other - base) for AUROC, AUPRC and BSS."""
    out = {}
    for metric in ("auroc", "auprc", "bss"):
        diffs = [other["summary"]["folds"][k][metric] - base["summary"]["folds"][k][metric]
                 for k in other["summary"]["folds"] if k in base["summary"]["folds"]]
        out[f"delta_{metric}"] = _round(np.mean(diffs)) if diffs else ""
        out[f"sd_delta_{metric}"] = _round(np.std(diffs, ddof=1)) if len(diffs) > 1 else ""
    return out


def cmd_extras(ctx: Context) -> None:
    """Modality ablation, sensitivity labels, medication-record check and calibration comparison for the selected models."""
    selected = load_selected(ctx)
    spec, tier, modality = ctx.cfg["ablation"], _tier(ctx), modality_of(ctx)
    n_runs = len(spec["modalities"]) + 1 + 4
    announce(ctx, "extras", n_runs * estimate(ctx, [(label, s["model"], False) for label, s in selected.items()]))
    ablation, sensitivity, calibration = [], [], []
    for label, choice in selected.items():
        model, base = choice["model"], _cv(ctx, label, choice["model"])
        params, features = fold_params(base), base["features"]
        # --- leave-one-modality-out, and clinical + demographics only
        groups = [(f"without {m}", [f for f in features if modality.get(f) != m]) for m in spec["modalities"]]
        groups.append(("clinical + demographics only", [f for f in features if modality.get(f) in spec["clinical_demographics"]]))
        for name, kept in groups:
            row = {"label": label, "model": model, "analysis": name, "n_features_full": len(features), "n_features_used": len(kept)}
            if len(kept) == len(features) or not kept:
                ablation.append({**row, "status": "not run: the label has no feature of this modality" if kept else "not run: no feature left"})
                continue
            details = run(ctx, "extras", label, tier, model, ctx.seed, variant=_slug(name), params=params, features=kept)
            if not details.get("summary"):
                ablation.append({**row, "status": details.get("status", "failed")})
                continue
            ablation.append({**row, "status": "ok", **{m: _round(details["summary"]["pooled"][m]) for m in ("auroc", "auprc", "bss")},
                             **_deltas(base, details)})
        # --- sensitivity labels that reuse this label's model
        sensitivity.append({"label": label, "analysis": "primary label (reference)", "model": model,
                            **_sensitivity_row(base)})
        for other, parent in (ctx.cfg.get("sensitivity_labels") or {}).items():
            if parent != label:
                continue
            if builders.label_column(other) not in ctx.frame.columns:
                sensitivity.append({"label": other, "analysis": f"sensitivity label of {label}", "model": model, "status": "label not in the dataset"})
                continue
            details = run(ctx, "extras", other, tier, model, ctx.seed, variant="sensitivity", params=params)
            sensitivity.append({"label": other, "analysis": f"sensitivity label of {label}", "model": model, **_sensitivity_row(details)})
        # --- medication-record sensitivity ("no record = not taking")
        med = ctx.cfg.get("medication_record") or {}
        if med.get("label") == label and med.get("column") in ctx.frame.columns:
            has_record = ctx.frame[med["column"]].astype(bool)
            oof = load_oof(ctx, base["run_id"])
            subset = oof[oof[KEY].isin(set(ctx.frame.loc[has_record, KEY].astype(str)))]
            sensitivity.append({"label": label, "analysis": "primary model, evaluated only on participants with >= 1 medication-log record",
                                "model": model, "status": "ok", "n_eligible": S(len(subset)),
                                **{m: _round(v) for m, v in metrics.summarise(subset)["pooled"].items()}})
            details = run(ctx, "extras", label, tier, model, ctx.seed, variant="med_record_only", params=params, restrict=has_record)
            sensitivity.append({"label": label, "analysis": "retrained and evaluated only on participants with >= 1 medication-log record",
                                "model": model, **_sensitivity_row(details)})
        # --- calibration comparison
        for method, details in (("sigmoid (selected)", base),
                                ("isotonic", run(ctx, "extras", label, tier, model, ctx.seed, variant="cal_isotonic", params=params, calibration="isotonic")),
                                ("none", run(ctx, "extras", label, tier, model, ctx.seed, variant="cal_none", params=params, calibration="none"))):
            if details.get("summary"):
                calibration.append({"label": label, "model": model, "calibration": method,
                                    **{m: _round(details["summary"]["pooled"][m]) for m in metrics.LABEL_METRICS},
                                    "mean_bss": _round(details["summary"]["mean"]["bss"]), "sd_bss": _round(details["summary"]["sd"]["bss"])})
    write_csv(ctx, ablation, "modality_ablation.csv")
    write_csv(ctx, sensitivity, "sensitivity_labels.csv")
    write_csv(ctx, calibration, "calibration_comparison.csv")
    figures.ablation(pd.DataFrame(ablation), ctx.paths.reports / "figures")
    write_text(ctx, _extras_notes(ctx), ctx.paths.reports / "extras_notes.md")
    privacy_check(ctx)


def _sensitivity_row(details: dict) -> dict:
    if not details.get("summary"):
        return {"status": details.get("status", "failed"), "n_eligible": S(details.get("n_eligible", 0))}
    summary = details["summary"]
    return {"status": "ok", "n_eligible": S(details["n_eligible"]), **{m: _round(summary["pooled"][m]) for m in metrics.LABEL_METRICS},
            "mean_bss": _round(summary["mean"]["bss"]), "sd_bss": _round(summary["sd"]["bss"])}


def _extras_notes(ctx: Context) -> str:
    """Interpretation notes that belong next to the extras tables (aggregate numbers from the Phase 2 report)."""
    moca = "baseline MoCA differs very little between AD-like positive and negative participants"
    path = ctx.paths.phase2_reports / "construct_check.csv"
    if path.is_file():
        table = pd.read_csv(path, dtype=str, keep_default_na=False)
        rows = table[table["check"] == "MoCA by AD-like status"].set_index("status")
        if {"positive", "negative"} <= set(rows.index) and rows.loc["positive", "mean_value"] and rows.loc["negative", "mean_value"]:
            moca += (f" (mean {float(rows.loc['positive', 'mean_value']):.1f} vs {float(rows.loc['negative', 'mean_value']):.1f}, "
                     "development set, `reports/phase2/construct_check.csv`)")
    return "\n".join([
        "# Notes for the extras tables", "",
        "## Construct note: cognition and the AD-like label", "",
        f"At baseline, {moca}. **Cognition does not strongly separate the biomarker groups at baseline.** The AD-like "
        "signal is a CSF biomarker proxy in a largely early-stage cohort; a model that finds little signal in cognitive "
        "scores is consistent with this and is not a modelling failure.", "",
        "## Medication-record sensitivity", "",
        "The vascular label assumes that the Concomitant Medication Log is complete (no record = not taking). "
        "`sensitivity_labels.csv` repeats the analysis for participants with at least one medication-log record. A "
        "clear difference would mean the assumption matters.", "",
        "## Sensitivity labels and censored AD-like values", "",
        "Sensitivity labels reuse the selected model family and the per-fold hyperparameters of the primary label. "
        "`ad_like_v1_uncensored` masks every participant whose ABeta42 or p-tau value is a boundary substitution for a "
        "censored assay measurement (not the participant's true value).", "",
        "## Modality ablation", "",
        "Deltas are (ablated model - full primary-tier model) per outer fold, reported as mean and SD over folds. "
        "Blood pressure and drug flags define the vascular label and are never features, so removing the "
        "vascular-evidence modality is not applicable to the vascular labels.", ""]) + "\n"


# --------------------------------------------------------------------------
# 6. explain
# --------------------------------------------------------------------------

def cmd_explain(ctx: Context) -> None:
    """SHAP reports for the selected models: out-of-fold attributions of the uncalibrated model."""
    selected = load_selected(ctx)
    spec, modality = ctx.cfg["explain"], modality_of(ctx)
    expected = yaml.safe_load(ctx.paths.expected.read_text(encoding="utf-8")) or {}
    announce(ctx, "explain", 0.3 * estimate(ctx, [(label, s["model"], False) for label, s in selected.items()]) + 120 * len(selected))
    plausibility, summary = [], ["# SHAP explanations of the selected models", "",
                                 "SHAP values explain the **uncalibrated** predictive model. Each outer-fold model explains its own "
                                 "held-out fold. Sigmoid calibration is a monotonic transformation of the model output, so it does not "
                                 "change feature rankings. Reports are aggregate only; participant-level SHAP values are in the "
                                 "git-ignored `data/processed/shap/`.", ""]
    for label, choice in selected.items():
        model, base = choice["model"], _cv(ctx, label, choice["model"])
        data, params = prepare(ctx, label, _tier(ctx), features=base["features"]), fold_params(base)
        values, rows, spaces = [], [], set()
        for k in sorted(params):
            train_rows, test_rows = data["folds"] != k, np.flatnonzero(data["folds"] == k)
            rng = np.random.default_rng(ctx.seed + int(k))
            test_rows = np.sort(rng.choice(test_rows, min(int(spec["max_rows_per_fold"]), len(test_rows)), replace=False))
            pipeline = candidates.build(model, params[k], data["y"][train_rows], ctx.seed, ctx.cfg).fit(data["X"][train_rows], data["y"][train_rows])
            result = shap_explainer.explain(model, pipeline, data["X"][train_rows], data["X"].iloc[test_rows])
            values.append(result["values"])
            rows.append(test_rows)
            spaces.add((result["explainer"], result["space"]))
            ctx.log(f"explain {label} / {model}: fold {k} done")
        values, rows = np.vstack(values), np.concatenate(rows)
        features = data["features"]
        ctx.paths.shap.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(values, columns=features).assign(**{KEY: data["ids"][rows], "fold": data["folds"][rows]}).to_parquet(
            ctx.paths.shap / f"shap_{label}.parquet", index=False)
        importance = shap_explainer.mean_abs(values, features).sort_values(ascending=False, kind="mergesort")
        total = float(importance.sum()) or 1.0
        table = pd.DataFrame({"rank": range(1, len(importance) + 1), "feature": importance.index,
                              "modality": [modality.get(f, "") for f in importance.index],
                              "mean_abs_shap": importance.round(6).to_numpy(), "pct_of_total": (100 * importance / total).round(2).to_numpy()})
        table["top_n"] = table["rank"] <= int(spec["top_n"])
        write_csv(ctx, table, f"shap_global_{label}.csv")
        grouped = table.groupby("modality").agg(n_features=("feature", "size"), mean_abs_shap_sum=("mean_abs_shap", "sum")).reset_index()
        grouped["pct_of_total"] = (100 * grouped["mean_abs_shap_sum"] / total).round(2)
        write_csv(ctx, grouped.sort_values("mean_abs_shap_sum", ascending=False), f"shap_modality_{label}.csv")
        parts = []
        for feature in table["feature"].head(int(spec["top_n"])):
            j = features.index(feature)
            binned = shap_explainer.dependence(data["X"][feature].iloc[rows], values[:, j], int(spec["dependence_bins"]))
            parts.append(binned.assign(feature=feature).round(6))
        write_csv(ctx, pd.concat(parts)[["feature", "bin", "n_in_bin", "mean_feature_value", "mean_shap"]], f"shap_dependence_{label}.csv")
        figures.shap_bars(table.head(int(spec["top_n"])), grouped, label, model, ctx.paths.reports / "figures")
        for item in expected.get(label, []):
            if "pattern" in item:
                match = table[table["feature"].str.contains(item["pattern"], regex=True)]
            else:
                match = table[table["modality"] == item["modality"]]
            best = match.iloc[0] if len(match) else None
            plausibility.append({"label": label, "model": model, "expected_item": item["item"], "n_matching_features": len(match),
                                 "best_rank": "" if best is None else int(best["rank"]), "best_feature": "" if best is None else best["feature"],
                                 "in_top_n": bool(best is not None and best["top_n"]),
                                 "pct_of_total_all_matching": "" if best is None else round(float(match["pct_of_total"].sum()), 2)})
        explainer, space = sorted(spaces)[0]
        summary += [f"## {label} - {model}", "", f"- Explainer: {explainer}", f"- SHAP / model-output space: {space}",
                    f"- Rows explained: {S(len(rows))} (each by the outer-fold model that did not train on it); features: {len(features)}", "",
                    "Top features (mean absolute SHAP): " + ", ".join(f"`{f}`" for f in table["feature"].head(int(spec["top_n"]))), ""]
    write_csv(ctx, plausibility, "shap_plausibility.csv")
    summary += ["## Plausibility", "",
                "`shap_plausibility.csv` compares the rankings with `docs/expected_features.md`, which was written before any "
                "result. An expected item outside the top features is reported and discussed; it does not change the selection.", ""]
    write_text(ctx, "\n".join(summary) + "\n", ctx.paths.reports / "shap_summary.md")
    privacy_check(ctx)
