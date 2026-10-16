"""Experiment registry: one row per run in ``experiments/registry.csv`` plus one JSON file of details per run.

A run is identified by its run ID together with the hashes of the dataset,
the fold scheme and the configuration. A command that is restarted skips
every run already registered as ``ok`` under the same three hashes.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HASHES = ["fold_scheme_sha256", "dataset_sha256", "config_sha256"]
METRICS = ["auroc", "auprc", "brier", "bss", "se_bss", "cal_slope", "cal_intercept", "ece", "f1"]
COLUMNS = ["run_id", "stage", "label", "tier", "model", "seed", "variant", *HASHES, "status", "n_failed_folds", *METRICS,
           "started_at", "finished_at", "seconds"]


def run_id(stage: str, label: str, tier: str, model: str, seed: int, variant: str = "") -> str:
    return "-".join(str(part) for part in (stage, label, tier, model, f"s{seed}", variant) if part != "")


def read(path: Path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if r.get("run_id")]


def find(path: Path, rid: str, hashes: dict) -> dict | None:
    """The latest ``ok`` row of this run under the current dataset, folds and configuration."""
    rows = [r for r in read(path) if r["run_id"] == rid and r.get("status") == "ok" and all(r.get(h) == hashes[h] for h in HASHES)]
    return rows[-1] if rows else None


def append(path: Path, row: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.is_file() or path.read_text(encoding="utf-8").split("\n", 1)[0].strip().split(",") != COLUMNS
    if fresh and path.is_file() and read(path):
        raise RuntimeError("experiments/registry.csv has rows in an older layout; move it aside before running Phase 3")
    with open(path, "w" if fresh else "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n", extrasaction="ignore")
        if fresh:
            writer.writeheader()
        writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in COLUMNS})


def save_details(runs_dir: Path, rid: str, details: dict) -> Path:
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{rid}.json"
    path.write_text(json.dumps(details, indent=1, sort_keys=True, default=_plain) + "\n", encoding="utf-8")
    return path


def load_details(runs_dir: Path, rid: str) -> dict:
    return json.loads((Path(runs_dir) / f"{rid}.json").read_text(encoding="utf-8"))


def _plain(value):
    try:
        return value.item()
    except AttributeError:
        return str(value)
