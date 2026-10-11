"""Read approved source tables straight from the PPMI download archives.

Tables are located by name pattern, the newest copy wins, and nothing is
extracted to disk. Pilot and Deprecated biospecimen tables are refused by
name, whatever pattern asked for them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable

import pandas as pd

from . import archive, classify
from .domain import matches
from .privacy import normalise_id
from .table_reader import iter_table_chunks

ID_COLUMN = "PATNO"


class SourceError(RuntimeError):
    """A required source table is missing, forbidden or malformed."""


def find_column(columns, name: str) -> str | None:
    wanted = str(name).strip().upper()
    return next((c for c in columns if str(c).strip().upper() == wanted), None)


def to_number(series: pd.Series) -> pd.Series:
    """Numeric values; anything that is not a number becomes NaN."""
    return pd.to_numeric(series.astype(str).str.strip().replace("", pd.NA), errors="coerce").astype("float64")


@dataclass
class SourceLoader:
    """Finds and reads tables under the raw-data root, remembering what was used."""

    root: Path
    forbidden: list[str] = field(default_factory=lambda: ["Pilot_*", "Deprecated_*"])
    used: dict[str, dict] = field(default_factory=dict)
    seen_ids: set = field(default_factory=set)
    _members: list | None = None
    _hashes: dict = field(default_factory=dict)

    def members(self) -> list[archive.Member]:
        if self._members is None:
            found: list[archive.Member] = []
            for path in archive.discover_files(self.root):
                rel = path.relative_to(self.root).as_posix()
                if archive.extension(path.name) == ".zip":
                    found += [m for m in archive.list_zip(path, rel) if m.file_type == "tabular"]
                elif archive.file_type(path.name) == "tabular":
                    found += archive.inspect_source(self.root, path, hash_archives=False).members
            self._members = found
        return self._members

    def find(self, patterns: list[str], exclude: list[str] | None = None) -> archive.Member:
        """Newest tabular member whose file name matches ``patterns``."""
        options = []
        for m in self.members():
            stem = PurePosixPath(m.file_name).stem
            base, date = classify.split_table_name(stem)
            if not matches(patterns, stem, base) or matches(list(exclude or []), stem, base):
                continue
            if matches(self.forbidden, stem, base):
                raise SourceError(f"table name matches a forbidden pattern (Pilot/Deprecated results are never used): {stem}")
            options.append((date, m.modified, m.source, m))
        if not options:
            raise SourceError(f"no source table matches {patterns}")
        return max(options, key=lambda o: o[:3])[3]

    def _file_record(self, member: archive.Member) -> dict:
        if member.source not in self._hashes:
            path = self.root / member.source
            sha = hashlib.sha256()
            with open(path, "rb") as fh:
                while block := fh.read(1024 * 1024):
                    sha.update(block)
            self._hashes[member.source] = {"file": member.source, "size_bytes": path.stat().st_size, "sha256": sha.hexdigest()}
        return self._hashes[member.source]

    def read(
        self,
        key: str,
        patterns: list[str],
        exclude: list[str] | None = None,
        columns: list[str] | None = None,
        row_filter: Callable[[pd.DataFrame], pd.Series] | None = None,
        sheet_requires: list[str] | None = None,
    ) -> pd.DataFrame:
        """Read one table as text. ``columns`` are matched without regard to case.

        ``row_filter`` is applied per chunk, so a large table is never held whole.
        The participant identifier is normalised and recorded for the report
        privacy check.
        """
        member = self.find(patterns, exclude)
        parts: list[pd.DataFrame] = []
        sheet_used = None
        with archive.open_member(self.root, member) as stream:
            for sheet, chunk in iter_table_chunks(stream, member.ext, 200_000):
                if sheet_requires and any(find_column(chunk.columns, c) is None for c in sheet_requires):
                    continue
                if sheet_used is None:
                    sheet_used = sheet
                elif sheet != sheet_used:
                    continue  # a workbook contributes one data sheet
                chunk = chunk.apply(lambda s: s.astype(str).str.strip())
                id_col = find_column(chunk.columns, ID_COLUMN)
                if id_col is not None:
                    chunk[id_col] = chunk[id_col].map(normalise_id)
                    self.seen_ids.update(chunk[id_col].unique().tolist())
                    chunk = chunk.rename(columns={id_col: ID_COLUMN})
                if columns is not None:
                    wanted = {}
                    for name in columns:
                        actual = find_column(chunk.columns, name)
                        if actual is None:
                            raise SourceError(f"{key}: required column missing: {name}")
                        wanted[actual] = name
                    chunk = chunk[list(wanted)].rename(columns=wanted)
                if row_filter is not None:
                    chunk = chunk[row_filter(chunk).to_numpy(dtype=bool)]
                parts.append(chunk)
        if not parts:
            raise SourceError(f"{key}: no readable sheet or rows in {PurePosixPath(member.file_name).name}")
        frame = pd.concat(parts, ignore_index=True)
        self.used[key] = {
            "table": PurePosixPath(member.file_name).stem + (f"#{sheet_used}" if sheet_used else ""),
            "member_path": member.display_path, **self._file_record(member), "n_rows_read": int(len(frame)),
        }
        return frame
