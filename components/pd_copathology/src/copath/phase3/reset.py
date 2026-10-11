"""``reset-cv``: remove ONLY the Phase 3 cross-validation outputs so that `cv` can be restarted from scratch.

Removed: registry rows of stage ``cv``, the run details ``experiments/phase3/cv-*.json``, the
out-of-fold predictions in ``data/processed/oof/`` and the cv report files in ``reports/phase3``.
Untouched: Phase 2 outputs, the frozen split, the Lumipulse GMM and every other file.

It refuses (changing nothing) when a final run or the lock file exists, and when results that were
derived from the cv runs exist (robustness or extras runs, a selection, SHAP files): those would mix
the old and the new pipeline. The command reads file names and registry rows only, never participant data.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..training import registry
from .core import Paths, Phase3Error

CV_REPORT_FILES = ("baseline_results.csv", "candidate_results.csv", "leakage_checks.csv", "dropped_features.csv")
DERIVED_FILES = ("selection_preliminary.json",)  # in experiments/phase3, written by `select --stage preliminary`


def _final_artifacts(paths: Paths, rows: list[dict]) -> list[str]:
    found = []
    if paths.lock.is_file():
        found.append(f"lock file {paths.lock.name}")
    if any(r["stage"] == "final" for r in rows):
        found.append("final run(s) in the registry")
    if (paths.processed / "final").is_dir() and any((paths.processed / "final").iterdir()):
        found.append("data/processed/final")
    if paths.models.is_dir() and any(p.name != ".gitkeep" for p in paths.models.iterdir()):
        found.append("models/final contents")
    return found


def _derived_artifacts(paths: Paths, rows: list[dict]) -> list[str]:
    found = sorted({f"{r['stage']} runs in the registry" for r in rows if r["stage"] not in ("cv", "final")})
    found += [f"experiments/phase3/{name}" for name in DERIVED_FILES if (paths.runs / name).is_file()]
    if paths.selected.is_file():
        found.append(f"configs/frozen/{paths.selected.name}")
    if paths.shap.is_dir() and any(paths.shap.iterdir()):
        found.append("data/processed/shap")
    return found


def plan(paths: Paths) -> dict:
    """What `reset-cv --confirm` would remove. Raises Phase3Error when the reset is refused."""
    rows = registry.read(paths.registry)
    blocked = _final_artifacts(paths, rows)
    if blocked:
        raise Phase3Error("reset-cv refused: the final evaluation has run or its files exist (" + "; ".join(blocked) + "). "
                          "Nothing was changed.")
    derived = _derived_artifacts(paths, rows)
    if derived:
        raise Phase3Error("reset-cv refused: results derived from the cv runs exist (" + "; ".join(derived) + "), and they would "
                          "mix the old and the new pipeline. Nothing was changed; remove them deliberately first.")
    files = sorted(paths.runs.glob("cv-*.json")) if paths.runs.is_dir() else []
    files += sorted(paths.oof.glob("*")) if paths.oof.is_dir() else []
    files += [paths.reports / name for name in CV_REPORT_FILES if (paths.reports / name).is_file()]
    figures = paths.reports / "figures"
    files += sorted(figures.glob("cv_curves_*.png")) if figures.is_dir() else []
    return {"registry_rows": sum(r["stage"] == "cv" for r in rows), "files": [f for f in files if f.is_file()]}


def _drop_cv_rows(path: Path) -> None:
    """Rewrite the registry without its cv rows (same header; other stages untouched)."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header, kept = list(reader.fieldnames or registry.COLUMNS), [r for r in reader if r.get("stage") != "cv"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)


def cmd_reset_cv(paths: Paths | None = None, confirm: bool = False, log=print) -> dict:
    paths = paths or Paths()
    found = plan(paths)
    log(f"reset-cv: {found['registry_rows']} registry row(s) of stage cv and {len(found['files'])} cv file(s) "
        "(run details, out-of-fold predictions, cv reports) {}".format("will be removed" if not confirm else "removed"))
    if not confirm:
        raise Phase3Error("nothing was removed: run `python -m copath.phase3 reset-cv --confirm` to remove the cv outputs listed above")
    for f in found["files"]:
        f.unlink()
    if paths.registry.is_file():
        _drop_cv_rows(paths.registry)
    return found
