"""Helpers shared by the Phase 3 tests: a synthetic Phase 2 output and isolated Phase 3 paths."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from copath.phase3.core import Paths

SMALL = {
    "tuning": {"inner_folds": 3, "trials": {"lr_l2": 2, "lr_enet": 2, "rf": 2, "xgb": 2, "hgb": 2}},
    "hgb": {"max_iter": 30},
    "robustness": {"n_seeds": 3, "top_k": 10, "shap_rows_per_fold": 30},
    "explain": {"max_rows_per_fold": 40, "top_n": 20, "dependence_bins": 10},
    "final": {"version": "v1.0", "n_bootstrap": 40},
    "n_jobs": 2,
    "outer_jobs": 1,
}


def phase3_paths(work: Path, phase2, **changes) -> Paths:
    """Phase 3 paths under ``work`` reading the synthetic Phase 2 outputs; the scientific files are the real ones."""
    defaults = Paths()
    cfg = yaml.safe_load(defaults.config.read_text(encoding="utf-8"))
    cfg.update(copy.deepcopy(SMALL))
    cfg.update(changes)
    work.mkdir(parents=True, exist_ok=True)
    config = work / "phase3.yaml"
    config.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return Paths(config=config, frozen=work / "frozen", processed=work / "processed", splits=phase2.splits,
                 reports=work / "reports" / "phase3", phase2_reports=phase2.reports, registry=work / "experiments" / "registry.csv",
                 runs=work / "experiments" / "phase3", models=work / "models" / "final")
