"""Read-only inventory of PPMI download archives.

Archives are never extracted into the repository. Members are streamed
straight out of the ZIP; a nested ZIP (one level deep) is copied to a spooled
temporary file in the operating-system temp directory, which is deleted as
soon as it is closed.
"""

from __future__ import annotations

import fnmatch
import hashlib
import shutil
import tempfile
import zipfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import IO, Iterator

TABULAR_EXTS = {".csv", ".tsv", ".xlsx", ".xlsm"}
UNSUPPORTED_TABULAR_EXTS = {".xls", ".sas7bdat", ".sav", ".dta", ".parquet", ".xpt", ".rdata", ".rds"}
IMAGING_EXTS = {
    ".dcm", ".ima", ".nii", ".nii.gz", ".img", ".hdr", ".mgz", ".mgh", ".nrrd",
    ".par", ".rec", ".v", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp",
}
DOCUMENT_EXTS = {".pdf", ".doc", ".docx", ".rtf", ".md", ".txt", ".html", ".htm", ".pptx", ".ppt"}
ARCHIVE_EXTS = {".zip"}
OTHER_ARCHIVE_EXTS = {".gz", ".tar", ".tgz", ".7z", ".rar"}

# Member names are listed only for these types. Imaging and other binary
# members are reported as aggregate counts, because their paths commonly
# contain participant identifiers.
NAMED_TYPES = {"tabular", "tabular_unsupported", "document", "nested_zip", "archive_unsupported"}

_SPOOL_BYTES = 64 * 1024 * 1024
_BLOCK = 1024 * 1024


@dataclass(frozen=True)
class Member:
    """One file inside a source: a ZIP member, a nested-ZIP member or a loose file."""

    source: str  # path of the archive / loose file relative to the data root (posix)
    source_kind: str  # "zip" or "loose_file"
    path: str  # member path inside the archive ("" for a loose file)
    nested_in: str | None  # path of the inner ZIP, when the member is nested
    size: int
    compressed_size: int | None
    crc32: str
    modified: str
    ext: str
    file_type: str

    @property
    def display_path(self) -> str:
        if self.source_kind == "loose_file":
            return PurePosixPath(self.source).name
        return f"{self.nested_in}!/{self.path}" if self.nested_in else self.path

    @property
    def file_name(self) -> str:
        return PurePosixPath(self.path or self.source).name

    @property
    def content_signature(self) -> str:
        return f"{self.size}:{self.crc32}"


@dataclass
class SourceInfo:
    """One archive or loose file found under the data root."""

    source: str
    kind: str
    size: int
    modified: str
    sha256: str
    members: list[Member]
    status: str = "audited"
    note: str = ""


def extension(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".nii.gz"):
        return ".nii.gz"
    return PurePosixPath(lower).suffix


def file_type(name: str) -> str:
    ext = extension(name)
    if ext in TABULAR_EXTS:
        return "tabular"
    if ext in UNSUPPORTED_TABULAR_EXTS:
        return "tabular_unsupported"
    if ext in IMAGING_EXTS:
        return "imaging"
    if ext in DOCUMENT_EXTS:
        return "document"
    if ext in ARCHIVE_EXTS:
        return "nested_zip"
    if ext in OTHER_ARCHIVE_EXTS:
        return "archive_unsupported"
    return "other"


def file_digest(path: Path, with_sha: bool = True) -> tuple[str, str]:
    """Return ``(sha256, crc32)`` of a file, read in blocks."""
    sha = hashlib.sha256()
    crc = 0
    with open(path, "rb") as fh:
        while block := fh.read(_BLOCK):
            if with_sha:
                sha.update(block)
            crc = zlib.crc32(block, crc)
    return (sha.hexdigest() if with_sha else ""), f"{crc & 0xFFFFFFFF:08x}"


def _mtime(path: Path) -> str:
    stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return stamp.replace(microsecond=0).isoformat()


def _zip_time(info: zipfile.ZipInfo) -> str:
    try:
        return datetime(*info.date_time).isoformat()
    except (ValueError, TypeError):
        return ""


def matches_any(name: str, patterns: list[str]) -> bool:
    base = PurePosixPath(name).name
    return any(
        fnmatch.fnmatch(name.lower(), p.lower()) or fnmatch.fnmatch(base.lower(), p.lower())
        for p in patterns
    )


def discover_files(root: Path) -> list[Path]:
    """All regular files under ``root``, in a deterministic order."""
    return sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix())


def _zip_members(zf: zipfile.ZipFile, source: str, nested_in: str | None) -> list[Member]:
    members = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        members.append(
            Member(
                source=source,
                source_kind="zip",
                path=info.filename,
                nested_in=nested_in,
                size=info.file_size,
                compressed_size=info.compress_size,
                crc32=f"{info.CRC & 0xFFFFFFFF:08x}",
                modified=_zip_time(info),
                ext=extension(info.filename),
                file_type=file_type(info.filename),
            )
        )
    return members


@contextmanager
def _spooled_copy(stream: IO[bytes]) -> Iterator[IO[bytes]]:
    """Seekable temporary copy of a stream, held in memory or the OS temp dir."""
    with tempfile.SpooledTemporaryFile(max_size=_SPOOL_BYTES) as tmp:
        shutil.copyfileobj(stream, tmp, _BLOCK)
        tmp.seek(0)
        yield tmp


def list_zip(path: Path, source: str) -> list[Member]:
    """List a ZIP's members, descending one level into nested ZIPs."""
    members: list[Member] = []
    with zipfile.ZipFile(path, "r") as zf:
        outer = _zip_members(zf, source, None)
        members.extend(outer)
        for member in outer:
            if member.file_type != "nested_zip":
                continue
            try:
                with zf.open(member.path, "r") as raw, _spooled_copy(raw) as tmp:
                    with zipfile.ZipFile(tmp, "r") as inner:
                        members.extend(_zip_members(inner, source, member.path))
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError):
                # The inner archive stays listed as a member; it is just not descended.
                continue
    return sorted(members, key=lambda m: (m.nested_in or "", m.path))


def inspect_source(root: Path, path: Path, hash_archives: bool = True) -> SourceInfo:
    """Inventory one archive or loose file. Raises ``zipfile.BadZipFile`` for a broken ZIP."""
    source = path.relative_to(root).as_posix()
    size = path.stat().st_size
    if extension(path.name) == ".zip":
        sha, _ = file_digest(path, with_sha=hash_archives)
        return SourceInfo(source, "zip", size, _mtime(path), sha, list_zip(path, source))
    sha, crc = file_digest(path, with_sha=hash_archives)
    member = Member(
        source=source,
        source_kind="loose_file",
        path="",
        nested_in=None,
        size=size,
        compressed_size=None,
        crc32=crc,
        modified=_mtime(path),
        ext=extension(path.name),
        file_type=file_type(path.name),
    )
    return SourceInfo(source, "loose_file", size, _mtime(path), sha, [member])


@contextmanager
def open_member(root: Path, member: Member) -> Iterator[IO[bytes]]:
    """Open a member for reading as a binary stream. Nothing is written to the repository."""
    path = root / member.source
    if member.source_kind == "loose_file":
        with open(path, "rb") as fh:
            yield fh
        return
    with zipfile.ZipFile(path, "r") as zf:
        if member.nested_in is None:
            with zf.open(member.path, "r") as fh:
                yield fh
            return
        with zf.open(member.nested_in, "r") as raw, _spooled_copy(raw) as tmp:
            with zipfile.ZipFile(tmp, "r") as inner, inner.open(member.path, "r") as fh:
                yield fh
