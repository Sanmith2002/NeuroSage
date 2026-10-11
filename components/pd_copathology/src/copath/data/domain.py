"""Reviewed, table-specific decisions for the audit (``configs/domain_overrides.yaml``).

The generic naming rules in :mod:`copath.data.classify` stay untouched; this
module layers explicit decisions on top of them: which tables define the
analytic universe, which are excluded, which modality a table really belongs
to, and which columns of a few small tables must be kept in memory for
per-participant timing and status counts.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ALL_COLUMNS = "ALL"
DIAGNOSIS = "diagnosis"


def matches(patterns: list[str], *names: str) -> bool:
    return any(fnmatch.fnmatch(n.lower(), p.lower()) for p in patterns for n in names if n)


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    return [str(v) for v in value] if isinstance(value, (list, tuple)) else [str(value)]


@dataclass
class DomainOverrides:
    """Parsed overrides. An empty instance changes nothing."""

    raw: dict = field(default_factory=dict)
    base_dir: Path | None = None

    @classmethod
    def from_yaml(cls, path: Path | None) -> "DomainOverrides":
        if path is None or not Path(path).is_file():
            return cls()
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}, Path(path).resolve().parent)

    def drug_classes(self) -> dict:
        """Drug-name lists for the medication audit (empty when not configured)."""
        name = self.section("medications").get("drug_classes_file")
        if not name or self.base_dir is None or not (self.base_dir / str(name)).is_file():
            return {}
        raw = yaml.safe_load((self.base_dir / str(name)).read_text(encoding="utf-8")) or {}
        components = raw.get("components")
        if not components:
            return raw
        # The frozen include / conditional / exclude lists, viewed the way the audit reports them.
        titles = {"htn": "antihypertensive", "dyslip": "lipid-lowering", "dm": "antidiabetic"}
        classes: dict[str, dict] = {}
        flagged: dict[str, dict] = {}
        for key, title in titles.items():
            section = components.get(key) or {}
            classes[title] = {g: a for drugs in (section.get("include") or {}).values() for g, a in (drugs or {}).items()}
            for kind in ("conditional", "exclude"):
                flagged.update({group: drugs or {} for group, drugs in (section.get(kind) or {}).items()})
        return {"classes": classes, "flagged": flagged,
                "indication_categories": raw.get("indication_categories") or {}}

    def is_derived(self, *names: str) -> bool:
        return matches(_as_list(self.raw.get("derived_tables")), *names)

    # ------------------------------------------------------------ sections
    def section(self, name: str) -> dict:
        return self.raw.get(name) or {}

    def patterns(self, section: str, key: str) -> list[str]:
        return _as_list(self.section(section).get(key))

    @property
    def universe(self) -> dict:
        return self.section("universe")

    @property
    def baseline_events(self) -> list[str]:
        return _as_list(self.universe.get("baseline_events")) or ["BL"]

    @property
    def screening_events(self) -> list[str]:
        return _as_list(self.universe.get("screening_events")) or ["SC"]

    @property
    def reference_tables(self) -> list[str]:
        return _as_list(self.raw.get("reference_tables"))

    # -------------------------------------------------------------- lookups
    def modality_override(self, *names: str) -> dict | None:
        for entry in self.raw.get("modality_overrides") or []:
            if matches([entry["pattern"]], *names):
                return entry
        return None

    def exclusion_reason(self, *names: str) -> str:
        """Why a table is left out of modality counts, or ``""`` when it is kept."""
        for entry in self.raw.get("exclude_from_modalities") or []:
            if matches([entry["pattern"]], *names):
                return str(entry.get("reason") or "excluded by configuration")
        override = self.modality_override(*names)
        if override and override.get("exclude"):
            return str(override.get("reason") or "excluded by configuration")
        return ""

    def candidate_excluded(self, names: tuple[str, ...], target: str, concept: str, field_name: str) -> str:
        """Reason a name match is a known false positive, or ``""``."""
        for entry in self.raw.get("candidate_exclusions") or []:
            if entry.get("table") and not matches([entry["table"]], *names):
                continue
            if entry.get("target") and entry["target"] != target:
                continue
            if entry.get("concept") and entry["concept"] != concept:
                continue
            if entry.get("field") and not re.search(entry["field"], field_name):
                continue
            return str(entry.get("reason") or "excluded by configuration")
        return ""

    def group_tables(self) -> dict[str, list[str]]:
        return {k: _as_list(v) for k, v in (self.raw.get("overlap_group_tables") or {}).items()}

    def is_reference_table(self, *names: str) -> bool:
        return matches(self.reference_tables, *names)

    def capture_columns(self, names: tuple[str, ...], columns: list[str], has_participant_id: bool):
        """Columns of a table to keep in memory, ``ALL_COLUMNS``, or ``None``.

        Captured values never leave memory: they are used for baseline dates,
        diagnosis timing, status values and keyword counts, all reported as
        aggregates. Reference tables are captured whole so they can be printed
        after the identifier check.
        """
        whole = self.is_reference_table(*names) or matches(_as_list(self.section("annotated_dictionary").get("table")), *names)
        if whole and not has_participant_id:
            return ALL_COLUMNS
        if not has_participant_id:
            return None
        wanted: list[str] = []
        if matches(_as_list(self.universe.get("curated_table")), *names):
            wanted += _as_list(self.universe.get("baseline_date_column"))
        med = self.section("medical_conditions")
        if matches(_as_list(med.get("table")), *names):
            wanted += _as_list(med.get("category_column")) + _as_list(med.get("date_columns"))
            wanted += _as_list(med.get("year_columns")) + ["__TEXT__"]
        drugs = self.section("medications")
        if matches(_as_list(drugs.get("table")), *names):
            for key in ("start_date_column", "stop_date_column", "ongoing_column", "indication_code_column",
                        "indication_text_column", "name_columns", "text_columns"):
                wanted += _as_list(drugs.get(key))
        vitals = self.section("vital_signs")
        if matches(_as_list(vitals.get("table")), *names):
            wanted += _as_list(vitals.get("supine_sbp_column")) + _as_list(vitals.get("supine_dbp_column"))
        fs7 = self.section("fs7_wm_check")
        if matches(_as_list(fs7.get("tables")), *names) and fs7.get("capture_field"):
            wanted.append("__RE__:" + str(fs7["capture_field"]))
        feas = self.section("baseline_feasibility")
        if matches(_as_list(feas.get("saa_table")), *names):
            wanted += _as_list(feas.get("saa_status_column"))
        if not wanted:
            return None
        present = {c.upper(): c for c in columns}
        special = [w for w in dict.fromkeys(wanted) if w.startswith("__")]
        return [present[w.upper()] for w in dict.fromkeys(wanted) if w.upper() in present] + special
