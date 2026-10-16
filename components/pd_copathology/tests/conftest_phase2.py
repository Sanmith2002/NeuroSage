"""Helpers shared by the Phase 2 tests: a synthetic download and isolated output paths."""

from __future__ import annotations

from pathlib import Path

import yaml

from copath.phase2 import Paths

from .fixtures import build_phase2_fixtures as fx


def isolated_paths(work: Path, expected_counts: dict | None = None, **changes) -> Paths:
    """Phase 2 paths under ``work``, with the drift guard set to the synthetic universe.

    The frozen scientific files (target cards, leakage matrix, drug lists) are
    the real ones; only the output folders and the expected counts differ.
    """
    defaults = Paths()
    cfg = yaml.safe_load(defaults.config.read_text(encoding="utf-8"))
    cfg["universe"]["expected_counts"] = dict(expected_counts or fx.COUNTS)
    cfg["lumipulse_gmm"]["min_development_n"] = 30
    cfg.update(changes.pop("config_changes", {}))
    config = work / "phase2.yaml"
    work.mkdir(parents=True, exist_ok=True)
    config.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    paths = Paths(config=config, frozen=work / "frozen", processed=work / "processed", splits=work / "splits",
                  reports=work / "reports" / "phase2", audit_manifest=work / "no_audit_manifest.json",
                  registry=work / "experiments" / "registry.csv")
    for key, value in changes.items():
        setattr(paths, key, value)
    return paths
