"""Cross-table aggregation of profiled tables into privacy-safe report frames.

Nothing here reads source data: it works on the aggregates held by
:class:`~copath.data.profiling.TableResult`. Conventions that the privacy
self-check relies on:

* count columns are named ``n_*`` / ``pct_*`` and counts never appear inside a
  text cell;
* every count passes through :func:`suppress` / :func:`safe_pct`;
* in Markdown, every name taken from the data is written in backticks.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd

from . import classify
from .archive import NAMED_TYPES, SourceInfo
from .domain import DomainOverrides, _as_list, matches
from .privacy import safe_pct, suppress, vet_reference_table
from .provenance import error_record
from .profiling import (
    DISTINCT_CAP, NO_VISIT, ROLE_VALUE_CAP, SENTINELS, TEST_TOKEN_CAP, Registry, TableResult,
    is_code_like, pack, token_class, unpack,
)

REFERENCE_MODALITY = "reference-only derived dataset"
_COHORT_PRIORITY = [
    "COHORT_DEFINITION", "COHORT", "APPRDX", "CONCOHORT_DEFINITION", "CONCOHORT", "SUBGROUP",
    "RESEARCH_GROUP", "GROUP", "DIAGNOSIS", "PRIMDIAG",
]
_NO_VALUE_ROLES = {
    "participant_id", "date", "free_text", "sample_id", "imaging_series_id", "row_id", "test_value",
}
_KEEP_RARE_ROLES = {
    "visit_event", "cohort_diagnosis", "test_name", "unit", "sample_matrix", "assay", "form_discriminator",
}
_STRONG_ASSOCIATION = 0.3
_VISIT_CLASSES = {"screening", "baseline", "scheduled follow-up", "unscheduled/special visit"}
_NO_COHORT = "(not in cohort source)"
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def month_index(values: pd.Series) -> pd.Series:
    """Dates as ``year * 12 + month`` (NaN when unparseable). A bare year counts as January."""
    text = values.astype(str).str.strip()
    out = pd.Series(np.nan, index=text.index, dtype="float64")
    patterns = [
        r"^(?P<m>\d{1,2})/(?P<y>\d{4})$",
        r"^(?P<y>\d{4})-(?P<m>\d{1,2})(?:-\d{1,2})?(?:[ T].*)?$",
        r"^(?P<m>\d{1,2})/\d{1,2}/(?P<y>\d{4})(?:[ T].*)?$",
    ]
    for pattern in patterns:
        found = text.str.extract(pattern)
        value = pd.to_numeric(found["y"], errors="coerce") * 12 + pd.to_numeric(found["m"], errors="coerce")
        out = out.fillna(value)
    named = text.str.extract(r"^(?P<mon>[A-Za-z]{3})[A-Za-z]*[ /-]?(?P<y>\d{4})$")
    out = out.fillna(pd.to_numeric(named["y"], errors="coerce") * 12 + named["mon"].str.lower().map(_MONTHS))
    year = text.str.extract(r"^(?P<y>\d{4})(?:\.0+)?$")
    return out.fillna(pd.to_numeric(year["y"], errors="coerce") * 12 + 1)


def find_column(frame: pd.DataFrame, name: object) -> str | None:
    wanted = str(name or "").upper()
    return next((c for c in frame.columns if c.upper() == wanted and wanted), None)


@dataclass
class Outputs:
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)
    interim: pd.DataFrame | None = None
    upset: dict = field(default_factory=dict)
    upsets: dict[str, dict] = field(default_factory=dict)  # figure name -> UpSet data
    reference: dict[str, pd.DataFrame] = field(default_factory=dict)  # verified documentation tables


@dataclass
class AuditContext:
    sources: list[SourceInfo]
    tables: list[TableResult]
    errors: list[dict]
    pids: Registry
    events: Registry
    threshold: int = 5
    max_category_values: int = 20
    config: dict = field(default_factory=dict)
    overrides: DomainOverrides = field(default_factory=DomainOverrides)


class Decoder:
    """Code -> label and item -> description lookups built from dictionary tables."""

    _ALIASES = {"CLINICAL_EVENT": "EVENT_ID", "VISIT": "EVENT_ID", "VISCODE": "EVENT_ID"}

    def __init__(self, tables: list[TableResult]) -> None:
        self.codes: dict[tuple[str, str], set] = {}
        self.descriptions: dict[str, str] = {}
        for t in tables:
            for key, labels in t.decode.items():
                self.codes.setdefault(key, set()).update(labels)
            for item, text in t.descriptions.items():
                self.descriptions.setdefault(item, text)

    def decode(self, column: str, value: str) -> str:
        item = classify.norm(column)
        value = re.sub(r"\.0+$", "", str(value).strip())
        for name in (item, self._ALIASES.get(item, item)):
            labels = self.codes.get((name, value))
            if labels:
                return " | ".join(sorted(labels)) if len(labels) <= 3 else ""
        return ""

    def describe(self, column: str) -> str:
        return self.descriptions.get(classify.norm(column), "")


def q(name: object) -> str:
    """Quote a data-derived name for Markdown."""
    text = str(name).replace("`", "'")
    return f"`{text}`" if text else "(blank)"


def md_table(headers: list[str], rows: list[list[object]], limit: int | None = None) -> str:
    if not rows:
        return "_None found._\n"
    shown = rows if limit is None else rows[:limit]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in shown]
    if limit is not None and len(rows) > limit:
        lines.append(f"\n_Showing {limit} of {len(rows)} rows; the full list is in the CSV._")
    return "\n".join(lines) + "\n"


def printable(value: str) -> str:
    """A data value that is safe to print: a short code, never a date or a long number."""
    if value == "":
        return "(blank)"
    if value == NO_VISIT:
        return value
    if not is_code_like(value) or (value.isdigit() and len(value) >= 4):
        return "(value withheld)"
    return value


def cramers_v(table: np.ndarray) -> float | str:
    """Cramér's V of a contingency table (blank when it is not defined)."""
    table = table[table.sum(axis=1) > 0][:, table.sum(axis=0) > 0]
    if table.size == 0 or min(table.shape) < 2:
        return ""
    total = table.sum()
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / total
    chi2 = float(((table - expected) ** 2 / expected).sum())
    return round(math.sqrt(chi2 / (total * (min(table.shape) - 1))), 3)


class Builder:
    """Builds every report frame and Markdown summary from an :class:`AuditContext`."""

    def __init__(self, ctx: AuditContext) -> None:
        self.ctx = ctx
        self.thr = ctx.threshold
        self.out = Outputs()
        self.data = [t for t in ctx.tables if not t.is_reference and not t.is_dictionary]
        self.refs = [t for t in ctx.tables if t.is_reference]
        self.dicts = [t for t in ctx.tables if t.is_dictionary]
        self.decoder = Decoder(self.dicts)
        self.modality: dict[str, dict] = {}
        self.mod_sets: dict[str, set] = {}
        self.table_mod_sets: dict[str, dict[str, set]] = {}
        self.concept_pairs: dict[tuple[str, str], list[np.ndarray]] = {}
        self.cohort_of: dict[int, str] = {}
        self.cohort_source: tuple[TableResult, str] | None = None
        self.cohort_conflicts = 0
        self.ov = ctx.overrides
        self.excluded: dict[str, str] = {}  # table_id -> reason it is left out of modality counts
        self.leakage: set[str] = set()  # diagnosis tables: never a feature
        self.universes: dict[str, set | None] = {"participant_status": None, "curated_bl": None}
        self.universe_tables: dict[str, str] = {}
        self.cohort_short: dict[int, str] = {}
        self.curated: TableResult | None = None
        self.field_pairs: dict[str, dict[str, np.ndarray]] = {}
        self.field_concepts: dict[str, dict[str, set]] = {}
        self.vascular_sets: dict[tuple[str, str], tuple[set, TableResult]] = {}
        self.wmh_fields: list[str] = []
        self._combo_mod: dict[str, dict[int, str]] = {}
        self._cohort_sets: dict[str, dict[str, set]] = {}
        self.reference_rows: list[dict] = []
        self.csf: dict[str, dict] = {}
        self.wmh_table: TableResult | None = None

    # ------------------------------------------------------------- helpers
    def S(self, n: int) -> int | str:
        return suppress(n, self.thr)

    def P(self, num: int, den: int) -> float | str:
        return safe_pct(num, den, self.thr)

    def part_of(self, part: int, whole: int) -> int | str:
        """A count shown next to its total: withheld when the remainder would be a small cell."""
        if 0 < whole - part < self.thr and whole >= self.thr:
            return "suppressed"
        return suppress(part, self.thr)

    def ev_label(self, code: int) -> str:
        return printable(self.ctx.events.values[code])

    def concept_set(self, target: str, *concepts: str) -> set:
        out: set = set()
        for concept in concepts:
            for arr in self.concept_pairs.get((target, concept), []):
                out.update(unpack(arr)[1].tolist())
        return out

    def concept_visit_pairs(self, target: str, *concepts: str) -> np.ndarray:
        parts = [a for c in concepts for a in self.concept_pairs.get((target, c), [])]
        if not parts:
            return np.empty(0, dtype=np.uint64)
        merged = np.unique(np.concatenate(parts))
        no_visit = self.ctx.events.code(NO_VISIT)
        return merged[unpack(merged)[0] != no_visit]

    def names(self, t: TableResult) -> tuple[str, str]:
        return (t.table_name, t.base_name)

    def pick(self, patterns: list[str], long: bool | None = None, visit: bool = False) -> TableResult | None:
        """Newest source table matching ``patterns`` (by name date, then timestamp)."""
        found = [
            t for t in self.data
            if patterns and matches(patterns, *self.names(t)) and len(t.participants)
            and (long is None or (t.long is not None) == long) and (not visit or t.roles.visit)
        ]
        return max(found, key=lambda t: (t.name_date, t.member.modified, -int(t.table_id[1:])), default=None)

    def event_codes(self, labels: list[str]) -> np.ndarray:
        wanted = set(labels)
        return np.array([i for i, v in enumerate(self.ctx.events.values) if v in wanted], dtype=np.int64)

    def visit_based(self, t: TableResult) -> bool:
        """True when most rows carry a clinic-visit code (not a log/event-driven code)."""
        rows = t.visits.get(t.roles.visit, {}).get("rows") if t.roles.visit else None
        if not rows:
            return False
        visits = sum(
            count for value, count in rows.items()
            if classify.classify_event(printable(value), self.decoder.decode(t.roles.visit, value))[0] in _VISIT_CLASSES
        )
        return visits * 2 >= sum(rows.values())

    def long_frame(self, t: TableResult) -> pd.DataFrame:
        """Distinct (combo, event, participant) rows of a long table with a modality per test."""
        frame = t.long.participants_by_combo_event()
        frame["modality"] = frame["combo"].map(self._combo_mod[t.table_id])
        return frame

    def table_sets(self, t: TableResult, labels: list[str] | None = None) -> dict[str, set]:
        """Participants of a table per modality, optionally only at the given event codes.

        Tables without clinic-visit codes (genetics, logs) count at every window.
        """
        if t.table_id in self.excluded:
            return {}
        modality = self.modality[t.table_id]["modality"]
        codes = None if labels is None or not self.visit_based(t) else self.event_codes(labels)
        if t.long is not None and len(t.long.triples):
            frame = self.long_frame(t)
            if codes is not None:
                frame = frame[frame["event"].isin(codes)]
            return {str(m): set(g.unique().tolist()) for m, g in frame.groupby("modality")["pid"]}
        if codes is None:
            return {modality: set(t.participants.tolist())}
        ev, pid = unpack(t.visits[t.roles.visit]["pairs"])
        return {modality: set(pid[np.isin(ev, codes)].tolist())}

    def cohort_names(self, universe: str) -> list[str]:
        order = list((self.ov.universe.get("cohort_short_labels") or {}).values())
        present = set(self._cohort_sets.get(universe, {}))
        return [c for c in order if c in present] + sorted(present - set(order))

    def members(self, universe: str, cohort: str) -> set:
        if cohort == "ALL":
            return self.universes[universe] or set()
        return self._cohort_sets.get(universe, {}).get(cohort, set())

    def cohort_label(self, column: str, value: str) -> str:
        shown = printable(value)
        label = self.decoder.decode(column, value)
        return f"{shown} = {label}" if label and shown == value else shown

    # --------------------------------------------------------------- build
    def build(self) -> Outputs:
        self._classify()
        self._trusted_cohort()
        self._universes()
        self._archives()
        self._tables()
        self._columns()
        self._duplicates()
        self._events()
        self._biomarkers()
        self._candidates()
        self._keywords_and_dictionaries()
        self._modalities_and_overlap()
        self._participant_counts()
        self._missingness()
        from . import phase15  # imported here: phase15 builds on this class

        self._guard("vascular concepts by cohort", self._vascular_concepts)
        self._guard("reference tables", self._reference_tables)
        phase15.run(self)
        self._interim()
        self.out.texts["medical_conditions_log_audit.md"] = self._medical_conditions_md()
        self.out.texts["reference_dataset_audit.md"] = self._reference_md()
        self.out.texts["target_feasibility_summary.md"] = self._feasibility_md()
        self.out.texts["audit_summary.md"] = self._summary_md()
        return self.out

    def _guard(self, name: str, step) -> None:
        """Run one targeted output; record a failure without its message and carry on."""
        try:
            step()
        except Exception as exc:  # noqa: BLE001 - one failing output must not stop the audit
            self.ctx.errors.append(error_record("", name, "phase 1.5 output", exc))

    def _frame(self, name: str, rows: list[dict], columns: list[str], sort: list[str] | None = None) -> pd.DataFrame:
        frame = pd.DataFrame(rows, columns=columns)
        if sort and len(frame):
            frame = frame.sort_values(sort, kind="mergesort", key=lambda s: s.astype(str)).reset_index(drop=True)
        self.out.frames[name] = frame
        return frame

    # ------------------------------------------------------ classification
    def _classify(self) -> None:
        for t in self.ctx.tables:
            if t.is_reference:
                self.modality[t.table_id] = {
                    "modality": REFERENCE_MODALITY, "modality_basis": "configured reference file",
                    "modality_detail": "not a source table", "also_matched": "", "needs_review": True,
                }
                continue
            if t.is_dictionary:
                self.modality[t.table_id] = {
                    "modality": classify.DICTIONARY, "modality_basis": "dictionary structure",
                    "modality_detail": t.dict_kind, "also_matched": "", "needs_review": False,
                }
                continue
            column_mods = [
                classify.CONCEPT_MODALITY[r.concept]
                for c in t.candidates.values() for r in c["rules"] if r.concept in classify.CONCEPT_MODALITY
            ]
            info = classify.classify_table(t.base_name, column_mods)
            override = self.ov.modality_override(*self.names(t))
            if override:
                leak = bool(override.get("leakage"))
                info = {
                    "modality": override["modality"], "modality_basis": "domain override",
                    "modality_detail": "leakage: never a feature" if leak else str(override.get("reason") or ""),
                    "also_matched": info["modality"] if info["modality"] != override["modality"] else "",
                    "needs_review": False,
                }
                if leak:
                    self.leakage.add(t.table_id)
            if self.ov.is_derived(*self.names(t)) and t.roles.pid_cols:
                info = {"modality": "curated derived dataset", "modality_basis": "domain override",
                        "modality_detail": "used for the analytic universe and named checks only",
                        "also_matched": info["modality"], "needs_review": False}
                self.excluded[t.table_id] = "curated derived dataset"
            if self.ov.is_reference_table(*self.names(t)) and not t.roles.pid_cols:
                info = {"modality": classify.DICTIONARY, "modality_basis": "domain override",
                        "modality_detail": "documentation table", "also_matched": "", "needs_review": False}
            reason = self.ov.exclusion_reason(*self.names(t))
            if reason:
                self.excluded.setdefault(t.table_id, reason)
            self.modality[t.table_id] = info
            if t.long is not None:
                per_combo = {}
                for idx, combo in enumerate(t.long.combos):
                    by_matrix = classify.matrix_modality(combo[1], combo[0])
                    if info["modality"] not in (classify.NEEDS_REVIEW, "other") and not combo[1].strip():
                        by_matrix = info["modality"]
                    per_combo[idx] = by_matrix or info["modality"]
                self._combo_mod[t.table_id] = per_combo
            sets = self.table_sets(t)
            self.table_mod_sets[t.table_id] = sets
            for mod, pids in sets.items():
                self.mod_sets.setdefault(mod, set()).update(pids)

    def _trusted_cohort(self) -> None:
        options = []
        for t in self.data:
            if self.modality[t.table_id]["modality"] != "enrollment/cohort" or t.granularity != "participant-level":
                continue
            for col in t.roles.cohort_cols:
                key = classify.norm(col)
                if key in _COHORT_PRIORITY and t.cohorts.get(col):
                    options.append((
                        "participant_status" not in classify.norm(t.base_name).lower(),
                        _COHORT_PRIORITY.index(key),
                        -int(t.name_date.replace("-", "") or 0),
                        -len(t.participants), t.member.source, t.table_id, t, col,
                    ))
        if not options:
            return
        *_, table, column = sorted(options, key=lambda o: o[:6])[0]
        self.cohort_source = (table, column)
        seen: dict[int, str] = {}
        conflicts: set = set()
        for value, pids in sorted(table.cohorts[column].items()):
            label = self.cohort_label(column, value)
            for pid in pids:
                if pid in seen and seen[pid] != label:
                    conflicts.add(pid)
                seen[pid] = label
        self.cohort_conflicts = len(conflicts)
        self.cohort_of = {p: label for p, label in seen.items() if p not in conflicts}

    def _universes(self) -> None:
        """Analytic universes: Participant_Status, and a baseline row in the curated data cut."""
        short = self.ov.universe.get("cohort_short_labels") or {}
        self.cohort_short = {p: str(short.get(label, label)) for p, label in self.cohort_of.items()}
        status = self.pick(self.ov.patterns("universe", "participant_status_table"))
        if status is None and self.cohort_source is not None:
            status = self.cohort_source[0]
        if status is not None:
            self.universes["participant_status"] = set(status.participants.tolist())
            self.universe_tables["participant_status"] = status.table_name
        curated = self.pick(self.ov.patterns("universe", "curated_table"), visit=True)
        if curated is not None:
            ev, pid = unpack(curated.visits[curated.roles.visit]["pairs"])
            baseline = set(pid[np.isin(ev, self.event_codes(self.ov.baseline_events))].tolist())
            self.universes["curated_bl"] = baseline
            self.universe_tables["curated_bl"] = curated.table_name
            self.curated = curated
        rows = []
        for name, pids in self.universes.items():
            if pids is None:
                rows.append({"universe": name, "source_table": "(no matching table found)", "cohort": "ALL",
                             "n_participants": ""})
                continue
            by_cohort: dict[str, set] = {}
            for p in pids:
                by_cohort.setdefault(self.cohort_short.get(p, _NO_COHORT), set()).add(p)
            self._cohort_sets[name] = by_cohort
            rows.append({"universe": name, "source_table": self.universe_tables[name], "cohort": "ALL",
                         "n_participants": self.S(len(pids))})
            for cohort in self.cohort_names(name):
                rows.append({"universe": name, "source_table": self.universe_tables[name], "cohort": cohort,
                             "n_participants": self.S(len(by_cohort[cohort]))})
        both = [self.universes["participant_status"], self.universes["curated_bl"]]
        if all(u is not None for u in both):
            rows.append({"universe": "curated_bl and participant_status", "source_table": "", "cohort": "ALL",
                         "n_participants": self.S(len(both[0] & both[1]))})
            rows.append({"universe": "curated_bl but not participant_status", "source_table": "", "cohort": "ALL",
                         "n_participants": self.S(len(both[1] - both[0]))})
        self._frame("analytic_universe.csv", rows, ["universe", "source_table", "cohort", "n_participants"])

    # ------------------------------------------------------------ archives
    def _archives(self) -> None:
        rows, member_rows = [], []
        for src in self.ctx.sources:
            types = [m.file_type for m in src.members]
            rows.append({
                "source": src.source, "kind": src.kind, "status": src.status, "size_bytes": src.size,
                "modified_utc": src.modified, "sha256": src.sha256, "n_members": len(src.members),
                "n_tabular": types.count("tabular"), "n_tabular_unsupported": types.count("tabular_unsupported"),
                "n_imaging": types.count("imaging"), "n_document": types.count("document"),
                "n_nested_zip": types.count("nested_zip"),
                "n_other": types.count("other") + types.count("archive_unsupported"),
                "uncompressed_bytes": sum(m.size for m in src.members), "note": src.note,
            })
            aggregate: dict[tuple, list] = {}
            for m in src.members:
                if m.file_type in NAMED_TYPES:
                    member_rows.append({
                        "source": src.source, "entry": m.display_path, "nested_in": m.nested_in or "",
                        "file_type": m.file_type, "extension": m.ext, "n_files": 1,
                        "compressed_bytes": "" if m.compressed_size is None else m.compressed_size,
                        "uncompressed_bytes": m.size, "modified": m.modified, "crc32": m.crc32,
                        "audited_as_table": m.file_type == "tabular",
                    })
                else:
                    slot = aggregate.setdefault((m.nested_in or "", m.file_type, m.ext), [0, 0, 0])
                    slot[0] += 1
                    slot[1] += m.compressed_size or 0
                    slot[2] += m.size
            for (nested, ftype, ext), (count, comp, size) in aggregate.items():
                member_rows.append({
                    "source": src.source, "entry": f"[aggregate] {ftype} {ext or '(no extension)'}",
                    "nested_in": nested, "file_type": ftype, "extension": ext, "n_files": count,
                    "compressed_bytes": comp, "uncompressed_bytes": size, "modified": "", "crc32": "",
                    "audited_as_table": False,
                })
        self._frame("archive_inventory.csv", rows, [
            "source", "kind", "status", "size_bytes", "modified_utc", "sha256", "n_members", "n_tabular",
            "n_tabular_unsupported", "n_imaging", "n_document", "n_nested_zip", "n_other",
            "uncompressed_bytes", "note"], ["source"])
        self._frame("archive_member_inventory.csv", member_rows, [
            "source", "entry", "nested_in", "file_type", "extension", "n_files", "compressed_bytes",
            "uncompressed_bytes", "modified", "crc32", "audited_as_table"], ["source", "nested_in", "entry"])

    # -------------------------------------------------------------- tables
    def _missing_pcts(self, t: TableResult) -> list[float]:
        return [100.0 * st.n_blank / t.n_rows for st in t.cols.values()] if t.n_rows else []

    def _tables(self) -> None:
        rows, key_rows = [], []
        status = self.universes["participant_status"]
        for t in self.ctx.tables:
            mod = self.modality[t.table_id]
            own = set(t.participants.tolist())
            rec = next((k for k in t.keys if k["label"] == t.recommended_key), None)
            pcts = self._missing_pcts(t)
            rows.append({
                "table_id": t.table_id, "source": t.member.source, "member_path": t.member.display_path,
                "table_name": t.table_name, "table_base_name": t.base_name, "name_date": t.name_date,
                "version_status": t.status, "format": t.member.ext.lstrip("."), "n_rows": self.S(t.n_rows),
                "n_columns": len(t.columns), "n_participants": self.S(len(t.participants)),
                "modality": mod["modality"], "modality_basis": mod["modality_basis"],
                "modality_detail": mod["modality_detail"], "also_matched": mod["also_matched"],
                "needs_review": mod["needs_review"], "granularity": t.granularity,
                "recommended_key": " + ".join(rec["columns"]) if rec else "",
                "participant_id_columns": "; ".join(t.roles.pid_cols),
                "visit_columns": "; ".join(t.roles.visit_cols),
                "cohort_columns": "; ".join(t.roles.cohort_cols),
                "date_columns": "; ".join(t.roles.date_cols),
                "is_long_format": t.roles.is_long, "is_dictionary": t.is_dictionary,
                "is_reference_derived": t.is_reference,
                "n_rows_blank_participant_id": self.S(t.n_blank_pid),
                "pct_median_column_missing": round(float(np.median(pcts)), 1) if pcts else "",
                "row_limit_applied": t.truncated, "parse_note": t.parse_note,
                "excluded_from_modalities": self.excluded.get(t.table_id, ""),
                "leakage_table": t.table_id in self.leakage,
                "visit_based": self.visit_based(t),
                "pct_participants_in_participant_status":
                    self.P(len(own & status), len(own)) if status is not None and own else "",
            })
            for k in t.keys:
                key_rows.append({
                    "table_id": t.table_id, "table_name": t.table_name, "granularity": t.granularity,
                    "candidate_key": k["label"], "key_columns": " + ".join(k["columns"]),
                    "is_unique": k["is_unique"], "n_duplicate_rows": self.S(k["duplicate_rows"]),
                    "pct_duplicate_rows": self.P(k["duplicate_rows"], t.n_rows),
                    "is_recommended": k["label"] == t.recommended_key,
                })
            if not t.keys:
                key_rows.append({
                    "table_id": t.table_id, "table_name": t.table_name, "granularity": t.granularity,
                    "candidate_key": "(no participant or row identifier found)", "key_columns": "",
                    "is_unique": False, "n_duplicate_rows": "", "pct_duplicate_rows": "",
                    "is_recommended": False,
                })
        self._frame("table_inventory.csv", rows, list(rows[0].keys()) if rows else ["table_id"], ["table_id"])
        self._frame("table_granularity_inventory.csv", key_rows, [
            "table_id", "table_name", "granularity", "candidate_key", "key_columns", "is_unique",
            "n_duplicate_rows", "pct_duplicate_rows", "is_recommended"], ["table_id"])

    def _columns(self) -> None:
        rows, value_rows = [], []
        for t in self.ctx.tables:
            for position, col in enumerate(t.columns, start=1):
                st = t.cols[col]
                role = t.roles.role_of(col)
                if not role and st.dtype == "date":
                    role = "date"
                rows.append({
                    "table_id": t.table_id, "table_name": t.table_name, "column": col, "position": position,
                    "inferred_dtype": st.dtype, "role": role,
                    "pct_missing": self.P(st.n_blank, t.n_rows),
                    "pct_na_like_text": self.P(st.n_na_like, t.n_rows),
                    "n_distinct": len(st.distinct) if st.distinct is not None else f"over {DISTINCT_CAP}",
                    "candidate_for": "; ".join(sorted({f"{r.target}: {r.concept}" for r in t.candidates.get(col, {}).get("rules", [])})),
                    "dictionary_description": self.decoder.describe(col),
                })
                if (
                    st.values is None or not st.values or role in _NO_VALUE_ROLES or st.dtype == "date"
                    or st.max_len > 40 or t.is_dictionary
                ):
                    continue
                rare = 0
                for value, count in sorted(st.values.items(), key=lambda kv: (-kv[1], kv[0])):
                    shown = printable(value)
                    if shown != value or (count < self.thr and role not in _KEEP_RARE_ROLES):
                        rare += 1
                        continue
                    value_rows.append({
                        "table_id": t.table_id, "table_name": t.table_name, "column": col, "role": role,
                        "value": value, "decode": self.decoder.decode(col, value),
                        "n_rows": self.S(count), "pct_rows": self.P(count, t.n_rows),
                    })
                if rare:
                    value_rows.append({
                        "table_id": t.table_id, "table_name": t.table_name, "column": col, "role": role,
                        "value": "(values withheld: rare or not printable)", "decode": "",
                        "n_rows": "", "pct_rows": "",
                    })
        self._frame("column_inventory.csv", rows, [
            "table_id", "table_name", "column", "position", "inferred_dtype", "role", "pct_missing",
            "pct_na_like_text", "n_distinct", "candidate_for", "dictionary_description"])
        self._frame("column_value_inventory.csv", value_rows, [
            "table_id", "table_name", "column", "role", "value", "decode", "n_rows", "pct_rows"])

    # ---------------------------------------------------------- duplicates
    def _duplicates(self) -> None:
        rows = []
        src_time = {s.source: s.modified for s in self.ctx.sources}
        groups: dict[str, list[TableResult]] = {}
        families: dict[str, list[TableResult]] = {}
        for t in self.ctx.tables:
            groups.setdefault(classify.norm(t.base_name), []).append(t)
            families.setdefault(t.family, []).append(t)

        def base_row(t: TableResult, group: str, kind: str) -> dict:
            return {
                "group": group, "group_type": kind, "table_id": t.table_id, "source": t.member.source,
                "member_path": t.member.display_path, "table_name": t.table_name,
                "version_status": t.status, "name_date": t.name_date, "modified": t.member.modified,
                "size_bytes": t.member.size, "crc32": t.member.crc32, "n_rows": self.S(t.n_rows),
                "n_columns": len(t.columns), "schema_hash": t.schema_hash,
            }

        for group, members in sorted(groups.items()):
            if len(members) < 2:
                continue
            identical = len({m.member.content_signature for m in members}) == 1
            same_schema = len({m.schema_hash for m in members}) == 1
            same_rows = len({m.n_rows for m in members}) == 1
            if identical:
                relation = "identical content"
            elif not same_schema:
                relation = "different schema"
            elif not same_rows:
                relation = "same schema, different row count"
            else:
                relation = "same schema and row count, different content"
            preferred, reason = None, "cannot be determined from names or timestamps"
            if identical:
                preferred = sorted(members, key=lambda m: m.table_id)[0]
                reason = "identical content in every copy; any copy can be used"
            else:
                for attr, text in (
                    (lambda m: m.name_date, "newest date suffix in the file name"),
                    (lambda m: m.member.modified, "newest member timestamp"),
                    (lambda m: src_time.get(m.member.source, ""), "newest archive timestamp"),
                ):
                    values = sorted({attr(m) for m in members}, reverse=True)
                    if len(values) > 1 and values[0]:
                        top = [m for m in members if attr(m) == values[0]]
                        if len(top) == 1:
                            preferred, reason = top[0], text
                            break
            for m in sorted(members, key=lambda m: m.table_id):
                row = base_row(m, group, "same table name")
                row.update({
                    "relation": relation, "same_schema": same_schema, "same_row_count": same_rows,
                    "identical_content": identical,
                    "candidate_preferred_version": preferred is not None and m.table_id == preferred.table_id,
                    "preference_reason": reason,
                    "decision": "manual review required; nothing was merged or discarded",
                })
                rows.append(row)
        for family, members in sorted(families.items()):
            statuses = {m.status for m in members}
            if len({classify.norm(m.base_name) for m in members}) < 2 or len(statuses) < 2:
                continue
            for m in sorted(members, key=lambda m: m.table_id):
                row = base_row(m, family, "Current/Pilot/Deprecated family")
                row.update({
                    "relation": "status variants of one table family: " + ", ".join(sorted(statuses)),
                    "same_schema": len({x.schema_hash for x in members}) == 1,
                    "same_row_count": len({x.n_rows for x in members}) == 1,
                    "identical_content": False, "candidate_preferred_version": False,
                    "preference_reason": "status variants are different tables; do not combine without review",
                    "decision": "manual review required; nothing was merged or discarded",
                })
                rows.append(row)
        self._frame("duplicate_version_inventory.csv", rows, [
            "group", "group_type", "table_id", "source", "member_path", "table_name", "version_status",
            "name_date", "modified", "size_bytes", "crc32", "n_rows", "n_columns", "schema_hash",
            "relation", "same_schema", "same_row_count", "identical_content",
            "candidate_preferred_version", "preference_reason", "decision"])

    # -------------------------------------------------------------- events
    def _events(self) -> None:
        rows = []
        for t in self.ctx.tables:
            for col, info in t.visits.items():
                if info["rows"] is None:
                    rows.append({
                        "table_id": t.table_id, "table_name": t.table_name, "visit_column": col,
                        "event_code": f"(more than {ROLE_VALUE_CAP} distinct values; not treated as event codes)",
                        "decode": "", "event_class": "unknown", "class_basis": "", "note": "",
                        "n_rows": "", "n_participants": "",
                    })
                    continue
                ev, pid = unpack(info["pairs"])
                frame = pd.DataFrame({"label": [self.ev_label(c) for c in ev.tolist()], "pid": pid})
                participants = frame.groupby("label")["pid"].nunique().to_dict() if len(frame) else {}
                row_counts: dict[str, int] = {}
                for value, count in info["rows"].items():
                    row_counts[printable(value)] = row_counts.get(printable(value), 0) + count
                for label, count in row_counts.items():
                    decode = self.decoder.decode(col, label)
                    cls, basis, note = classify.classify_event(label, decode)
                    if label.startswith("("):
                        cls, basis, note = "unknown", "", ""
                    rows.append({
                        "table_id": t.table_id, "table_name": t.table_name, "visit_column": col,
                        "event_code": label, "decode": decode, "event_class": cls, "class_basis": basis,
                        "note": note, "n_rows": self.S(count),
                        "n_participants": self.S(participants.get(label, 0)),
                    })
        self._frame("event_code_inventory.csv", rows, [
            "table_id", "table_name", "visit_column", "event_code", "decode", "event_class",
            "class_basis", "note", "n_rows", "n_participants"], ["table_id", "visit_column", "event_code"])

    # ---------------------------------------------------------- biomarkers
    def _token_rows(self, base: dict, tokens, n_nonnum: int, sentinels: dict, nonblank: int, cap: int) -> list[dict]:
        rows = []
        if tokens is None:
            rows.append({**base, "token": f"(more than {cap} distinct non-numeric values)",
                         "token_class": "other_text", "n_values": self.S(n_nonnum),
                         "pct_of_non_missing": self.P(n_nonnum, nonblank)})
        else:
            withheld = 0
            for token, count in sorted(tokens.items()):
                if len(token) > 24 or re.match(classify.DATE_VALUE_RE, token):
                    withheld += count
                    continue
                rows.append({**base, "token": token, "token_class": token_class(token),
                             "n_values": self.S(count), "pct_of_non_missing": self.P(count, nonblank)})
            if withheld:
                rows.append({**base, "token": "(long or date-like text withheld)", "token_class": "other_text",
                             "n_values": self.S(withheld), "pct_of_non_missing": self.P(withheld, nonblank)})
        for sentinel, count in sorted(sentinels.items()):
            rows.append({**base, "token": str(int(sentinel)),
                         "token_class": "numeric_sentinel" if sentinel < 0 else "possible_numeric_sentinel",
                         "n_values": self.S(count), "pct_of_non_missing": self.P(count, nonblank)})
        return rows

    def _biomarkers(self) -> None:
        tests, by_event, special = [], [], []
        for t in self.data:
            if t.long is None:
                continue
            L = t.long
            frame = L.participants_by_combo_event()
            n_part = frame.groupby("combo")["pid"].nunique().to_dict() if len(frame) else {}
            part_ev = frame.groupby(["combo", "event"]).size().to_dict() if len(frame) else {}
            meas_total: dict[int, int] = {}
            events_of: dict[int, set] = {}
            for (combo, ev), count in L.n_meas.items():
                meas_total[combo] = meas_total.get(combo, 0) + count
                events_of.setdefault(combo, set()).add(ev)
            table_mod = self.modality[t.table_id]["modality"]
            for idx, (test, matrix, unit, assay) in enumerate(L.combos):
                rules = classify.match_test(test)
                modality = classify.matrix_modality(matrix, test) or table_mod
                assay_text = self._assay_text(t, assay)
                base = {
                    "table_id": t.table_id, "table_name": t.table_name, "version_status": t.status,
                    "test_name": test, "sample_matrix": matrix, "units": unit, "assay": assay_text,
                }
                tests.append({
                    **base, "concept": "; ".join(sorted({f"{r.target}: {r.concept}" for r in rules})),
                    "modality": modality, "n_measurements": self.S(meas_total.get(idx, 0)),
                    "n_participants": self.S(n_part.get(idx, 0)), "n_events": len(events_of.get(idx, ())),
                    "n_numeric_values": self.S(L.n_numeric.get(idx, 0)),
                    "n_non_numeric_values": self.S(L.n_nonnum.get(idx, 0)),
                    "n_blank_values": self.S(L.n_blank.get(idx, 0)),
                })
                for ev in sorted(events_of.get(idx, ()), key=self.ev_label):
                    label = self.ev_label(ev)
                    by_event.append({
                        **base, "event_code": label,
                        "event_class": classify.classify_event(label, self.decoder.decode(t.roles.visit or "", label))[0],
                        "n_measurements": self.S(L.n_meas[(idx, ev)]),
                        "n_participants": self.S(part_ev.get((idx, ev), 0)),
                    })
                nonblank = meas_total.get(idx, 0) - L.n_blank.get(idx, 0)
                sentinels = {s: L.sentinels[(idx, s)] for s in SENTINELS if L.sentinels.get((idx, s))}
                tokens = L.tokens.get(idx, {})
                special.extend(self._token_rows(
                    {"scope": "long-format test", "table_id": t.table_id, "table_name": t.table_name,
                     "field": t.roles.value_col, "test_name": test, "units": unit},
                    tokens, L.n_nonnum.get(idx, 0), sentinels, nonblank, TEST_TOKEN_CAP))
        for t in self.data:
            for col in t.columns:
                st = t.cols[col]
                if t.roles.role_of(col):
                    continue  # identifiers, codes and assay labels are not measurements
                nonblank = t.n_rows - st.n_blank
                base = {"scope": "wide column", "table_id": t.table_id, "table_name": t.table_name,
                        "field": col, "test_name": "", "units": ""}
                if st.dtype == "numeric_with_text_tokens":
                    special.extend(self._token_rows(base, st.nonnum, st.n_nonnum, dict(st.sentinels), nonblank, 50))
                elif st.dtype in {"integer", "float"} and st.sentinels:
                    special.extend(self._token_rows(base, {}, 0, dict(st.sentinels), nonblank, 50))
        test_cols = ["table_id", "table_name", "version_status", "test_name", "sample_matrix", "units", "assay"]
        frame = self._frame("biomarker_test_inventory.csv", tests, test_cols + [
            "concept", "modality", "n_measurements", "n_participants", "n_events", "n_numeric_values",
            "n_non_numeric_values", "n_blank_values"], test_cols)
        self._frame("biomarker_test_by_event.csv", by_event, test_cols + [
            "event_code", "event_class", "n_measurements", "n_participants"], test_cols + ["event_code"])
        self._frame("biomarker_special_values.csv", special, [
            "scope", "table_id", "table_name", "field", "test_name", "units", "token", "token_class",
            "n_values", "pct_of_non_missing"], ["scope", "table_id", "field", "test_name", "token"])
        assay = frame[frame["concept"] != ""].copy() if len(frame) else frame.copy()
        if len(assay):
            variants = assay.groupby("concept")[["table_name", "units", "assay", "sample_matrix"]].apply(
                lambda g: len(g.drop_duplicates())).to_dict()
            assay["n_assay_variants_for_concept"] = assay["concept"].map(variants)
            assay["harmonisation_review_needed"] = assay["n_assay_variants_for_concept"] > 1
            assay = assay.sort_values(["concept"] + test_cols, kind="mergesort").reset_index(drop=True)
        else:
            assay["n_assay_variants_for_concept"] = []
            assay["harmonisation_review_needed"] = []
        self.out.frames["biomarker_assay_inventory.csv"] = assay[[
            "concept", "table_id", "table_name", "version_status", "test_name", "sample_matrix", "units",
            "assay", "n_participants", "n_measurements", "n_events", "n_assay_variants_for_concept",
            "harmonisation_review_needed"]]

    def _assay_text(self, t: TableResult, assay: str) -> str:
        parts = [p.strip() for p in assay.split(" / ")] if assay else []
        named = [f"{col}={part}" for col, part in zip(t.roles.assay_cols, parts) if part]
        return "; ".join(named)

    # ---------------------------------------------------------- candidates
    def _candidate_status(self, t: TableResult, target: str, concept: str, name: str) -> str:
        if t.table_id in self.excluded:
            return f"table excluded: {self.excluded[t.table_id]}"
        if t.table_id in self.leakage:
            return "leakage: diagnosis table, never a feature"
        reason = self.ov.candidate_excluded(self.names(t), target, concept, name)
        return f"excluded: {reason}" if reason else "candidate"

    def _candidates(self) -> None:
        rows = []

        def events_text(ev_counts: dict[int, int]) -> tuple[int, str]:
            ordered = sorted(ev_counts.items(), key=lambda kv: (-kv[1], self.ev_label(kv[0])))
            labels = [self.ev_label(code) for code, _ in ordered[:15]]
            extra = len(ordered) - 15
            return len(ordered), "; ".join(labels) + (f"; (and {extra} more)" if extra > 0 else "")

        for t in self.data:
            mod = self.modality[t.table_id]["modality"]
            for col, cand in t.candidates.items():
                ev, pid = unpack(cand["pairs"])
                n_events, events = events_text(dict(zip(*np.unique(ev, return_counts=True)))) if len(ev) else (0, "")
                st = t.cols[col]
                for rule in cand["rules"]:
                    status = self._candidate_status(t, rule.target, rule.concept, col)
                    if status == "candidate":
                        self.concept_pairs.setdefault((rule.target, rule.concept), []).append(cand["pairs"])
                        self.field_pairs.setdefault(t.table_id, {})[col] = cand["pairs"]
                        self.field_concepts.setdefault(t.table_id, {}).setdefault(col, set()).add(
                            (rule.target, rule.concept))
                    rows.append({
                        "target": rule.target, "concept": rule.concept, "status": status,
                        "match_type": "column name",
                        "modality": mod, "source": t.member.source, "table_id": t.table_id,
                        "table_name": t.table_name, "version_status": t.status, "field": col,
                        "test_name": "", "datatype": st.dtype, "units": "", "assay": "",
                        "n_participants": self.S(len(np.unique(pid))),
                        "pct_rows_missing": self.P(st.n_blank, t.n_rows),
                        "n_events_with_data": n_events, "events_with_data": events,
                        "dictionary_description": self.decoder.describe(col),
                        "evidence": "name pattern only; usability not verified",
                        "notes": rule.note,
                    })
            if t.long is None or not len(t.long.triples):
                continue
            matched = {idx: classify.match_test(combo[0]) for idx, combo in enumerate(t.long.combos)}
            matched = {idx: rules for idx, rules in matched.items() if rules}
            if not matched:
                continue
            frame = t.long.participants_by_combo_event()
            frame = frame[frame["combo"].isin(matched)]
            totals: dict[int, int] = {}
            for (combo, _), count in t.long.n_meas.items():
                if combo in matched:
                    totals[combo] = totals.get(combo, 0) + count
            for idx, sub in frame.groupby("combo"):
                test, matrix, unit, assay = t.long.combos[idx]
                pairs = np.unique(pack(sub["event"].to_numpy(), sub["pid"].to_numpy()))
                n_events, events = events_text(sub.groupby("event").size().to_dict())
                numeric, nonnum = t.long.n_numeric.get(idx, 0), t.long.n_nonnum.get(idx, 0)
                dtype = "numeric" if not nonnum else ("numeric_with_text_tokens" if numeric >= nonnum else "string")
                for rule in matched[idx]:
                    status = self._candidate_status(t, rule.target, rule.concept, test)
                    if status == "candidate":
                        self.concept_pairs.setdefault((rule.target, rule.concept), []).append(pairs)
                    rows.append({
                        "target": rule.target, "concept": rule.concept, "status": status,
                        "match_type": "test name (long format)",
                        "modality": classify.matrix_modality(matrix, test) or mod,
                        "source": t.member.source, "table_id": t.table_id, "table_name": t.table_name,
                        "version_status": t.status, "field": f"{t.roles.test_col} / {t.roles.value_col}",
                        "test_name": test, "datatype": dtype, "units": unit,
                        "assay": self._assay_text(t, assay),
                        "n_participants": self.S(sub["pid"].nunique()),
                        "pct_rows_missing": self.P(t.long.n_blank.get(idx, 0), totals.get(idx, 0)),
                        "n_events_with_data": n_events, "events_with_data": events,
                        "dictionary_description": "",
                        "evidence": "name pattern only; usability not verified",
                        "notes": rule.note,
                    })
        self._frame("candidate_feature_inventory.csv", rows, [
            "target", "concept", "status", "match_type", "modality", "source", "table_id", "table_name",
            "version_status", "field", "test_name", "datatype", "units", "assay", "n_participants",
            "pct_rows_missing", "n_events_with_data", "events_with_data", "dictionary_description",
            "evidence", "notes"], ["target", "concept", "table_id", "field", "test_name", "units", "assay"])

    def _keywords_and_dictionaries(self) -> None:
        rows = []
        for t in self.data:
            if t.table_id in self.excluded:
                continue
            for (col, group), (n_rows, pids) in t.keywords.items():
                self.concept_pairs.setdefault(("Vascular-risk (free text)", group), []).append(
                    pack(np.full(len(pids), self.ctx.events.code(NO_VISIT)), np.array(sorted(pids), dtype=np.int64)))
                rows.append({
                    "keyword_group": group, "table_id": t.table_id, "table_name": t.table_name, "column": col,
                    "n_records": self.S(n_rows), "n_participants": self.S(len(pids)),
                    "note": "keyword match in free text; aggregate only, wording not reviewed",
                })
        self._frame("text_keyword_inventory.csv", rows, [
            "keyword_group", "table_id", "table_name", "column", "n_records", "n_participants", "note"],
            ["keyword_group", "table_id", "column"])
        rows = [{
            "table_id": t.table_id, "source": t.member.source, "table_name": t.table_name,
            "dictionary_kind": t.dict_kind, "n_rows": self.S(t.n_rows), "n_code_entries": len(t.decode),
            "n_item_descriptions": len(t.descriptions),
        } for t in self.dicts]
        self._frame("dictionary_inventory.csv", rows, [
            "table_id", "source", "table_name", "dictionary_kind", "n_rows", "n_code_entries",
            "n_item_descriptions"], ["table_id"])

    # ------------------------------------------------- modalities / overlap
    def _groups(self, labels: list[str] | None = None) -> dict[str, set]:
        """Participants per overlap group, at any visit or only at the given event codes."""
        mod_sets: dict[str, set] = {}
        per_table: dict[str, dict[str, set]] = {}
        for t in self.data:
            sets = self.table_mod_sets[t.table_id] if labels is None else self.table_sets(t, labels)
            per_table[t.table_id] = sets
            for mod, pids in sets.items():
                mod_sets.setdefault(mod, set()).update(pids)
        groups = {
            name: set().union(*[mod_sets.get(m, set()) for m in mods])
            for name, mods in classify.OVERLAP_GROUPS.items()
        }
        for name, patterns in self.ov.group_tables().items():
            members: set = set()
            for t in self.data:
                if matches(patterns, *self.names(t)):
                    for pids in per_table[t.table_id].values():
                        members |= pids
            groups[name] = members
        return groups

    def _overlap_block(self, universe: str, cohort: str, window: str, members: set, groups: dict[str, set],
                       detailed: bool, requested: list[list[str]] | None = None) -> tuple[list[dict], dict]:
        held = {name: pids & members for name, pids in groups.items()}
        names = list(held)
        rows = []

        def add(kind: str, combo: list[str], count: int | None = None) -> None:
            n = len(set.intersection(*[held[g] for g in combo])) if count is None else count
            rows.append({
                "universe": universe, "cohort": cohort, "window": window, "kind": kind,
                "combination": " + ".join(combo), "n_modalities": len(combo),
                "n_participants": self.S(n), "n_in_universe": self.S(len(members)),
                "pct_of_universe": self.P(n, len(members)),
            })

        for name in names:
            add("single modality", [name])
        for combo in (classify.NAMED_COMBINATIONS if requested is None else requested):
            add("requested combination", list(combo))
        add("all eight modality groups" if len(names) == 8 else f"all {len(names)} modality groups", names)
        available = [g for g in names if held[g]]
        if available and available != names:
            add("all modality groups that have data", available)
        if detailed:
            for pair in combinations(names, 2):
                add("pairwise", list(pair))
            for dropped in available:
                rest = [g for g in available if g != dropped]
                if len(rest) >= 2:
                    add(f"all with data except {dropped}", rest)
        membership: dict[int, list[str]] = {}
        for name in names:
            for pid in held[name]:
                membership.setdefault(pid, []).append(name)
        exclusive: dict[tuple, int] = {}
        for pattern in membership.values():
            exclusive[tuple(pattern)] = exclusive.get(tuple(pattern), 0) + 1
        ordered = sorted(exclusive.items(), key=lambda kv: (-kv[1], kv[0]))
        for pattern, count in ordered:
            add("exclusive pattern (exactly these modality groups)", list(pattern), count)
        upset = {
            "groups": names,
            "patterns": [(list(p), c) for p, c in ordered if c >= self.thr],
            "n_suppressed_patterns": sum(1 for c in exclusive.values() if c < self.thr),
            "group_sizes": {name: self.S(len(pids)) for name, pids in held.items()},
        }
        return rows, upset

    def _modalities_and_overlap(self) -> None:
        rows = []
        by_mod: dict[str, list[TableResult]] = {}
        for t in self.ctx.tables:
            if t.is_dictionary or t.is_reference:
                by_mod.setdefault(self.modality[t.table_id]["modality"], []).append(t)
            elif t.table_id in self.excluded:
                by_mod.setdefault(f"(excluded) {self.excluded[t.table_id]}", []).append(t)
            else:
                for mod in self.table_mod_sets[t.table_id] or {self.modality[t.table_id]["modality"]: set()}:
                    by_mod.setdefault(mod, []).append(t)
        for mod, tables in sorted(by_mod.items()):
            pids = self.mod_sets.get(mod, set())
            rows.append({
                "modality": mod, "n_tables": len(tables),
                "n_tables_needing_review": sum(bool(self.modality[t.table_id]["needs_review"]) for t in tables),
                "n_participants": self.S(len(pids)) if mod in self.mod_sets else "",
                "table_ids": "; ".join(sorted(t.table_id for t in tables)),
                "table_names": "; ".join(sorted({t.base_name for t in tables})),
            })
        self._frame("modality_inventory.csv", rows, [
            "modality", "n_tables", "n_tables_needing_review", "n_participants", "table_ids", "table_names"])

        any_groups = self._groups()
        window_events = list(dict.fromkeys(self.ov.screening_events + self.ov.baseline_events))
        window_name = "baseline window (" + " or ".join(window_events) + ")"
        window_groups = self._groups(window_events)
        kept = [t for t in self.data if t.table_id not in self.excluded]
        everyone = set().union(*[set(t.participants.tolist()) for t in kept]) if kept else set()

        rows, upset = self._overlap_block(
            "all participants in non-excluded source tables", "ALL", "any visit", everyone, any_groups, True)
        upset["title"] = "Participants by exact combination of modality groups (all non-excluded tables, any visit)"
        self.out.upset = upset
        for universe in ("participant_status", "curated_bl"):
            if self.universes[universe] is None:
                continue
            for cohort in ["ALL"] + self.cohort_names(universe):
                members = self.members(universe, cohort)
                block, _ = self._overlap_block(universe, cohort, "any visit", members, any_groups, cohort == "ALL")
                rows += block
                if universe != "curated_bl":
                    continue
                block, _ = self._overlap_block(
                    universe, cohort, window_name, members, window_groups, cohort == "ALL")
                rows += block
        self._frame("modality_overlap.csv", rows, [
            "universe", "cohort", "window", "kind", "combination", "n_modalities", "n_participants",
            "n_in_universe", "pct_of_universe"])
        self._overlap_groups, self._everyone = any_groups, everyone
        self._window_name = window_name

    def _participant_counts(self) -> None:
        rows = [{
            "scope": "all source tables", "table_id": "", "table_name": "", "cohort_column": "",
            "cohort_value": "", "n_participants": self.S(len(self._everyone)), "is_trusted_cohort_source": "",
        }]
        for t in self.data:
            rows.append({
                "scope": "table", "table_id": t.table_id, "table_name": t.table_name, "cohort_column": "",
                "cohort_value": "", "n_participants": self.S(len(t.participants)),
                "is_trusted_cohort_source": "",
            })
            for col, sets in t.cohorts.items():
                trusted = self.cohort_source is not None and self.cohort_source[0] is t and self.cohort_source[1] == col
                if sets is None:
                    continue
                merged: dict[str, set] = {}
                for value, pids in sets.items():
                    merged.setdefault(self.cohort_label(col, value), set()).update(pids)
                for label, pids in sorted(merged.items()):
                    rows.append({
                        "scope": "table x cohort value", "table_id": t.table_id, "table_name": t.table_name,
                        "cohort_column": col, "cohort_value": label, "n_participants": self.S(len(pids)),
                        "is_trusted_cohort_source": trusted,
                    })
        self._frame("participant_count_inventory.csv", rows, [
            "scope", "table_id", "table_name", "cohort_column", "cohort_value", "n_participants",
            "is_trusted_cohort_source"])

    # --------------------------------------------------------- missingness
    def _by_cohort_rows(self, level: str, item: str, available: set) -> list[dict]:
        labels = sorted(set(self.cohort_of.values()))
        table = np.zeros((len(labels), 2))
        rows = []
        if not hasattr(self, "_cohort_members"):
            self._cohort_members: dict[str, set] = {}
            for p, lab in self.cohort_of.items():
                self._cohort_members.setdefault(lab, set()).add(p)
        for i, label in enumerate(labels):
            members = self._cohort_members[label]
            have = len(members & available)
            table[i] = [have, len(members) - have]
            rows.append({
                "level": level, "item": item, "cohort": label, "n_participants_in_cohort": self.S(len(members)),
                "n_with_data": self.part_of(have, len(members)),
                "pct_without_data": self.P(len(members) - have, len(members)),
            })
        v = cramers_v(table) if len(labels) >= 2 else ""
        for row in rows:
            row["cramers_v"] = v
            row["availability_strongly_associated_with_cohort"] = v != "" and v >= _STRONG_ASSOCIATION
        return rows

    def _missingness(self) -> None:
        rows = []
        for t in self.ctx.tables:
            pcts = self._missing_pcts(t)
            rows.append({
                "level": "table", "table_id": t.table_id, "item": t.table_name, "event_code": "",
                "n_columns": len(t.columns), "n_empty_columns": sum(p >= 100 for p in pcts),
                "n_columns_over_half_missing": sum(p > 50 for p in pcts),
                "pct_median_column_missing": round(float(np.median(pcts)), 1) if pcts else "",
                "n_participants_with_data": "", "n_participants_expected": "", "pct_participants_missing": "",
            })
        total = len(self._everyone)
        for name, pids in self._overlap_groups.items():
            rows.append({
                "level": "modality group", "table_id": "", "item": name, "event_code": "", "n_columns": "",
                "n_empty_columns": "", "n_columns_over_half_missing": "", "pct_median_column_missing": "",
                "n_participants_with_data": self.S(len(pids)), "n_participants_expected": self.S(total),
                "pct_participants_missing": self.P(total - len(pids), total),
            })
        for t in self.data:
            if not t.roles.visit or not t.candidates:
                continue
            ev_all, _ = unpack(t.visits[t.roles.visit]["pairs"])
            expected = dict(zip(*[a.tolist() for a in np.unique(ev_all, return_counts=True)])) if len(ev_all) else {}
            for col, cand in t.candidates.items():
                ev, _ = unpack(cand["pairs"])
                have = dict(zip(*[a.tolist() for a in np.unique(ev, return_counts=True)])) if len(ev) else {}
                for code, n_expected in expected.items():
                    rows.append({
                        "level": "candidate field by event", "table_id": t.table_id, "item": col,
                        "event_code": self.ev_label(code), "n_columns": "", "n_empty_columns": "",
                        "n_columns_over_half_missing": "", "pct_median_column_missing": "",
                        "n_participants_with_data": self.part_of(have.get(code, 0), n_expected),
                        "n_participants_expected": self.S(n_expected),
                        "pct_participants_missing": self.P(n_expected - have.get(code, 0), n_expected),
                    })
        self._frame("missingness_summary.csv", rows, [
            "level", "table_id", "item", "event_code", "n_columns", "n_empty_columns",
            "n_columns_over_half_missing", "pct_median_column_missing", "n_participants_with_data",
            "n_participants_expected", "pct_participants_missing"], ["level", "table_id", "item", "event_code"])

        rows = []
        if self.cohort_of:
            for name, pids in self._overlap_groups.items():
                rows.extend(self._by_cohort_rows("modality group", name, pids))
            for target, concept in sorted(self.concept_pairs):
                rows.extend(self._by_cohort_rows("candidate concept", f"{target}: {concept}",
                                                 self.concept_set(target, concept)))
            for t in self.data:
                rows.extend(self._by_cohort_rows("table", f"{t.table_id} {t.table_name}",
                                                 set(t.participants.tolist())))
        self._frame("missingness_by_cohort.csv", rows, [
            "level", "item", "cohort", "n_participants_in_cohort", "n_with_data", "pct_without_data",
            "cramers_v", "availability_strongly_associated_with_cohort"])

    def _interim(self) -> None:
        ids = self.ctx.pids.values
        everyone = sorted(self._everyone)
        frame = pd.DataFrame({"participant_id": [ids[p] for p in everyone]})
        for name, pids in self._overlap_groups.items():
            frame[f"has_{classify.norm(name).lower()}"] = [p in pids for p in everyone]
        frame["cohort"] = [self.cohort_of.get(p, "") for p in everyone]
        for name, pids in self.universes.items():
            frame[f"in_{name}"] = [pids is not None and p in pids for p in everyone]
        frame["n_source_tables"] = 0
        counts: dict[int, int] = {}
        for t in self.data:
            for p in t.participants.tolist():
                counts[p] = counts.get(p, 0) + 1
        frame["n_source_tables"] = [counts.get(p, 0) for p in everyone]
        self.out.interim = frame.sort_values("participant_id", kind="mergesort").reset_index(drop=True)

    # ------------------------------------------------------------ markdown
    def _reference_md(self) -> str:
        lines = ["# Reference-only derived dataset audit", "",
                 "These files are earlier exploratory merges. They are **reference only** and must not be "
                 "used as the modelling dataset; the analytic dataset will be rebuilt from source tables.", ""]
        if not self.refs:
            return "\n".join(lines + ["No reference dataset matching the configured patterns was found.", ""])
        column_sources: dict[str, set] = {}
        for t in self.data:
            for col in t.columns:
                column_sources.setdefault(classify.norm(col), set()).add(t.base_name)
        for t in self.refs:
            lines += [f"## {q(t.table_name)} ({t.table_id})", "",
                      f"- Dimensions: {self.S(t.n_rows)} rows x {len(t.columns)} columns",
                      f"- Unique participants: {self.S(len(t.participants))}",
                      f"- Likely key fields: {', '.join(q(c) for c in t.roles.pid_cols + t.roles.visit_cols) or 'none found'}",
                      f"- Granularity as found: {t.granularity}", ""]
            lines += ["### Duplicate-key statistics", "", md_table(
                ["Candidate key", "Columns", "Unique", "Duplicate rows"],
                [[k["label"], " + ".join(q(c) for c in k["columns"]), k["is_unique"], self.S(k["duplicate_rows"])]
                 for k in t.keys])]
            rows = []
            for col in t.columns:
                st = t.cols[col]
                sources = sorted(column_sources.get(classify.norm(col), set()))
                key = classify.norm(col)
                stripped = re.sub(r"_[XY]$", "", key)
                if not sources and stripped != key:
                    sources = sorted(column_sources.get(stripped, set()))
                suspicious = bool(classify.SUSPICIOUS_DERIVED_RE.search(key)) or not sources
                rows.append([q(col), st.dtype, self.P(st.n_blank, t.n_rows), len(sources),
                             ", ".join(q(s) for s in sources[:4]) + (" ..." if len(sources) > 4 else ""),
                             "yes" if suspicious else ""])
            lines += ["### Columns, missingness and source matches", "",
                      "A column is flagged when its name looks like a target, score, merge artefact "
                      "(`_x`/`_y`) or when no source table has a column of that name.", "",
                      md_table(["Column", "Type", "% missing", "Source tables with this column",
                                "Examples", "Suspicious / derived"], rows)]
            for col, info in t.visits.items():
                if info["rows"] is None:
                    lines += [f"Visit column {q(col)}: too many distinct values to be event codes.", ""]
                    continue
                merged: dict[str, int] = {}
                for value, count in info["rows"].items():
                    merged[printable(value)] = merged.get(printable(value), 0) + count
                lines += [f"### Apparent visit codes in {q(col)}", "", md_table(
                    ["Code", "Class", "Rows"],
                    [[q(code), classify.classify_event(code, self.decoder.decode(col, code))[0], self.S(n)]
                     for code, n in sorted(merged.items())])]
        return "\n".join(lines) + "\n"

    def _n(self, pids: set) -> str:
        """Count inside each analytic universe, as ``Participant_Status / curated baseline``."""
        cells = []
        for name in ("participant_status", "curated_bl"):
            universe = self.universes[name]
            cells.append("n/a" if universe is None else str(self.S(len(pids & universe))))
        return " / ".join(cells)

    def _feasibility_md(self) -> str:
        cs = self.concept_set
        cohort_members = set(self.cohort_of)
        lines = [
            "# Preliminary target feasibility", "",
            "No thresholds were applied and no target columns were created. Every count is the number of "
            "participants with at least one non-missing value in a field whose **name** matches the concept; "
            f"counts below {self.thr} are shown as `<{self.thr}`. Name matches are not proof of usability.", "",
            "Counts are given as **in Participant_Status / in the curated baseline universe**. Excluded tables, "
            "diagnosis tables and configured false matches do not contribute.", "",
            "## Analytic universes", "",
            md_table(["Universe", "Source table", "Cohort", "Participants"],
                     [[r.universe, q(r.source_table) if r.source_table else "", r.cohort, r.n_participants]
                      for r in self.out.frames["analytic_universe.csv"].itertuples()]),
        ]
        # ---- reference groups
        lines += ["## Reference groups", ""]
        if self.cohort_source:
            t, col = self.cohort_source
            counts: dict[str, int] = {}
            for label in self.cohort_of.values():
                counts[label] = counts.get(label, 0) + 1
            lines += [f"Cohort taken from {q(t.table_name)} column {q(col)} (candidate source; confirm before use). "
                      f"Participants with conflicting values: {self.S(self.cohort_conflicts)}.", "",
                      md_table(["Cohort value", "Participants"], [[q(k), self.S(v)] for k, v in sorted(counts.items())])]
            text = " ".join(counts).lower()
            flags = {"Parkinson's disease": r"parkinson|\bpd\b", "Healthy control": r"healthy|control|\bhc\b",
                     "Prodromal": r"prodromal", "SWEDD": r"swedd"}
            lines += ["Group labels recognised among the cohort values:", ""]
            lines += [f"- {name}: {'yes' if re.search(pattern, text) else 'not recognised'}"
                      for name, pattern in flags.items()] + [""]
        else:
            lines += ["No participant-level enrolment table with a cohort column was identified. "
                      "A cohort source must be chosen manually.", ""]
        # ---- PD-type
        dat, updrs = cs("PD-type", "DAT-SPECT"), cs("PD-type", "MDS-UPDRS")
        saa, prod = cs("PD-type", "alpha-synuclein SAA"), cs("PD-type", "prodromal indicator")
        rows = [["Trusted cohort value available", self._n(cohort_members)],
                ["DAT-SPECT candidate value", self._n(dat)], ["MDS-UPDRS candidate value", self._n(updrs)],
                ["alpha-synuclein SAA candidate value", self._n(saa)],
                ["Prodromal indicator candidate value", self._n(prod)],
                ["Cohort + MDS-UPDRS", self._n(cohort_members & updrs)],
                ["Cohort + DAT-SPECT", self._n(cohort_members & dat)],
                ["Cohort + MDS-UPDRS + DAT-SPECT (potentially eligible for target construction)",
                 self._n(cohort_members & updrs & dat)],
                ["Cohort + MDS-UPDRS + DAT-SPECT + SAA", self._n(cohort_members & updrs & dat & saa)]]
        lines += ["## PD-type", "", md_table(["Requirement", "Participants"], rows)]
        # ---- AD-like
        a42 = cs("AD-like", "Abeta42")
        p181, p_any = cs("AD-like", "pTau181"), cs("AD-like", "pTau (isoform not stated)")
        ptau = p181 | p_any
        ttau, apoe = cs("AD-like", "total tau"), cs("AD-like", "APOE") | cs("Genetics", "APOE")
        cog = cs("AD-like", "MoCA") | cs("AD-like", "neuropsychological test")
        same_visit = np.intersect1d(
            self.concept_visit_pairs("AD-like", "Abeta42"),
            self.concept_visit_pairs("AD-like", "pTau181", "pTau (isoform not stated)"))
        same_visit_pids = set(unpack(same_visit)[1].tolist())
        rows = [["Abeta42", self._n(a42)], ["pTau181 (named as such)", self._n(p181)],
                ["pTau with isoform not stated in the test name", self._n(p_any)],
                ["total tau", self._n(ttau)], ["pTau217", self._n(cs("AD-like", "pTau217"))],
                ["NfL", self._n(cs("AD-like", "NfL"))],
                ["Abeta42 + pTau (181 or unstated), any visit", self._n(a42 & ptau)],
                ["Abeta42 + pTau at the same visit code", self._n(same_visit_pids)],
                ["Abeta42 + pTau + cognition", self._n(a42 & ptau & cog)],
                ["Abeta42 + pTau + APOE", self._n(a42 & ptau & apoe)],
                ["Abeta42 + pTau + cognition + APOE", self._n(a42 & ptau & cog & apoe)]]
        lines += ["## AD-like", "", md_table(["Requirement", "Participants"], rows)]
        assay = self.out.frames["biomarker_assay_inventory.csv"]
        ad = assay[assay["concept"].str.contains("AD-like")] if len(assay) else assay
        lines += ["### Assay / version compatibility", "",
                  "Each row is one test name x sample matrix x unit x assay x source table. More than one row "
                  "for a concept means a harmonisation decision is required before values are combined.", "",
                  md_table(["Concept", "Table", "Status", "Test", "Matrix", "Units", "Assay", "Participants"],
                           [[r.concept, q(r.table_name), r.version_status, q(r.test_name), q(r.sample_matrix),
                             q(r.units), q(r.assay), r.n_participants] for r in ad.itertuples()], limit=40)]
        # ---- vascular
        cand = self.out.frames["candidate_feature_inventory.csv"]
        vasc = cand[(cand["target"] == "Vascular-risk") & (cand["status"] == "candidate")] if len(cand) else cand
        concepts = sorted({c for (target, c) in self.concept_pairs if target == "Vascular-risk"})
        rows, per_pid = [], {}
        for concept in concepts:
            pids = cs("Vascular-risk", concept)
            for p in pids:
                per_pid[p] = per_pid.get(p, 0) + 1
            fields = vasc[vasc["concept"] == concept]
            shown = sorted(set(fields["test_name"].where(fields["test_name"] != "", fields["field"])))
            rows.append([concept, len(fields), ", ".join(q(f) for f in shown[:6]),
                         self._n(pids)])
        lines += ["## Vascular-risk", "", "### Structured fields", "",
                  md_table(["Concept", "Fields", "Field or test names (first six)", "Participants"], rows),
                  "Coding of each low-cardinality field is listed in `column_value_inventory.csv`.", "",
                  md_table(["Coverage", "Participants"], [
                      ["At least 1 vascular concept with data", self.S(sum(1 for v in per_pid.values() if v >= 1))],
                      ["At least 2 vascular concepts with data", self.S(sum(1 for v in per_pid.values() if v >= 2))],
                      ["At least 3 vascular concepts with data", self.S(sum(1 for v in per_pid.values() if v >= 3))]])]
        wmh = cs("Vascular-risk", "WMH / vascular MRI")
        lines += [f"WMH or other vascular MRI indicators: {self._n(wmh)} participants with a matching field"
                  + (" (none found)." if not wmh else "."), ""]
        kw = self.out.frames["text_keyword_inventory.csv"]
        lines += ["### Free-text keyword matches (medical history and medication tables)", "",
                  md_table(["Keyword group", "Table", "Column", "Records", "Participants"],
                           [[r.keyword_group, q(r.table_name), q(r.column), r.n_records, r.n_participants]
                            for r in kw.itertuples()]),
                  "Blood pressure, weight/BMI and medication matches are possible **proxies** for the vascular "
                  "target and must be handled in the leakage matrix. No vascular score was defined.", ""]
        lines += self._baseline_md()
        return "\n".join(lines) + "\n"

    def _summary_md(self) -> str:
        f = self.out.frames
        thr = self.thr
        lines = ["# PPMI dataset audit summary", "",
                 f"Aggregate, privacy-safe output. Counts below {thr} are shown as `<{thr}`; no participant "
                 "identifiers, rows, dates or free text are included. Source tables were **not** merged. "
                 "Classifications are naming rules and need manual confirmation.", ""]

        def section(number: int, title: str) -> None:
            lines.extend([f"## {number}. {title}", ""])

        lines += ["## Analytic universe and exclusions", "",
                  md_table(["Universe", "Source table", "Cohort", "Participants"],
                           [[r.universe, q(r.source_table) if r.source_table else "", r.cohort, r.n_participants]
                            for r in f["analytic_universe.csv"].itertuples()]),
                  f"{len(self.excluded)} tables are excluded from modality counts and candidate concepts "
                  f"(remote-only, adverse-event and pregnancy tables) and {len(self.leakage)} diagnosis tables are "
                  "marked as leakage, never a feature. See `excluded_from_modalities` and `leakage_table` in "
                  "`table_inventory.csv`, and `configs/domain_overrides.yaml`.", ""]

        from . import phase15

        lines += phase15.summary_md(self)

        section(1, "Which archives/releases were found?")
        lines.append(md_table(["Source", "Kind", "Status", "Size (bytes)", "Modified (UTC)", "Members", "Tabular", "Imaging"],
                              [[q(r.source), r.kind, r.status, r.size_bytes, r.modified_utc, r.n_members, r.n_tabular, r.n_imaging]
                               for r in f["archive_inventory.csv"].itertuples()]))
        section(2, "Which appear duplicated or versioned?")
        dup = f["duplicate_version_inventory.csv"]
        if len(dup):
            grouped = dup.groupby(["group_type", "group"], sort=True)
            rows = []
            for (kind, group), g in grouped:
                pref = g[g["candidate_preferred_version"] == True]  # noqa: E712
                rows.append([kind, q(group), len(g), g["relation"].iloc[0],
                             q(pref["member_path"].iloc[0]) + " in " + q(pref["source"].iloc[0]) if len(pref) else "none",
                             g["preference_reason"].iloc[0]])
            lines.append(md_table(["Type", "Group", "Copies", "Relation", "Candidate preferred version", "Reason"], rows, limit=60))
        else:
            lines.append("No table name occurs more than once.\n")
        lines.append("Nothing was merged or discarded. Every row above needs a manual decision.\n")

        section(3, "Which source tables exist?")
        tab = f["table_inventory.csv"]
        lines.append(f"{len(self.data)} source tables, {len(self.dicts)} dictionary tables and {len(self.refs)} "
                     "reference-only derived file(s) were profiled. Full list: `table_inventory.csv`.\n")
        lines.append(md_table(["ID", "Table", "Source", "Rows", "Cols", "Participants", "Modality", "Review"],
                              [[r.table_id, q(r.table_name), q(r.source), r.n_rows, r.n_columns, r.n_participants,
                                r.modality, "yes" if r.needs_review else ""] for r in tab.itertuples()], limit=200))
        section(4, "What is each table's granularity?")
        lines.append(md_table(["Granularity", "Tables"], [[k, v] for k, v in sorted(tab["granularity"].value_counts().items())]))
        lines.append("Per-table granularity is in `table_inventory.csv`. Tables of different granularity must not be outer-joined.\n")

        section(5, "Which join keys appear safe/unsafe?")
        keys = f["table_granularity_inventory.csv"]
        unsafe = tab[(tab["recommended_key"] == "") & (~tab["is_dictionary"])]
        lines.append(f"{int((tab['recommended_key'] != '').sum())} tables have a candidate key that is unique; "
                     f"{len(unsafe)} have **no unique candidate key** and are unsafe to join as they are:\n")
        lines.append(md_table(["ID", "Table", "Granularity", "Keys tested"],
                              [[r.table_id, q(r.table_name), r.granularity,
                                "; ".join(keys[keys["table_id"] == r.table_id]["candidate_key"])] for r in unsafe.itertuples()], limit=80))
        section(6, "Which visit/event codes exist?")
        ev = f["event_code_inventory.csv"]
        if len(ev):
            rows = []
            for code, g in ev.groupby("event_code", sort=True):
                rows.append([q(code), "; ".join(sorted(set(g["event_class"]))), "; ".join(sorted(set(g["decode"]) - {""}))[:60],
                             g["table_id"].nunique()])
            lines.append(md_table(["Code", "Class", "Dictionary decode", "Tables"], rows, limit=120))
        else:
            lines.append("No visit/event column was found.\n")
        lines.append("Screening, baseline and `V00`-style codes are reported separately and were **not** combined. "
                     "Classes come from PPMI naming conventions and any dictionary table in the download; "
                     "the Data User Guide PDFs were not read by this run.\n")

        section(7, "Which modalities are genuinely available?")
        lines.append(md_table(["Modality", "Tables", "Needing review", "Participants"],
                              [[r.modality, r.n_tables, r.n_tables_needing_review, r.n_participants]
                               for r in f["modality_inventory.csv"].itertuples()]))
        lines.append("A participant counts towards a modality when they have at least one row in one of its "
                     "tables (or one test of that sample matrix); that is weaker than having usable values.\n")
        section(8, "What participant overlap exists among modalities?")
        ov = f["modality_overlap.csv"]
        keep = ov[ov["kind"].isin(["single modality", "requested combination", "all eight modality groups"])
                  & (ov["cohort"] == "ALL")
                  & ((ov["universe"] == "participant_status")
                     | ((ov["universe"] == "curated_bl") & (ov["window"] != "any visit")))]
        lines.append(md_table(["Universe", "Window", "Kind", "Combination", "Participants", "% of universe"],
                              [[r.universe, r.window, r.kind, r.combination, r.n_participants, r.pct_of_universe]
                               for r in keep.itertuples()]))
        lines.append("Per-cohort rows, the any-visit view of the baseline universe, pairwise and exclusive "
                     "patterns are in `modality_overlap.csv`.\n")
        lines.append(f"All participants seen in non-excluded source tables: {self.S(len(self._everyone))}. "
                     "Pairwise and exclusive patterns are in `modality_overlap.csv`; see "
                     "`participant_count_inventory.csv` for which tables and cohort values account for the total.\n")

        cand = f["candidate_feature_inventory.csv"]
        for number, target, title in ((9, "PD-type", "Which candidate variables support PD-type?"),
                                      (10, "AD-like", "Which support AD-like?"),
                                      (11, "Vascular-risk", "Which support vascular-risk?")):
            section(number, title)
            sub = cand[(cand["target"] == target) & (cand["status"] == "candidate")] if len(cand) else cand
            rows = []
            for concept, g in sub.groupby("concept", sort=True):
                names = sorted(set(g["test_name"].where(g["test_name"] != "", g["field"])))
                rows.append([concept, len(g), g["table_id"].nunique(),
                             ", ".join(q(n) for n in names[:6]) + (" ..." if len(names) > 6 else "")])
            lines.append(md_table(["Concept", "Fields/tests", "Tables", "Examples"], rows))
        gen = cand[(cand["target"] == "Genetics") & (cand["status"] == "candidate")] if len(cand) else cand
        lines.append("Genetics candidates: " + (", ".join(
            f"{c} ({len(g)})" for c, g in gen.groupby("concept", sort=True)) or "none found") + ".\n")
        lines.append("Details and participant coverage: `candidate_feature_inventory.csv` and "
                     "`target_feasibility_summary.md`.\n")

        section(12, "Which biomarkers are long-format?")
        longs = [t for t in self.data if t.long is not None]
        lines.append(md_table(["ID", "Table", "Status", "Test column", "Value column", "Distinct test/matrix/unit/assay rows"],
                              [[t.table_id, q(t.table_name), t.status, q(t.roles.test_col), q(t.roles.value_col),
                                len(t.long.combos)] for t in longs]))
        section(13, "Which assay/version issues remain?")
        assay = f["biomarker_assay_inventory.csv"]
        multi = assay[assay["harmonisation_review_needed"] == True] if len(assay) else assay  # noqa: E712
        rows = [[concept, len(g), g["table_name"].nunique(), ", ".join(q(u) for u in sorted(set(g["units"]))[:5])]
                for concept, g in multi.groupby("concept", sort=True)]
        lines.append(md_table(["Concept", "Assay variants", "Tables", "Units seen"], rows))
        statuses = sorted({t.status for t in longs})
        lines.append(f"Long-format table statuses present: {', '.join(statuses) or 'none'}. "
                     "Current, Pilot and Deprecated results must not be pooled without a decision.\n")

        section(14, "Which special/censored values occur?")
        sp = f["biomarker_special_values.csv"]
        if len(sp):
            rows = [[cls, len(g), g["table_id"].nunique(), ", ".join(q(tk) for tk in sorted(set(g["token"]))[:8])]
                    for cls, g in sp.groupby("token_class", sort=True)]
            lines.append(md_table(["Class", "Field/test entries", "Tables", "Example tokens"], rows))
        else:
            lines.append("None found.\n")
        lines.append("Blank cells are counted as missing separately from these tokens. No numeric encoding was chosen.\n")

        section(15, "What potential leakage risks are already visible?")
        risks = []
        cohort_tables = [t for t in self.data if t.roles.cohort_cols
                         and self.modality[t.table_id]["modality"] != "enrollment/cohort"]
        if cohort_tables:
            risks.append(f"Cohort/diagnosis columns are carried inside {len(cohort_tables)} non-enrolment tables "
                         f"(for example {', '.join(q(t.table_name) for t in cohort_tables[:4])}); they would leak the reference label.")
        mbc = f["missingness_by_cohort.csv"]
        strong = mbc[mbc["availability_strongly_associated_with_cohort"] == True] if len(mbc) else mbc  # noqa: E712
        if len(strong):
            items = sorted(set(strong[strong["level"] != "table"]["item"]))
            risks.append("Data availability is strongly associated with cohort (Cramér's V >= "
                         f"{_STRONG_ASSOCIATION}) for: {', '.join(items[:12]) or 'individual tables only'}. "
                         "Missingness indicators for these would leak diagnostic group.")
        for target, concept, why in (
            ("PD-type", "DAT-SPECT", "DAT-SPECT is part of how PD is diagnosed/enrolled"),
            ("PD-type", "enrolment subgroup flag", "enrolment flags encode recruitment route"),
            ("AD-like", "Abeta42", "CSF Abeta/tau would define the AD-like proxy and cannot also be its features"),
            ("Vascular-risk", "blood pressure", "blood pressure and vascular medications are proxies for the vascular proxy"),
        ):
            if self.concept_pairs.get((target, concept)):
                risks.append(f"{target}: {why}.")
        if any(k[0] == "Vascular-risk (free text)" and "medication" in k[1] or k[1] == "statin" for k in self.concept_pairs):
            risks.append("Medication records match antihypertensive/antidiabetic/statin keywords; treatment variables can leak the vascular target.")
        if self.refs:
            risks.append("The reference-only derived dataset contains columns flagged as derived or target-like; see `reference_dataset_audit.md`.")
        risks.append("Date, visit-code, site and update-stamp columns can encode enrolment era and cohort; review before use as features.")
        lines += [f"- {r}" for r in risks] + [""]

        section(16, "What data-quality/version problems require manual decisions?")
        problems = []
        if len(dup):
            problems.append(f"{dup['group'].nunique()} duplicated or versioned table groups need an authoritative version.")
        if len(unsafe):
            problems.append(f"{len(unsafe)} tables have no unique candidate key.")
        review = tab[tab["needs_review"] == True]  # noqa: E712
        if len(review):
            problems.append(f"{len(review)} tables have an uncertain modality (`needs_review`).")
        unknown_events = ev[ev["event_class"] == "unknown"]["event_code"].nunique() if len(ev) else 0
        if unknown_events:
            problems.append(f"{unknown_events} event codes could not be classified.")
        skipped = [s for s in self.ctx.sources if s.status != "audited"]
        if skipped:
            problems.append("Sources not audited: " + ", ".join(f"{q(s.source)} ({s.status})" for s in skipped) + ".")
        limited = tab[tab["row_limit_applied"] == True]  # noqa: E712
        if len(limited):
            problems.append(f"{len(limited)} tables were only partly read because of the row limit; their counts are lower bounds.")
        noted = tab[tab["parse_note"] != ""]
        if len(noted):
            problems.append(f"{len(noted)} tables had malformed lines that were skipped: " + ", ".join(q(n) for n in noted["table_name"][:8]) + ".")
        if self.cohort_conflicts:
            problems.append(f"{self.S(self.cohort_conflicts)} participants have conflicting values in the cohort source.")
        lines += [f"- {p}" for p in problems] or ["- None detected automatically."]
        lines.append("")
        lines.append("### Tables or files that could not be audited\n")
        lines.append(md_table(["Source", "Member", "Stage", "Error type", "Location"],
                              [[q(e["source"]), q(e["member"]), e["stage"], e["exception_type"], e["location"]]
                               for e in self.ctx.errors]))
        unsupported = f["archive_member_inventory.csv"]
        unsupported = unsupported[unsupported["file_type"].isin(["tabular_unsupported", "archive_unsupported"])]
        if len(unsupported):
            lines.append("Unsupported files (listed, not read): " + ", ".join(q(e) for e in unsupported["entry"][:20]) + ".\n")

        section(17, "What must be decided before Phase 2?")
        lines += [
            "1. Authoritative version of every duplicated/versioned table, and the role of Pilot/Deprecated results.",
            "2. The analytic cohort and the trusted cohort/diagnosis source.",
            "3. Baseline/index-visit rules, including how screening and baseline codes relate.",
            "4. PD-type, AD-like and vascular-risk proxy definitions, with positive/negative/masked rules.",
            "5. Handling of censored and special assay values, and assay harmonisation.",
            "6. The leakage matrix and per-target allowed feature sets.",
            "7. Final usable modalities given the overlap above.",
            "8. Participant-level split strategy.",
            "9. A reproducible merge specification that respects each table's granularity and key.", "",
        ]
        return "\n".join(lines) + "\n"

    # ------------------------------------------------- v1.1 targeted audits
    def _baseline_month(self) -> dict[int, float]:
        """Month index of each participant's baseline visit, from the curated data cut."""
        cur = self.curated
        if cur is None or cur.captured is None:
            return {}
        column = find_column(cur.captured, self.ov.universe.get("baseline_date_column"))
        if column is None:
            return {}
        cap = cur.captured
        cap = cap[(cap["_pid"] >= 0) & cap["_event"].isin(self.ov.baseline_events)]
        return month_index(cap[column]).groupby(cap["_pid"]).min().dropna().to_dict()

    def _evidence_rows(self, source: str, table: TableResult, concept: str, frame: pd.DataFrame,
                       baseline: dict[int, float]) -> list[dict]:
        """Per-universe, per-cohort participant counts for one piece of vascular evidence."""
        anytime = set(frame["_pid"].tolist())
        before = set(frame.loc[frame["_when"] <= frame["_pid"].map(baseline), "_pid"].tolist())
        self.vascular_sets[(source, concept)] = (before, table)
        rows = []
        for universe in ("participant_status", "curated_bl"):
            if self.universes[universe] is None:
                continue
            timings = [("any time", anytime)]
            if universe == "curated_bl":
                timings.append(("at or before baseline", before))
            for cohort in ["ALL"] + self.cohort_names(universe):
                members = self.members(universe, cohort)
                for timing, pids in timings:
                    n = len(pids & members)
                    rows.append({
                        "source": source, "table_name": table.table_name, "concept": concept,
                        "universe": universe, "cohort": cohort, "timing": timing,
                        "n_participants": self.part_of(n, len(members)),
                        "n_in_cohort": self.S(len(members)), "pct_of_cohort": self.P(n, len(members)),
                    })
        return rows

    def _vascular_concepts(self) -> None:
        """Vascular concepts per cohort, at/before baseline and at any time. Aggregates only."""
        rows: list[dict] = []
        baseline = self._baseline_month()
        self.n_with_baseline_date = len(baseline)

        cfg = self.ov.section("medical_conditions")
        table = self.pick(_as_list(cfg.get("table")))
        self.medical_table, self.medical_text_columns = table, []
        if table is not None and table.captured is not None:
            cap = table.captured[table.captured["_pid"] >= 0].copy()
            when = pd.Series(np.nan, index=cap.index, dtype="float64")
            used = []
            for name in _as_list(cfg.get("date_columns")) + _as_list(cfg.get("year_columns")):
                column = find_column(cap, name)
                if column:
                    when = when.fillna(month_index(cap[column]))
                    used.append(column)
            cap["_when"] = when
            category = find_column(cap, cfg.get("category_column"))
            if category:
                used.append(category)
                codes = cap[category].astype(str).str.replace(r"\.0+$", "", regex=True)
                for code, concept in (cfg.get("category_concepts") or {}).items():
                    rows += self._evidence_rows("Medical_Conditions_Log category code", table,
                                                f"{concept} [{category}={code}]", cap[codes == str(code)], baseline)
                distinct = sorted(v for v in set(codes) if v and printable(v) == v)
                if len(distinct) <= 40:
                    for code in distinct:
                        label = self.decoder.decode(category, code)
                        rows += self._evidence_rows(
                            "Medical_Conditions_Log category (every code)", table,
                            f"{category}={code}" + (f" ({label})" if label else ""), cap[codes == code], baseline)
            # Only genuine text counts: form names, codes, years and dates are not condition terms.
            text_columns = [
                c for c in cap.columns
                if not c.startswith("_") and c not in used
                and table.cols[c].dtype in {"string", "mixed"} and table.roles.role_of(c) in {"", "free_text"}
            ]
            self.medical_text_columns = text_columns
            if text_columns:
                text = cap[text_columns].astype(str).agg(" | ".join, axis=1)
                for concept, patterns in classify.VASCULAR_CONCEPTS.items():
                    hit = text.str.contains(patterns["condition"], case=False, regex=True)
                    rows += self._evidence_rows("Medical_Conditions_Log condition text", table, concept,
                                                cap[hit.to_numpy()], baseline)

        cfg = self.ov.section("medications")
        table = self.pick(_as_list(cfg.get("table")))
        if table is not None and table.captured is not None:
            cap = table.captured[table.captured["_pid"] >= 0].copy()
            start = find_column(cap, cfg.get("start_date_column"))
            cap["_when"] = month_index(cap[start]) if start else np.nan
            text_columns = [c for c in (find_column(cap, n) for n in _as_list(cfg.get("text_columns"))) if c]
            if text_columns:
                text = cap[text_columns].astype(str).agg(" | ".join, axis=1)
                for concept, patterns in classify.VASCULAR_CONCEPTS.items():
                    hit = text.str.contains(patterns["condition"], case=False, regex=True)
                    rows += self._evidence_rows("Concomitant_Medication_Log indication text (condition keywords)",
                                                table, concept, cap[hit.to_numpy()], baseline)
                    if patterns["medication"]:
                        hit = text.str.contains(patterns["medication"], case=False, regex=True)
                        rows += self._evidence_rows("Concomitant_Medication_Log medication name (drug keywords)",
                                                    table, concept, cap[hit.to_numpy()], baseline)
        self._frame("vascular_concept_by_cohort.csv", rows, [
            "source", "table_name", "concept", "universe", "cohort", "timing", "n_participants",
            "n_in_cohort", "pct_of_cohort"])

    def _baseline_md(self) -> list[str]:
        frame = self.out.frames.get("bl_label_feasibility_by_cohort.csv", pd.DataFrame())
        lines = ["## Per-label feasibility at baseline, by cohort", "",
                 "Universe: participants with a baseline row in the curated data cut. Each cell is the number "
                 "of participants in the cohort who meet the requirement in the stated window. Still no "
                 "thresholds and no labels.", ""]
        if not len(frame):
            return lines + ["Not available: no curated baseline universe was found.", ""]
        cohorts = list(dict.fromkeys(frame["cohort"]))
        sizes = frame.drop_duplicates("cohort").set_index("cohort")["n_in_cohort"].to_dict()
        for label, part in frame.groupby("label", sort=True):
            cells: dict[tuple, dict] = {}
            for r in part.itertuples():
                cells.setdefault((r.requirement, r.window, r.source_table), {})[r.cohort] = r.n_participants
            lines += [f"### {label}", "", md_table(
                ["Requirement", "Window", "Source"] + [f"{c} (n = {sizes[c]})" for c in cohorts],
                [[req, window, q(source) if source else ""] + [got.get(c, "") for c in cohorts]
                 for (req, window, source), got in cells.items()])]
        if self.wmh_fields and self.wmh_table is not None:
            lines += ["White-matter hypointensity columns found in " + q(self.wmh_table.table_name) + ": "
                      + ", ".join(q(f) for f in self.wmh_fields) + ".", ""]
        return lines

    def _reference_tables(self) -> None:
        """Queue documentation tables for printing once they pass the identifier check."""
        seen = set()
        for t in self.ctx.tables:
            if t.is_reference or not self.ov.is_reference_table(*self.names(t)):
                continue
            key = (classify.norm(t.base_name), t.member.content_signature)
            file, coincidences = "", ""
            if key in seen:
                status = "not exported again: identical copy of a table already exported"
            elif t.roles.pid_cols:
                status = "not exported: the table has a participant-identifier column"
            elif t.captured is None:
                status = "not exported: more rows than the documentation-table limit, so it was not held in memory"
            else:
                frame = t.captured.drop(columns=["_pid", "_event"])
                kept, status, coincidences = vet_reference_table(frame, self.ctx.pids.values)
                if kept is not None:
                    file = re.sub(r"[^A-Za-z0-9_.-]+", "_", t.table_name).strip("_") + ".csv"
                    self.out.reference[file] = kept
                    seen.add(key)
            self.reference_rows.append({
                "table_id": t.table_id, "source": t.member.source, "table_name": t.table_name,
                "n_rows": self.S(t.n_rows), "n_columns": len(t.columns), "status": status,
                "reference_file": file, "n_numbers_equal_to_an_identifier_by_coincidence": coincidences,
            })

    def _medical_conditions_md(self) -> str:
        lines = ["# Medical_Conditions_Log audit", "",
                 f"Aggregates only; counts below {self.thr} are shown as `<{self.thr}`.", ""]
        table = getattr(self, "medical_table", None)
        if table is None:
            return "\n".join(lines + ["No table matching the configured Medical_Conditions_Log pattern was found.", ""])
        lines += [f"Table: {q(table.table_name)} ({table.table_id}), granularity {table.granularity}.", "",
                  "## Columns", "",
                  md_table(["Column", "Type", "Role", "% missing", "Distinct values", "Dictionary description"],
                           [[q(c), table.cols[c].dtype, table.roles.role_of(c), self.P(table.cols[c].n_blank, table.n_rows),
                             len(table.cols[c].distinct) if table.cols[c].distinct is not None else "many",
                             self.decoder.describe(c)] for c in table.columns])]
        values = self.out.frames["column_value_inventory.csv"]
        coded = values[values["table_id"] == table.table_id]
        lines += ["## Coded fields", "",
                  md_table(["Column", "Code", "Decode", "Rows"],
                           [[q(r.column), q(r.value), r.decode, r.n_rows] for r in coded.itertuples()])]
        if self.medical_text_columns:
            lines += ["Free-text columns searched in memory for vascular keywords (text is never written): "
                      + ", ".join(q(c) for c in self.medical_text_columns) + ".", ""]
        else:
            lines += ["**No condition-term or free-text column is present in this table.** Individual conditions "
                      "(hypertension, diabetes, hyperlipidaemia, cardiac disease, stroke/TIA) therefore cannot be "
                      "identified from it; only the category code is available. The concept counts below use the "
                      "category code, and the medication log as a separate, weaker source.", ""]
        frame = self.out.frames["vascular_concept_by_cohort.csv"]
        lines += [f"Participants with a baseline date available for timing: {self.S(self.n_with_baseline_date)}. "
                  "A record counts as at or before baseline when its diagnosis (or medication start) month is not "
                  "later than the baseline month; records with only a year count when the year is not later; "
                  "records without a date count under any time only.", ""]
        part = frame[(frame["universe"] == "curated_bl") & (~frame["source"].str.contains("every code"))] if len(frame) else frame
        if not len(part):
            return "\n".join(lines + ["No vascular evidence could be computed.", ""])
        cohorts = list(dict.fromkeys(part["cohort"]))
        sizes = part.drop_duplicates("cohort").set_index("cohort")["n_in_cohort"].to_dict()
        lines += ["## Vascular concepts by cohort (curated baseline universe)", ""]
        cells: dict[tuple, dict] = {}
        for r in part.itertuples():
            cells.setdefault((r.source, r.concept, r.timing), {})[r.cohort] = r.n_participants
        lines.append(md_table(
            ["Source", "Concept", "Timing"] + [f"{c} (n = {sizes[c]})" for c in cohorts],
            [[source, concept, timing] + [got.get(c, "") for c in cohorts]
             for (source, concept, timing), got in cells.items()]))
        lines += ["Every category code by cohort, and the Participant_Status universe, are in "
                  "`vascular_concept_by_cohort.csv`.", ""]
        return "\n".join(lines) + "\n"
