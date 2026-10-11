"""Privacy guards for audit reports.

Everything written under ``reports/`` must be aggregate only: small counts are
suppressed, and after a run the generated files are scanned for any
participant identifier that was seen while reading the source tables.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable

DEFAULT_THRESHOLD = 5
MIN_NUMERIC_ID_DIGITS = 4

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_BACKTICK_RE = re.compile(r"`([^`]*)`")
# Values the audit itself generates: numbers, suppression markers, ISO dates, versions.
_STRUCTURED_RE = re.compile(
    r"^(-?\d+(\.\d+)*|<\d+|\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?)$"
)
_TEXT_SUFFIXES = {".csv", ".md", ".json", ".txt"}

# Columns whose cells are a controlled vocabulary copied from the data (assay
# test names, units, censoring tokens). They legitimately contain numbers such
# as ">1700", so they are compared with identifiers cell by cell, not token by
# token.
VOCABULARY_COLUMNS = {"test_name", "units", "assay", "sample_matrix", "token"}


# Phase 3 report columns that hold only computed metrics (their decimals are not identifiers).
METRIC_COLUMNS = {"auroc", "auprc", "brier", "bss", "cal_slope", "cal_intercept", "ece", "f1", "precision", "recall",
                  "threshold", "hamming_loss", "macro_f1_all_eligible", "value", "seed", "rank", "bin", "best_rank"}


def suppress(n: int, threshold: int = DEFAULT_THRESHOLD) -> int | str:
    """Return ``n``, or ``"<threshold>"`` when ``0 < n < threshold``."""
    n = int(n)
    if 0 < n < threshold:
        return f"<{threshold}"
    return n


def safe_pct(num: int, den: int, threshold: int = DEFAULT_THRESHOLD) -> float | str:
    """Percentage of ``num`` in ``den``, withheld when it would reveal a small count.

    A percentage plus its denominator gives back the numerator, so the value is
    withheld when either the numerator or its complement is a small non-zero
    count.
    """
    num, den = int(num), int(den)
    if den <= 0:
        return ""
    if 0 < num < threshold or 0 < den - num < threshold:
        return "suppressed"
    return round(100.0 * num / den, 1)


def normalise_id(value: object) -> str:
    """Canonical text form of a participant identifier (``"3001.0"`` -> ``"3001"``)."""
    text = str(value).strip()
    return re.sub(r"\.0+$", "", text)


def is_generated_column(name: str) -> bool:
    """True for report columns that hold only audit-generated numbers or timestamps."""
    return (
        name.startswith(("n_", "pct_", "mean_", "median_", "sd_", "se_", "delta_", "ci_"))
        or name.endswith("_bytes")
        or name in {"position", "cramers_v", "modified", "modified_utc", "name_date"}
        or name in METRIC_COLUMNS
    )


def checkable_ids(ids: Iterable[str]) -> tuple[set[str], int]:
    """Identifiers the scan can test, and how many were too short to test.

    A purely numeric identifier with fewer than four digits cannot be told
    apart from an ordinary category code, so it is skipped and counted.
    """
    keep: set[str] = set()
    skipped = 0
    for raw in ids:
        value = normalise_id(raw)
        if not value:
            continue
        if value.isdigit() and len(value) < MIN_NUMERIC_ID_DIGITS:
            skipped += 1
        else:
            keep.add(value)
    return keep, skipped


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text))


def _json_strings(node: object) -> Iterable[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from _json_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _json_strings(value)
    elif isinstance(node, str):
        yield node


# An identifier written next to an identifier keyword, e.g. "PATNO 3001" or "subject ID: 3001".
_ID_CONTEXT_RE = re.compile(
    r"(?i)\b(?:patno|patnos|(?:participant|subject|patient)s?\s*(?:ids?|numbers?|nos?\.?|#)|ids?)"
    r"[^0-9A-Za-z]{0,4}(\d{4,})"
)


def reference_table_check(frame, ids: Iterable[str], skip_generated_columns: bool = False) -> tuple[str, int]:
    """Decide whether a documentation table may be printed.

    Returns ``(issue, n_coincidences)``: ``issue`` is empty when the table is
    safe, and ``n_coincidences`` counts numbers in it that merely happen to
    equal a participant identifier.

    Documentation legitimately contains numbers (project numbers, subject
    counts, thresholds), and with tens of thousands of identifiers some of
    them equal an identifier by chance. The table is therefore refused only
    when something *behaves like* an identifier:

    * a column header equals an identifier;
    * half or more of a column's distinct values (or three or more values
      making up over 20%) equal identifiers;
    * a text cell names an identifier next to an identifier keyword
      ("PATNO 3001", "subject ID: 3001");
    * a text cell contains three or more different identifiers.

    Four-digit years (1900-2100) are ignored. With ``skip_generated_columns``
    the audit's own count columns (``n_*``, ``pct_*``) are not tested.
    """
    wanted, _ = checkable_ids(ids)
    if not wanted:
        return "", 0
    if any(normalise_id(c) in wanted for c in frame.columns):
        return "a column header equals a participant identifier", 0
    coincidences = 0
    for position, column in enumerate(frame.columns, start=1):
        if skip_generated_columns and is_generated_column(str(column)):
            continue
        values = {normalise_id(v) for v in frame[column].astype(str)} - {""}
        if not values:
            continue
        hits = len(values & wanted)
        share = hits / len(values)
        if share >= 0.5 or (hits >= 3 and share > 0.2):
            return f"column {position} looks like a participant-identifier column", coincidences
        coincidences += hits
        for value in values:
            if _STRUCTURED_RE.match(value):
                continue
            if any(normalise_id(m.group(1)) in wanted for m in _ID_CONTEXT_RE.finditer(value)):
                return f"text in column {position} contains a participant identifier next to an identifier keyword", coincidences
            words = {w for w in _tokens(value) if not (len(w) == 4 and w.isdigit() and 1900 <= int(w) <= 2100)}
            found = words & wanted
            if len(found) >= 3:
                return f"a text cell in column {position} contains several participant identifiers", coincidences
            coincidences += len(found)
    return "", coincidences


def vet_reference_table(frame, ids: Iterable[str], skip_generated_columns: bool = False):
    """Return ``(frame_to_export_or_None, status, n_coincidences)`` for a documentation table.

    When the only problem is text that names an identifier, the offending rows
    are withheld and the rest is exported, with the number of withheld rows in
    the status. Any column-level problem refuses the whole table.
    """
    issue, coincidences = reference_table_check(frame, ids, skip_generated_columns)
    if not issue:
        return frame, "exported after identifier check", coincidences
    if "text" in issue:
        wanted, _ = checkable_ids(ids)

        def risky(value: object) -> bool:
            text = normalise_id(value)
            if not text or _STRUCTURED_RE.match(text):
                return False
            if any(normalise_id(m.group(1)) in wanted for m in _ID_CONTEXT_RE.finditer(text)):
                return True
            words = {w for w in _tokens(text) if not (len(w) == 4 and w.isdigit() and 1900 <= int(w) <= 2100)}
            return len(words & wanted) >= 3

        bad = frame.astype(str).map(risky).any(axis=1)
        kept = frame[~bad]
        second, coincidences = reference_table_check(kept, ids, skip_generated_columns)
        if len(kept) and not second:
            return kept, (f"exported after identifier check; {int(bad.sum())} row(s) withheld because their "
                          "text names a participant identifier"), coincidences
    return None, f"not exported: {issue}", coincidences


def reference_table_issue(frame, ids: Iterable[str]) -> str:
    """Why a documentation table must not be printed, or ``""`` when it is safe."""
    return reference_table_check(frame, ids)[0]


def scan_reports_for_ids(
    root: Path, ids: Iterable[str], exclude_dirs: tuple[Path, ...] = ()
) -> list[dict[str, object]]:
    """Scan every text report under ``root`` for participant identifiers.

    PPMI identifiers are plain integers, so a count in a report can equal an
    identifier by coincidence. To keep the check meaningful the scan looks at
    every place where a string taken from the data can end up:

    * CSV: the header and every cell. Audit-generated numbers and timestamps
      are skipped in generated columns (see :func:`is_generated_column`), and
      vocabulary columns are compared cell by cell;
    * Markdown: every backtick span (all data-derived names are written in
      backticks, counts never are);
    * JSON: every key and string value that is not a number, date or version.

    Identifiers containing a letter are additionally searched for in the whole
    text of every file. Findings never contain the identifier itself.

    ``exclude_dirs`` are skipped: the printed documentation tables under
    ``reference/`` hold counts and project numbers as plain cells and are
    verified column by column with :func:`reference_table_issue` instead.
    """
    wanted, _ = checkable_ids(ids)
    simple = {v for v in wanted if _TOKEN_RE.fullmatch(v)}
    compound = wanted - simple
    lettered = {v for v in simple if not v.isdigit()}
    findings: list[dict[str, object]] = []

    def record(hits: int, file: Path, where: str) -> None:
        if hits:
            findings.append({"file": file.name, "location": where, "n_matches": hits})

    def token_hits(text: str) -> int:
        return len(_tokens(text) & simple) + sum(1 for c in compound if c in text)

    skipped = [Path(d).resolve() for d in exclude_dirs]
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        suffix = path.suffix.lower()
        if suffix not in _TEXT_SUFFIXES:
            continue
        if any(d in path.resolve().parents for d in skipped):
            continue  # checked separately, see reference_table_issue
        text = path.read_text(encoding="utf-8", errors="replace")
        record(len(_tokens(text) & lettered) + sum(1 for c in compound if c in text), path, "whole file")
        if suffix == ".csv":
            rows = list(csv.reader(text.splitlines()))
            if not rows:
                continue
            header = rows[0]
            record(token_hits(" ".join(header)), path, "header")
            for idx, name in enumerate(header):
                cells = [r[idx].strip() for r in rows[1:] if idx < len(r)]
                if name in VOCABULARY_COLUMNS:
                    record(len({normalise_id(c) for c in cells} & wanted), path, f"column {name}")
                    continue
                if is_generated_column(name):
                    cells = [c for c in cells if not _STRUCTURED_RE.match(c)]
                record(token_hits(" ".join(cells)), path, f"column {name}")
        elif suffix == ".json":
            try:
                strings = [s for s in _json_strings(json.loads(text)) if not _STRUCTURED_RE.match(s.strip())]
            except ValueError:
                strings = [text]
            record(token_hits(" ".join(strings)), path, "string values")
        else:
            record(token_hits(" ".join(_BACKTICK_RE.findall(text))), path, "quoted names")
    return findings
