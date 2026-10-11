"""Single-pass, chunked profiling of one source table.

A :class:`TableProfile` is fed chunks of text cells and accumulates only
aggregates: counts, capped sets of distinct values, hashes of candidate keys
and integer-coded (event, participant) pairs. Participant identifiers are held
as integer codes from a run-wide :class:`Registry` and never leave memory
through this module.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import classify
from .archive import Member
from .privacy import normalise_id

SENTINELS = (-1.0, -9.0, -99.0, -999.0, -9999.0, 999.0, 9999.0)
NA_TOKENS = {
    "NA", "N/A", "NAN", "NULL", "NONE", "MISSING", "UNKNOWN", "UNK", "NOT AVAILABLE", "NOT DONE",
    "NOT APPLICABLE", ".", "-", "--", "?",
}
NO_VISIT = "(no visit column)"

DISTINCT_CAP = 2000  # exact cardinality is reported up to this many distinct values
NONNUM_CAP = 50  # distinct non-numeric tokens tracked per column
ROLE_VALUE_CAP = 500  # distinct visit codes tracked per visit column
COHORT_VALUE_CAP = 60
TEST_TOKEN_CAP = 20  # distinct non-numeric tokens tracked per test
MAX_EVENT_CODE = 4095
CAPTURE_ROWS = 500_000  # per-participant captures (dates, status, free text) for small tables
CAPTURE_ALL_ROWS = 50_000  # whole-table capture of documentation tables
ATTR_CAP = 500  # distinct values of an assay attribute tracked per test

_SEP = "\x1f"
_U32 = np.uint64(32)
_U44 = np.uint64(44)


class Registry:
    """Maps strings to stable integer codes for the duration of one run."""

    def __init__(self, blank_is_missing: bool = False, normalise=None) -> None:
        self.values: list[str] = []
        self._index: dict[str, int] = {}
        self._blank_is_missing = blank_is_missing
        self._normalise = normalise

    def code(self, value: str) -> int:
        if self._normalise is not None:
            value = self._normalise(value)
        if self._blank_is_missing and value == "":
            return -1
        found = self._index.get(value)
        if found is None:
            found = len(self.values)
            self._index[value] = found
            self.values.append(value)
        return found

    def encode(self, series: pd.Series) -> np.ndarray:
        codes, uniques = pd.factorize(series)
        lut = np.fromiter((self.code(str(u)) for u in uniques), dtype=np.int64, count=len(uniques))
        return lut[codes] if len(lut) else np.full(len(series), -1, dtype=np.int64)

    def __len__(self) -> int:
        return len(self.values)


def new_participant_registry() -> Registry:
    return Registry(blank_is_missing=True, normalise=normalise_id)


def token_class(token: str) -> str:
    """Classify a non-numeric value found in a numeric field."""
    upper = token.strip().upper()
    if upper.startswith("<") or "LLOQ" in upper or "BELOW" in upper:
        return "below_limit"
    if upper.startswith(">") or "ULOQ" in upper or "ABOVE" in upper:
        return "above_limit"
    if upper in {"ND", "N.D.", "NOT DETECTED"} or "UNDETECT" in upper:
        return "not_detected"
    if upper in NA_TOKENS:
        return "na_like_text"
    return "other_text"


def pack(events: np.ndarray, pids: np.ndarray) -> np.ndarray:
    return (events.astype(np.uint64) << _U32) | pids.astype(np.uint64)


def unpack(packed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (packed >> _U32).astype(np.int64), (packed & np.uint64(0xFFFFFFFF)).astype(np.int64)


def _unique_concat(parts: list[np.ndarray], dtype=np.uint64) -> np.ndarray:
    if not parts:
        return np.empty(0, dtype=dtype)
    return np.unique(np.concatenate(parts))


@dataclass
class ColStats:
    n_blank: int = 0
    n_na_like: int = 0
    n_numeric: int = 0
    n_intlike: int = 0
    n_nonnum: int = 0
    max_len: int = 0
    date_frac: float = 0.0
    sampled: bool = False
    sentinels: Counter = field(default_factory=Counter)
    nonnum: Counter | None = field(default_factory=Counter)
    distinct: set | None = field(default_factory=set)
    values: Counter | None = field(default_factory=Counter)
    dtype: str = ""
    pairs: list = field(default_factory=list)  # candidate columns only


@dataclass
class LongResult:
    combos: list[tuple[str, str, str, str]]  # (test, matrix, unit, assay)
    n_meas: Counter  # (combo, event) -> rows
    triples: np.ndarray  # packed combo<<44 | event<<32 | participant
    n_blank: Counter
    n_numeric: Counter
    n_nonnum: Counter
    tokens: dict[int, Counter | None]
    sentinels: Counter  # (combo, sentinel) -> rows
    attrs: dict = field(default_factory=dict)  # attribute column -> {combo: set of values, or None if too many}

    def participants_by_combo_event(self) -> pd.DataFrame:
        """Distinct (combo, event, participant) triples as integer columns."""
        t = self.triples
        return pd.DataFrame({
            "combo": (t >> _U44).astype(np.int64),
            "event": ((t >> _U32) & np.uint64(0xFFF)).astype(np.int64),
            "pid": (t & np.uint64(0xFFFFFFFF)).astype(np.int64),
        })


@dataclass
class TableResult:
    member: Member
    table_name: str
    sheet: str | None
    base_name: str
    name_date: str
    status: str
    family: str
    columns: list[str]
    roles: classify.Roles
    n_rows: int
    participants: np.ndarray
    n_blank_pid: int
    cols: dict[str, ColStats]
    keys: list[dict]
    granularity: str
    recommended_key: str
    visits: dict[str, dict]
    cohorts: dict[str, dict | None]
    candidates: dict[str, dict]
    long: LongResult | None
    dict_kind: str | None
    decode: dict[tuple[str, str], set]
    descriptions: dict[str, str]
    keywords: dict[tuple[str, str], tuple[int, set]]
    is_reference: bool
    schema_hash: str
    parse_note: str = ""
    truncated: bool = False
    table_id: str = ""
    captured: pd.DataFrame | None = None  # in-memory only; never written to reports
    capture_dropped: bool = False

    @property
    def is_dictionary(self) -> bool:
        return self.dict_kind is not None

    @property
    def display_name(self) -> str:
        return self.table_name


class TableProfile:
    """Accumulates the aggregates of one table across chunks."""

    def __init__(
        self,
        member: Member,
        table_name: str,
        sheet: str | None,
        columns: list[str],
        participants: Registry,
        events: Registry,
        max_category_values: int = 20,
        is_reference: bool = False,
        capture=None,
    ) -> None:
        self.member, self.table_name, self.sheet = member, table_name, sheet
        self.columns = list(columns)
        self.pids, self.events = participants, events
        self.max_cat = max_category_values
        self.is_reference = is_reference
        self.roles = classify.detect_roles(self.columns)
        self.dict_kind = classify.dictionary_kind(table_name, self.columns)
        self.n_rows = 0
        self.n_blank_pid = 0
        self.stats = {c: ColStats() for c in self.columns}
        self._participants: list[np.ndarray] = []
        self._no_visit = events.code(NO_VISIT)

        self.candidates: dict[str, list[classify.Rule]] = {}
        self.keyword_cols: list[str] = []
        if not is_reference and self.dict_kind is None and self.roles.pid:
            skip = set(self.roles.pid_cols + self.roles.visit_cols + self.roles.date_cols)
            for col in self.columns:
                rules = classify.match_column(col) if col not in skip else []
                if rules:
                    self.candidates[col] = rules
            if classify.TEXT_TABLE_RE.search(classify.norm(table_name)):
                self.keyword_cols = [
                    c for c in self.columns
                    if c not in skip and classify.TEXT_COLUMN_RE.search(classify.norm(c))
                ]
        self.keywords: dict[tuple[str, str], list] = {}

        self.visit_rows: dict[str, Counter | None] = {c: Counter() for c in self.roles.visit_cols}
        self.visit_pairs: dict[str, list] = {c: [] for c in self.roles.visit_cols}
        self.cohort_sets: dict[str, dict | None] = {c: {} for c in self.roles.cohort_cols}

        self.key_candidates = self._key_candidates()
        self.key_hashes: dict[str, list] = {label: [] for label, _ in self.key_candidates}

        # long-format state
        self._combo_index: dict[tuple, int] = {}
        self._combos: list[tuple] = []
        self._n_meas: Counter = Counter()
        self._triples: list[np.ndarray] = []
        self._l_blank: Counter = Counter()
        self._l_numeric: Counter = Counter()
        self._l_nonnum: Counter = Counter()
        self._l_tokens: dict[int, Counter | None] = {}
        self._l_sentinels: Counter = Counter()
        self._l_attrs: dict[str, dict] = {c: {} for c in self.roles.long_attr_cols}

        self.decode: dict[tuple[str, str], set] = {}
        self.descriptions: dict[str, str] = {}
        self._last_item = ""

        # Columns kept in memory for the configured small tables (see domain.py).
        self.capture_all = capture == "ALL"
        self.capture_cols: list[str] = []
        if self.capture_all:
            self.capture_cols = list(self.columns)
        elif capture:
            taken = set(self.roles.pid_cols + self.roles.visit_cols)
            for name in capture:
                if name == "__TEXT__":
                    self.capture_cols += [
                        c for c in self.columns
                        if c not in taken and c not in self.roles.date_cols
                        and classify.TEXT_COLUMN_RE.search(classify.norm(c))
                    ]
                elif name.startswith("__RE__:"):
                    self.capture_cols += [
                        c for c in self.columns if c not in taken and re.search(name[len("__RE__:"):], c)
                    ]
                elif name in self.columns:
                    self.capture_cols.append(name)
            self.capture_cols = list(dict.fromkeys(self.capture_cols))
        self._captured: list[pd.DataFrame] | None = [] if self.capture_cols else None
        self._capture_limit = CAPTURE_ALL_ROWS if self.capture_all else CAPTURE_ROWS
        self.capture_dropped = False

    # ------------------------------------------------------------------ keys
    def _key_candidates(self) -> list[tuple[str, list[str]]]:
        r = self.roles
        keys: list[tuple[str, list[str]]] = []
        if r.pid:
            base = [r.pid] + ([r.visit] if r.visit else [])
            keys.append(("participant", [r.pid]))
            if r.visit:
                keys.append(("participant+visit", base))
            if r.form_cols:
                keys.append(("participant+visit+form", base + r.form_cols))
            if r.is_long:
                keys.append(("participant+visit+test", base + [r.test_col]))
                extra = [c for c in [r.matrix_col, r.unit_col, *r.assay_cols] if c]
                if extra:
                    keys.append(("participant+visit+test+assay", base + [r.test_col] + extra))
            if r.sample_col:
                keys.append(("participant+sample", [r.pid, r.sample_col]))
            if r.series_col:
                keys.append(("participant+series", [r.pid, r.series_col]))
        if r.rowid_col:
            keys.append(("row_id (surrogate)", [r.rowid_col]))
        return keys

    # ---------------------------------------------------------------- update
    def update(self, chunk: pd.DataFrame) -> None:
        n = len(chunk)
        if n == 0:
            return
        self.n_rows += n
        data = {c: chunk[c].astype(str).str.strip() for c in self.columns}
        r = self.roles

        if r.pid:
            pid = self.pids.encode(data[r.pid])
            self.n_blank_pid += int((pid < 0).sum())
            self._participants.append(np.unique(pid[pid >= 0]))
            for extra in r.pid_cols[1:]:
                self.pids.encode(data[extra])  # registered so the privacy self-check knows them
        else:
            pid = np.full(n, -1, dtype=np.int64)
        has_pid = pid >= 0

        if r.visit:
            ev = self.events.encode(data[r.visit])
        else:
            ev = np.full(n, self._no_visit, dtype=np.int64)
        packed = pack(ev, np.where(has_pid, pid, 0))

        for col in r.visit_cols:
            counter = self.visit_rows[col]
            if counter is not None:
                counter.update(data[col].value_counts().to_dict())
                if len(counter) > ROLE_VALUE_CAP:
                    self.visit_rows[col] = None
            codes = ev if col == r.visit else self.events.encode(data[col])
            self.visit_pairs[col].append(np.unique(pack(codes, np.where(has_pid, pid, 0))[has_pid]))

        for col in r.cohort_cols:
            sets = self.cohort_sets[col]
            if sets is None:
                continue
            values = data[col].to_numpy(dtype=object)
            mask = has_pid & (values != "")
            pairs = pd.DataFrame({"v": values[mask], "p": pid[mask]}).drop_duplicates()
            for value, group in pairs.groupby("v")["p"]:
                sets.setdefault(str(value), set()).update(group.tolist())
            if len(sets) > COHORT_VALUE_CAP:
                self.cohort_sets[col] = None

        for col in self.columns:
            self._update_column(col, data[col], packed, has_pid)

        if self._captured is not None:
            if self.n_rows > self._capture_limit:
                self._captured, self.capture_dropped = None, True
            else:
                kept = pd.DataFrame({c: data[c].to_numpy(dtype=object) for c in self.capture_cols})
                kept["_pid"] = pid
                kept["_event"] = data[r.visit].to_numpy(dtype=object) if r.visit else ""
                self._captured.append(kept)

        for label, cols in self.key_candidates:
            frame = pd.DataFrame({c: data[c] for c in cols})
            self.key_hashes[label].append(pd.util.hash_pandas_object(frame, index=False).to_numpy())

        if r.is_long and not self.is_reference:
            self._update_long(data, ev, pid, has_pid)
        if self.dict_kind:
            self._update_dictionary(data)
        for col in self.keyword_cols:
            for group, pattern in classify.KEYWORD_RES.items():
                hit = data[col].str.contains(pattern.pattern, case=False, regex=True).to_numpy(dtype=bool)
                if hit.any():
                    entry = self.keywords.setdefault((col, group), [0, set()])
                    entry[0] += int(hit.sum())
                    entry[1].update(pid[hit & has_pid].tolist())

    def _update_column(self, col: str, s: pd.Series, packed: np.ndarray, has_pid: np.ndarray) -> None:
        st = self.stats[col]
        blank = (s == "").to_numpy(dtype=bool)
        st.n_blank += int(blank.sum())
        if blank.all():
            return
        num = pd.to_numeric(s, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
        isnum = ~np.isnan(num)
        st.n_numeric += int(isnum.sum())
        st.n_intlike += int((isnum & (np.floor(num) == num)).sum())
        for sentinel in SENTINELS:
            count = int((num == sentinel).sum())
            if count:
                st.sentinels[sentinel] += count
        nonnum = ~blank & ~isnum
        na_like = np.zeros(len(s), dtype=bool)
        if nonnum.any():
            text = s[nonnum]
            st.n_nonnum += len(text)
            na_like[nonnum] = text.str.upper().isin(NA_TOKENS).to_numpy(dtype=bool)
            st.n_na_like += int(na_like.sum())
            if st.nonnum is not None:
                st.nonnum.update(text.value_counts().to_dict())
                if len(st.nonnum) > NONNUM_CAP:
                    st.nonnum = None
        if st.distinct is not None:
            counts = s[~blank].value_counts()
            st.distinct.update(counts.index)
            if len(st.distinct) > DISTINCT_CAP:
                st.distinct, st.values = None, None
            elif st.values is not None:
                st.values.update(counts.to_dict())
                if len(st.values) > self.max_cat:
                    st.values = None
        st.max_len = max(st.max_len, int(s.str.len().max()))
        if not st.sampled:
            sample = s[~blank].head(2000)
            st.date_frac = float(sample.str.match(classify.DATE_VALUE_RE).mean())
            st.sampled = True
        if col in self.candidates:
            available = ~blank & ~na_like & has_pid
            st.pairs.append(np.unique(packed[available]))

    def _update_long(self, data: dict, ev: np.ndarray, pid: np.ndarray, has_pid: np.ndarray) -> None:
        r = self.roles
        n = len(ev)
        blank_col = pd.Series([""] * n, dtype=str)
        parts = [
            data[r.test_col],
            data[r.matrix_col] if r.matrix_col else blank_col,
            data[r.unit_col] if r.unit_col else blank_col,
        ]
        assay = blank_col
        for idx, col in enumerate(r.assay_cols):
            assay = data[col].reset_index(drop=True) if idx == 0 else assay + " / " + data[col].reset_index(drop=True)
        key = parts[0].reset_index(drop=True)
        for part in parts[1:] + [assay]:
            key = key + _SEP + part.reset_index(drop=True)
        codes, uniques = pd.factorize(key)
        lut = np.empty(len(uniques), dtype=np.int64)
        for idx, joined in enumerate(uniques):
            combo = tuple(str(joined).split(_SEP))
            found = self._combo_index.get(combo)
            if found is None:
                found = len(self._combos)
                self._combo_index[combo] = found
                self._combos.append(combo)
            lut[idx] = found
        combo = lut[codes]
        ev_c = np.minimum(ev, MAX_EVENT_CODE)

        pair, counts = np.unique((combo.astype(np.uint64) << _U32) | ev_c.astype(np.uint64), return_counts=True)
        for p, c in zip(pair.tolist(), counts.tolist()):
            self._n_meas[(p >> 32, p & 0xFFFFFFFF)] += c
        triple = (combo.astype(np.uint64) << _U44) | (ev_c.astype(np.uint64) << _U32) | np.where(has_pid, pid, 0).astype(np.uint64)
        self._triples.append(np.unique(triple[has_pid]))

        value = data[r.value_col].reset_index(drop=True)
        blank = (value == "").to_numpy(dtype=bool)
        num = pd.to_numeric(value, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
        isnum = ~np.isnan(num)
        nonnum = ~blank & ~isnum
        for mask, counter in ((blank, self._l_blank), (isnum, self._l_numeric), (nonnum, self._l_nonnum)):
            u, c = np.unique(combo[mask], return_counts=True)
            for k, v in zip(u.tolist(), c.tolist()):
                counter[k] += v
        for sentinel in SENTINELS:
            u, c = np.unique(combo[num == sentinel], return_counts=True)
            for k, v in zip(u.tolist(), c.tolist()):
                self._l_sentinels[(k, sentinel)] += v
        for column, store in self._l_attrs.items():
            seen = pd.DataFrame({"c": combo, "v": data[column].to_numpy(dtype=object)}).drop_duplicates()
            for c_code, item in zip(seen["c"].tolist(), seen["v"].tolist()):
                if item == "" or (c_code in store and store[c_code] is None):
                    continue
                bucket = store.setdefault(c_code, set())
                bucket.add(item)
                if len(bucket) > ATTR_CAP:
                    store[c_code] = None
        if nonnum.any():
            frame = pd.DataFrame({"c": combo[nonnum], "v": value.to_numpy(dtype=object)[nonnum]})
            for (c_code, token), count in frame.groupby(["c", "v"]).size().items():
                bucket = self._l_tokens.setdefault(int(c_code), Counter())
                if bucket is None:
                    continue
                bucket[str(token)] += int(count)
                if len(bucket) > TEST_TOKEN_CAP:
                    self._l_tokens[int(c_code)] = None

    def _update_dictionary(self, data: dict) -> None:
        by_norm = {classify.norm(c): c for c in self.columns}
        item = by_norm.get("ITM_NAME") or by_norm.get("VARIABLE") or by_norm.get("ITEM")
        if self.dict_kind == "code_list":
            code, decode = by_norm["CODE"], by_norm["DECODE"]
            items = data[item] if item else pd.Series([""] * len(data[code]))
            for i, c, d in zip(items, data[code], data[decode]):
                # Workbook dictionaries name the variable once and leave it blank on the
                # following code rows, so a blank item inherits the last one seen.
                if i:
                    self._last_item = i
                if c != "" and d != "":
                    self.decode.setdefault((classify.norm(i or self._last_item), str(c)), set()).add(str(d)[:80])
        elif item:
            desc = by_norm.get("DSCR") or by_norm.get("DESCRIPTION")
            if desc:
                for i, d in zip(data[item], data[desc]):
                    if i and d:
                        self.descriptions.setdefault(classify.norm(i), str(d)[:160])

    # -------------------------------------------------------------- finalize
    def _dtype(self, col: str) -> str:
        st = self.stats[col]
        nonblank = self.n_rows - st.n_blank
        if nonblank <= 0:
            return "empty"
        content = nonblank - st.n_na_like
        if content <= 0:
            return "na_tokens_only"
        if col in self.roles.date_cols or st.date_frac >= 0.8:
            return "date"
        if st.n_numeric >= content:
            return "integer" if st.n_intlike == st.n_numeric else "float"
        if st.n_numeric >= 0.5 * content:
            return "numeric_with_text_tokens"
        return "mixed" if st.n_numeric else "string"

    def finalize(self) -> TableResult:
        for col in self.columns:
            self.stats[col].dtype = self._dtype(col)
            if self.stats[col].dtype == "date" and col not in self.roles.date_cols:
                self.roles.date_cols.append(col)

        keys = []
        unique_labels = set()
        for label, cols in self.key_candidates:
            hashes = np.concatenate(self.key_hashes[label]) if self.key_hashes[label] else np.empty(0, dtype=np.uint64)
            n_dup = int(len(hashes) - len(np.unique(hashes)))
            is_unique = len(hashes) > 0 and n_dup == 0
            if is_unique:
                unique_labels.add(label)
            keys.append({"label": label, "columns": cols, "is_unique": is_unique, "duplicate_rows": n_dup})

        r = self.roles
        preferred = [
            "participant", "participant+visit", "participant+visit+form", "participant+visit+test",
            "participant+visit+test+assay", "participant+sample", "participant+series",
        ]
        if r.series_col:
            preferred.insert(0, "participant+series")
        elif r.sample_col:
            preferred.insert(0, "participant+sample")
        recommended = next((k for k in preferred if k in unique_labels), "")
        if self.dict_kind:
            granularity = "reference/dictionary"
        elif not r.pid or self.n_rows == 0:
            granularity = "unknown"
        elif r.is_long:
            granularity = "participant-visit-test"
        elif r.series_col:
            granularity = "imaging-series"
        elif r.sample_col:
            granularity = "participant-sample"
        elif "participant" in unique_labels:
            granularity = "participant-level"
        elif "participant+visit" in unique_labels:
            granularity = "participant-visit"
        elif r.form_cols or r.rowid_col or not r.visit:
            granularity = "form/event-level"
        else:
            granularity = "unknown"

        long = None
        if r.is_long and not self.is_reference:
            long = LongResult(
                combos=self._combos, n_meas=self._n_meas, triples=_unique_concat(self._triples),
                n_blank=self._l_blank, n_numeric=self._l_numeric, n_nonnum=self._l_nonnum,
                tokens=self._l_tokens, sentinels=self._l_sentinels, attrs=self._l_attrs,
            )

        stem = self.table_name.split("#")[0]
        base, name_date = classify.split_table_name(stem)
        if self.sheet is not None:
            base = f"{base}#{self.sheet}"
        return TableResult(
            member=self.member,
            table_name=self.table_name,
            sheet=self.sheet,
            base_name=base,
            name_date=name_date,
            status=classify.version_status(self.table_name),
            family=classify.family_name(base),
            columns=self.columns,
            roles=r,
            n_rows=self.n_rows,
            participants=_unique_concat(self._participants, dtype=np.int64),
            n_blank_pid=self.n_blank_pid,
            cols=self.stats,
            keys=keys,
            granularity=granularity,
            recommended_key=recommended,
            visits={
                c: {"rows": self.visit_rows[c], "pairs": _unique_concat(self.visit_pairs[c])}
                for c in r.visit_cols
            },
            cohorts=self.cohort_sets,
            candidates={
                c: {"rules": rules, "pairs": _unique_concat(self.stats[c].pairs)}
                for c, rules in self.candidates.items()
            },
            long=long,
            dict_kind=self.dict_kind,
            decode=self.decode,
            descriptions=self.descriptions,
            keywords={k: (v[0], v[1]) for k, v in self.keywords.items()},
            is_reference=self.is_reference,
            schema_hash=hashlib.sha1("|".join(self.columns).encode("utf-8")).hexdigest()[:12],
            captured=pd.concat(self._captured, ignore_index=True) if self._captured else None,
            capture_dropped=self.capture_dropped,
        )


_CODE_LIKE_RE = re.compile(r"^[A-Za-z0-9 _./#+\-'(),&:%]{1,40}$")
_DATE_RE = re.compile(classify.DATE_VALUE_RE)


def is_code_like(value: str) -> bool:
    """True for a short code that is safe to print (not a date, not free text)."""
    return bool(_CODE_LIKE_RE.match(value)) and not _DATE_RE.match(value)
