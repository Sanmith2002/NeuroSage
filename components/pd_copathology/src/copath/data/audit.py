"""Dataset audit: table inventory, missingness, visit coverage.

Phase 1 entry point. Reads the PPMI download archives in place (read-only, no
extraction into the repository), profiles every tabular member in chunks and
writes aggregate, privacy-safe reports. Source tables are not merged.

Run it with::

    python -m copath.data.audit

The raw-data directory comes from ``PPMI_DATA_ROOT`` (environment or ``.env``).
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

import pandas as pd
import yaml

from . import archive, classify, provenance
from .audit_figures import plot_modality_upset
from .domain import DomainOverrides
from .load import COMPONENT_DIR, REPO_DIR, DataRootError, resolve_data_root
from .privacy import checkable_ids, scan_reports_for_ids
from .profiling import Registry, TableProfile, TableResult, new_participant_registry
from .summarize import AuditContext, Builder
from .table_reader import UnsupportedTableFormat, iter_table_chunks

DEFAULT_CONFIG = COMPONENT_DIR / "configs" / "audit.yaml"
DEFAULT_OVERRIDES = COMPONENT_DIR / "configs" / "domain_overrides.yaml"
REFERENCE_DIR = "reference"
DEFAULT_REPORTS_DIR = COMPONENT_DIR / "reports"
DEFAULT_INTERIM_DIR = COMPONENT_DIR / "data" / "interim"
INTERIM_FILE = "audit_participant_modality_availability.parquet"
FIGURE_FILE = "audit_modality_upset.png"
# Outputs of earlier audit versions that this version replaces.
OBSOLETE_REPORTS = ["baseline_feasibility_by_cohort.csv"]
OBSOLETE_FIGURES = "audit_modality_upset_bl_*.png"


class PrivacyCheckError(RuntimeError):
    """A participant identifier was found in a generated report."""


@dataclass
class AuditConfig:
    suppress_threshold: int = 5
    max_category_values: int = 20
    chunk_rows: int = 100_000
    max_rows_per_table: int | None = None
    skip_archives: list[str] = field(default_factory=list)
    skip_members: list[str] = field(default_factory=list)
    reference_patterns: list[str] = field(default_factory=lambda: ["final_multimodal_dataset*.csv"])
    hash_archives: bool = True
    make_figures: bool = True

    @classmethod
    def from_yaml(cls, path: Path | None) -> "AuditConfig":
        if path is None or not Path(path).is_file():
            return cls()
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__ and v is not None}
        return cls(**known)


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


_error = provenance.error_record


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _table_name(member: archive.Member, sheet: str | None) -> str:
    stem = PurePosixPath(member.file_name).stem
    return stem if sheet is None else f"{stem}#{sheet}"


def profile_member(
    root: Path, member: archive.Member, cfg: AuditConfig, pids: Registry, events: Registry, is_reference: bool,
    overrides: DomainOverrides | None = None,
) -> list[TableResult]:
    """Profile one tabular member; an Excel member yields one result per sheet."""
    note = ""
    for strict in (True, False):
        profiles: dict[str | None, TableProfile] = {}
        try:
            with archive.open_member(root, member) as stream:
                for sheet, chunk in iter_table_chunks(
                    stream, member.ext, cfg.chunk_rows, cfg.max_rows_per_table, strict=strict
                ):
                    if sheet not in profiles:
                        name, columns = _table_name(member, sheet), list(chunk.columns)
                        capture = None
                        if overrides is not None and not is_reference:
                            base = classify.split_table_name(name.split("#")[0])[0]
                            names = (name, base if sheet is None else f"{base}#{sheet}")
                            capture = overrides.capture_columns(
                                names, columns, bool(classify.detect_roles(columns).pid_cols))
                        profiles[sheet] = TableProfile(
                            member, name, sheet, columns, pids, events,
                            max_category_values=cfg.max_category_values, is_reference=is_reference,
                            capture=capture,
                        )
                    profiles[sheet].update(chunk)
            break
        except pd.errors.ParserError:
            if not strict:
                raise
            note = "malformed lines skipped"
    results = []
    for profile in profiles.values():
        result = profile.finalize()
        result.parse_note = note
        result.truncated = cfg.max_rows_per_table is not None and result.n_rows >= cfg.max_rows_per_table
        results.append(result)
    return results


def _write_reports(out, audit_dir: Path, written: list[Path]) -> None:
    audit_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in sorted(out.frames.items()):
        path = audit_dir / name
        frame.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
        written.append(path)
    for name, text in sorted(out.texts.items()):
        path = audit_dir / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)


def run_audit(
    data_root: Path,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    cfg: AuditConfig | None = None,
    overrides: DomainOverrides | None = None,
) -> dict:
    """Run the audit and return a small result summary.

    Raises :class:`PrivacyCheckError` (after deleting the generated reports) if
    a participant identifier is found in anything written under ``reports_dir``.
    """
    cfg = cfg or AuditConfig()
    overrides = overrides if overrides is not None else DomainOverrides.from_yaml(DEFAULT_OVERRIDES)
    data_root, reports_dir, interim_dir = Path(data_root), Path(reports_dir), Path(interim_dir)
    if not data_root.is_dir():
        raise DataRootError("The raw-data directory does not exist.")
    for target in (reports_dir, interim_dir):
        if _inside(target, data_root):
            raise DataRootError("Output directories must be outside the raw-data directory, which is read-only.")
    warnings.simplefilter("ignore")  # library warnings can quote cell values

    pids, events = new_participant_registry(), Registry()
    sources: list[archive.SourceInfo] = []
    errors: list[dict] = []
    tables: list[TableResult] = []

    files = archive.discover_files(data_root)
    _log(f"Found {len(files)} file(s) under the data root.")
    for index, path in enumerate(files, start=1):
        rel = path.relative_to(data_root).as_posix()
        if archive.matches_any(rel, cfg.skip_archives):
            stat = path.stat()
            sources.append(archive.SourceInfo(
                rel, "zip" if archive.extension(path.name) == ".zip" else "loose_file", stat.st_size,
                "", "", [], status="skipped", note="skipped by configuration"))
            _log(f"[{index}/{len(files)}] {rel}: skipped by configuration")
            continue
        _log(f"[{index}/{len(files)}] {rel}: reading inventory" + (" and hashing" if cfg.hash_archives else ""))
        try:
            src = archive.inspect_source(data_root, path, cfg.hash_archives)
        except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as exc:
            errors.append(_error(rel, "", "archive inventory", exc))
            sources.append(archive.SourceInfo(rel, "zip", path.stat().st_size, "", "", [],
                                              status="error", note=type(exc).__name__))
            continue
        sources.append(src)
        tabular = [m for m in src.members
                   if m.file_type == "tabular" and not archive.matches_any(m.display_path, cfg.skip_members)]
        for number, member in enumerate(tabular, start=1):
            _log(f"    table {number}/{len(tabular)}: {member.display_path}")
            is_reference = archive.matches_any(member.file_name, cfg.reference_patterns)
            try:
                found = profile_member(data_root, member, cfg, pids, events, is_reference, overrides)
                if not found:
                    raise pd.errors.EmptyDataError()
                tables.extend(found)
            except UnsupportedTableFormat as exc:
                errors.append(_error(rel, member.display_path, "unsupported format", exc))
            except Exception as exc:  # noqa: BLE001 - one bad table must not stop the audit
                errors.append(_error(rel, member.display_path, "table profiling", exc))

    tables.sort(key=lambda t: (t.member.source, t.member.display_path, t.sheet or ""))
    for number, table in enumerate(tables, start=1):
        table.table_id = f"T{number:04d}"
    errors.sort(key=lambda e: (e["source"], e["member"], e["stage"]))

    config = asdict(cfg)
    ctx = AuditContext(sources=sources, tables=tables, errors=errors, pids=pids, events=events,
                       threshold=cfg.suppress_threshold, max_category_values=cfg.max_category_values,
                       config=config, overrides=overrides)
    _log("Aggregating reports ...")
    out = Builder(ctx).build()

    audit_dir, figures_dir = reports_dir / "audit", reports_dir / "figures"
    written: list[Path] = []
    figure_made = False
    if cfg.make_figures:
        for name, upset in [(FIGURE_FILE, out.upset)] + sorted(out.upsets.items()):
            try:
                if plot_modality_upset(upset, upset.get("group_sizes", {}), figures_dir / name):
                    written.append(figures_dir / name)
                    figure_made = True
            except Exception as exc:  # noqa: BLE001 - figures are optional
                errors.append(_error("", name, "figure", exc))
    out.frames["audit_errors.csv"] = pd.DataFrame(
        errors, columns=["source", "member", "stage", "exception_type", "location"])

    checked, too_short = checkable_ids(pids.values)
    source_records = [
        {"source": s.source, "kind": s.kind, "status": s.status, "size_bytes": s.size, "sha256": s.sha256}
        for s in sources
    ]
    manifest = provenance.build_manifest(source_records, {**config, "domain_overrides": overrides.raw}, REPO_DIR)
    manifest["outputs"] = {
        "n_tables_profiled": len(tables), "n_errors": len(errors), "figure_written": figure_made,
        "report_files": sorted(list(out.frames) + list(out.texts) + ["audit_manifest.json"]),
    }
    manifest["privacy_self_check"] = {
        "performed": True, "n_identifiers_checked": len(checked),
        "n_identifiers_too_short_to_check": too_short, "suppression_threshold": cfg.suppress_threshold,
    }

    for name in OBSOLETE_REPORTS:
        (audit_dir / name).unlink(missing_ok=True)
    for stale in figures_dir.glob(OBSOLETE_FIGURES) if figures_dir.is_dir() else []:
        stale.unlink(missing_ok=True)
    _write_reports(out, audit_dir, written)
    reference_dir = audit_dir / REFERENCE_DIR
    for name, frame in sorted(out.reference.items()):
        reference_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(reference_dir / name, index=False, lineterminator="\n", encoding="utf-8")
        written.append(reference_dir / name)
    manifest_path = audit_dir / "audit_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    written.append(manifest_path)

    findings = scan_reports_for_ids(reports_dir, pids.values, exclude_dirs=(reference_dir,))
    if findings:
        for path in written:
            path.unlink(missing_ok=True)
        detail = "; ".join(f"{f['file']} [{f['location']}] x{f['n_matches']}" for f in findings[:20])
        raise PrivacyCheckError(
            "Privacy self-check failed: a participant identifier appears in generated reports. "
            f"All reports from this run were deleted. Locations: {detail}"
        )

    interim_path = None
    if out.interim is not None:
        interim_dir.mkdir(parents=True, exist_ok=True)
        interim_path = interim_dir / INTERIM_FILE
        out.interim.to_parquet(interim_path, index=False)

    return {
        "run_id": manifest["run_id"], "audit_dir": audit_dir, "figure": figures_dir / FIGURE_FILE if figure_made else None,
        "interim_file": interim_path, "n_sources": len(sources), "n_tables": len(tables), "n_errors": len(errors),
        "n_identifiers_checked": len(checked),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m copath.data.audit",
        description="Phase 1 PPMI dataset audit. Writes aggregate, privacy-safe reports only.",
    )
    parser.add_argument("--data-root", help="Raw PPMI directory. Default: PPMI_DATA_ROOT from the environment or .env.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Audit configuration YAML.")
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES), help="Domain overrides YAML.")
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR), help="Reports root (audit/ and figures/ are written inside).")
    parser.add_argument("--interim-dir", default=str(DEFAULT_INTERIM_DIR), help="Git-ignored directory for the participant-level availability table.")
    parser.add_argument("--skip-archive", action="append", default=[], metavar="PATTERN",
                        help="Glob for archives/files to skip, e.g. 'Imaging*.zip'. Repeatable.")
    parser.add_argument("--max-rows-per-table", type=int, help="Read at most this many rows per table (counts become lower bounds).")
    parser.add_argument("--chunk-rows", type=int, help="Rows per chunk when reading tables.")
    parser.add_argument("--no-hash", action="store_true", help="Do not compute SHA-256 of source files.")
    parser.add_argument("--no-figures", action="store_true", help="Do not write figures.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = AuditConfig.from_yaml(Path(args.config))
    cfg.skip_archives = list(cfg.skip_archives) + list(args.skip_archive)
    if args.max_rows_per_table:
        cfg.max_rows_per_table = args.max_rows_per_table
    if args.chunk_rows:
        cfg.chunk_rows = args.chunk_rows
    if args.no_hash:
        cfg.hash_archives = False
    if args.no_figures:
        cfg.make_figures = False
    try:
        data_root = resolve_data_root(args.data_root)
        result = run_audit(data_root, Path(args.reports_dir), Path(args.interim_dir), cfg,
                           DomainOverrides.from_yaml(Path(args.overrides)))
    except DataRootError as exc:
        _log(f"Configuration error: {exc}")
        return 2
    except PrivacyCheckError as exc:
        _log(str(exc))
        return 3
    except Exception as exc:  # noqa: BLE001 - never print a message that may quote data
        record = _error("", "", "audit", exc)
        _log(f"Audit failed: {record['exception_type']} at {record['location'] or 'unknown location'}")
        return 1
    _log(
        f"Audit finished. run_id={result['run_id']}  sources={result['n_sources']}  "
        f"tables={result['n_tables']}  errors={result['n_errors']}"
    )
    _log(f"Privacy self-check passed ({result['n_identifiers_checked']} identifiers checked).")
    _log(f"Aggregate reports: {result['audit_dir']}")
    if result["interim_file"]:
        _log(f"Participant-level availability table (local only, Git-ignored): {result['interim_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
