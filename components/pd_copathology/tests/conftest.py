"""Shared fixtures. Every test runs against synthetic data only."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from .fixtures import build_fixtures


@pytest.fixture(autouse=True)
def _never_touch_real_data(monkeypatch):
    """Tests must not resolve the developer's real PPMI directory."""
    monkeypatch.delenv("PPMI_DATA_ROOT", raising=False)
    monkeypatch.setenv("COPATH_DISABLE_DOTENV", "1")


@pytest.fixture(scope="session")
def synthetic_root() -> Path:
    return build_fixtures.build(build_fixtures.DEFAULT_DEST)


def snapshot(root: Path) -> dict[str, tuple[int, int, str]]:
    """Size, modification time and SHA-256 of every file under ``root``."""
    return {
        p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(root.rglob("*")) if p.is_file()
    }


@pytest.fixture(scope="session")
def audit_run(synthetic_root, tmp_path_factory):
    """One full audit of the synthetic download, shared by the read-only tests."""
    from copath.data.audit import AuditConfig, run_audit

    work = tmp_path_factory.mktemp("audit_run")
    before = snapshot(synthetic_root)
    result = run_audit(synthetic_root, work / "reports", work / "interim", AuditConfig())
    return {
        "root": synthetic_root, "work": work, "reports": work / "reports", "audit": work / "reports" / "audit",
        "interim": work / "interim", "result": result, "before": before, "after": snapshot(synthetic_root),
    }
