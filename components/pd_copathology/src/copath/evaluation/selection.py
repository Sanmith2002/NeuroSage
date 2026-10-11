"""Model selection exactly as written in ``docs/selection_protocol.md``.

Pure functions over small result records; nothing here reads data.
A *result* is ``{"model", "pooled": {...}, "mean": {...}, "se": {...}, "n_failed_folds"}``.
"""

from __future__ import annotations

import math

GATES = ["G1 calibration slope", "G2 beats prevalence (Brier)", "G3 beats age + sex (AUPRC)", "G4 no failed fold"]


def _ok(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def gates(result: dict, b0a: dict, b0b: dict, spec: dict) -> dict[str, bool]:
    pooled = result["pooled"]
    slope, brier, auprc = pooled.get("cal_slope"), pooled.get("brier"), pooled.get("auprc")
    low, high = float(spec["gates"]["slope_min"]), float(spec["gates"]["slope_max"])
    return {
        GATES[0]: _ok(slope) and low <= slope <= high,
        GATES[1]: _ok(brier) and _ok(b0a["pooled"].get("brier")) and brier < b0a["pooled"]["brier"],
        GATES[2]: _ok(auprc) and _ok(b0b["pooled"].get("auprc")) and auprc > b0b["pooled"]["auprc"],
        GATES[3]: int(result.get("n_failed_folds", 0)) == 0,
    }


def preliminary(results: dict[str, dict], b0a: dict, b0b: dict, spec: dict) -> dict:
    """Stage 1 for one label: gate table, best model and 1-SE tie set (sections 4.1, 4.3 and 4.4)."""
    table = {}
    for model, result in results.items():
        passed = gates(result, b0a, b0b, spec)
        table[model] = {"gates": passed, "n_failed_gates": sum(not v for v in passed.values()),
                        "score": result["mean"].get("bss"), "se": result["se"].get("bss"),
                        "pooled_bss": result["pooled"].get("bss"), "cal_slope": result["pooled"].get("cal_slope")}
    rankable = {m: t for m, t in table.items() if t["gates"][GATES[3]] and _ok(t["score"])}
    passing = {m: t for m, t in rankable.items() if t["n_failed_gates"] == 0}
    provisional = not passing
    if provisional and rankable:
        fewest = min(t["n_failed_gates"] for t in rankable.values())
        pool = {m: t for m, t in rankable.items() if t["n_failed_gates"] == fewest}
    else:
        pool = passing
    if not pool:
        return {"table": table, "best": None, "tie_set": [], "gates_passed": False, "provisional": True}
    best = max(pool, key=lambda m: pool[m]["score"])
    margin = pool[best]["se"] if _ok(pool[best]["se"]) else 0.0
    tie_set = sorted((m for m, t in pool.items() if t["score"] >= pool[best]["score"] - margin),
                     key=lambda m: -pool[m]["score"])
    return {"table": table, "best": best, "tie_set": tie_set, "gates_passed": not provisional, "provisional": provisional}


def final_choice(tie_set: list[str], evidence: dict[str, dict], spec: dict) -> tuple[str, list[str]]:
    """Stage 2 for one label: apply the tie-breakers in order (section 6). Returns the model and the reasoning.

    ``evidence[model]`` holds ``slope_distance``, ``jaccard`` and ``strict_drop``.
    """
    tolerance, order = spec["tolerances"], list(spec["simplicity"])
    remaining, reasoning = list(tie_set), []
    if len(remaining) == 1:
        return remaining[0], ["The tie set has one model; it is selected directly (robustness results recorded below)."]
    steps = [("(a) calibration slope closest to 1", "slope_distance", False, float(tolerance["slope"])),
             ("(b) SHAP top-10 stability (mean Jaccard)", "jaccard", True, float(tolerance["jaccard"])),
             ("(c) smaller drop from primary to strict tier", "strict_drop", False, float(tolerance["strict_drop"]))]
    for name, key, larger_is_better, tol in steps:
        values = {m: evidence[m].get(key) for m in remaining}
        usable = {m: v for m, v in values.items() if _ok(v)}
        if not usable:
            reasoning.append(f"{name}: not available for any remaining model; skipped.")
            continue
        best = max(usable.values()) if larger_is_better else min(usable.values())
        kept = [m for m in remaining if m in usable and abs(usable[m] - best) <= tol]
        shown = ", ".join(f"{m} = {usable[m]:.3f}" if m in usable else f"{m} = n/a" for m in remaining)
        reasoning.append(f"{name}: {shown}; within {tol:g} of the best: {', '.join(kept)}.")
        remaining = kept
        if len(remaining) == 1:
            return remaining[0], reasoning
    chosen = min(remaining, key=order.index)
    reasoning.append(f"(d) simplicity ({' > '.join(order)}): {chosen} is the simplest of {', '.join(remaining)}.")
    return chosen, reasoning
