"""Run manifest for the dataset audit."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import traceback
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

AUDIT_VERSION = "1.2.0"
_PACKAGES = ["copath", "pandas", "numpy", "pyarrow", "matplotlib", "openpyxl", "python-dotenv", "PyYAML"]


def error_record(source: str, member: str, stage: str, exc: BaseException) -> dict:
    """Error record that never contains the exception message (it may quote data)."""
    location = ""
    for frame in reversed(traceback.extract_tb(exc.__traceback__)):
        if "copath" in Path(frame.filename).parts:
            location = f"{Path(frame.filename).name}:{frame.lineno} in {frame.name}"
            break
    return {"source": source, "member": member, "stage": stage,
            "exception_type": type(exc).__name__, "location": location}


def git_state(cwd: Path) -> dict[str, object]:
    """Commit SHA and dirty flag of the repository containing ``cwd`` (blank if unavailable)."""
    def run(*args: str) -> str:
        try:
            out = subprocess.run(
                ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return out.stdout.strip() if out.returncode == 0 else ""

    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "working_tree_dirty": bool(run("status", "--porcelain")),
    }


def package_versions() -> dict[str, str]:
    versions = {}
    for name in _PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def run_id(sources: list[dict[str, object]], config: dict[str, object]) -> str:
    """Deterministic identifier: same archives + same configuration + same audit version."""
    payload = json.dumps(
        {"sources": sources, "config": config, "audit_version": AUDIT_VERSION},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_manifest(sources: list[dict[str, object]], config: dict[str, object], repo_dir: Path) -> dict[str, object]:
    """Manifest content. The data-root path is deliberately not recorded."""
    return {
        "run_id": run_id(sources, config),
        "audit_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "audit_software": "copath.data.audit",
        "audit_version": AUDIT_VERSION,
        "git": git_state(repo_dir),
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "package_versions": package_versions(),
        "config": config,
        "sources": sources,
    }
