"""Block target-defining variables and near-proxies.

``configs/leakage_matrix.csv`` is the single authoritative source: one row per
column of the analytic dataset, one status per label. ``docs/leakage_matrix.md``
and ``configs/feature_sets/<label>_<tier>.yaml`` are generated from it and are
never edited by hand::

    python -m copath.features.leakage_guard        # regenerate both

Statuses
    defining    used to construct the label
    never       never a predictor for this label (leakage or not a feature at all)
    near_proxy  so close to the label that it is excluded from the strict tier
    safe        an ordinary predictor

Tiers (docs/phase1_final_decisions_v1.md sections 5.3 and 9)
    primary = every feature minus defining and never
    strict  = primary minus near_proxy

``defining`` and ``never`` features are in no tier. The former ``full`` tier
was dropped in Phase 2.1 because it equalled ``primary``. Missingness
indicators are never features.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml

from ..data.load import COMPONENT_DIR

MATRIX_PATH = COMPONENT_DIR / "configs" / "leakage_matrix.csv"
FEATURE_SETS_DIR = COMPONENT_DIR / "configs" / "feature_sets"
DOC_PATH = COMPONENT_DIR / "docs" / "leakage_matrix.md"

STATUSES = ("defining", "never", "near_proxy", "safe")
TIERS = ("primary", "strict")
META_COLUMNS = ["feature", "modality", "source", "note"]
MISSINGNESS_RE = re.compile(r"(?i)(_missing|_isna|_is_missing|_available|_avail|_observed)$|^(missing|avail)_")
GENERATED_HEADER = "# GENERATED from configs/leakage_matrix.csv by `python -m copath.features.leakage_guard`. Do not edit.\n"


class LeakageError(ValueError):
    """A feature is not allowed for a label and tier, or the matrix is inconsistent."""


def load_matrix(path: Path = MATRIX_PATH) -> pd.DataFrame:
    matrix = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in META_COLUMNS if c not in matrix.columns]
    if missing:
        raise LeakageError(f"leakage matrix lacks columns: {missing}")
    if matrix["feature"].duplicated().any():
        raise LeakageError("leakage matrix lists a feature more than once")
    for label in labels(matrix):
        bad = set(matrix[label]) - set(STATUSES)
        if bad:
            raise LeakageError(f"leakage matrix: invalid status for {label}: {sorted(bad)}")
    for row in matrix.itertuples():
        if MISSINGNESS_RE.search(row.feature) and any(getattr(row, label) != "never" for label in labels(matrix)):
            raise LeakageError("leakage matrix: a missingness indicator is not marked never for every label")
    return matrix


def labels(matrix: pd.DataFrame) -> list[str]:
    return [c for c in matrix.columns if c not in META_COLUMNS]


def tier_features(matrix: pd.DataFrame, label: str, tier: str) -> list[str]:
    """Features allowed for ``label`` in ``tier``, in matrix order."""
    if tier not in TIERS:
        raise LeakageError(f"unknown tier: {tier}")
    if label not in labels(matrix):
        raise LeakageError(f"label not in the leakage matrix: {label}")
    primary = matrix.loc[~matrix[label].isin(["defining", "never"]), "feature"].tolist()
    near = set(matrix.loc[matrix[label] == "near_proxy", "feature"])
    if tier == "strict":
        return [f for f in primary if f not in near]
    return primary


def features_for(matrix: pd.DataFrame, label: str, tier: str, available: list[str] | None = None,
                 parents: dict[str, str] | None = None) -> list[str]:
    """Tier features for a label or one of its sensitivity variants, limited to available columns."""
    column = (parents or {}).get(label, label)
    chosen = tier_features(matrix, column, tier)
    return chosen if available is None else [f for f in chosen if f in set(available)]


def assert_allowed(features: list[str], matrix: pd.DataFrame, label: str, tier: str,
                   parents: dict[str, str] | None = None) -> None:
    """Raise unless every feature is allowed for the label and tier."""
    column = (parents or {}).get(label, label)
    allowed = set(tier_features(matrix, column, tier))
    known = set(matrix["feature"])
    unknown = [f for f in features if f not in known]
    blocked = [f for f in features if f in known and f not in allowed]
    indicators = [f for f in features if MISSINGNESS_RE.search(f)]
    if unknown or blocked or indicators:
        raise LeakageError(
            f"{label} / {tier}: {len(blocked)} blocked, {len(unknown)} unclassified and "
            f"{len(indicators)} missingness-indicator feature(s): {sorted(set(blocked + unknown + indicators))[:10]}")


def assert_columns_classified(matrix: pd.DataFrame, columns: list[str]) -> None:
    """Every column of the analytic dataset must have a row in the matrix."""
    unknown = sorted(set(columns) - set(matrix["feature"]))
    if unknown:
        raise LeakageError(f"{len(unknown)} analytic column(s) are not classified in the leakage matrix: {unknown[:20]}")


def render_markdown(matrix: pd.DataFrame) -> str:
    names = labels(matrix)
    lines = ["# Leakage matrix", "", GENERATED_HEADER.strip("# \n").join(["_", "_"]), "",
             "One row per column of the analytic dataset. `defining` and `never` features are excluded from every "
             "tier; missingness indicators are never features. Tiers: primary = everything except defining and never; "
             "strict = primary minus near-proxies.", "",
             "## Features per label and tier", "",
             "| Label | primary | strict | defining | never | near_proxy |", "|---|---|---|---|---|---|"]
    for label in names:
        counts = matrix[label].value_counts()
        lines.append(f"| {label} | {len(tier_features(matrix, label, 'primary'))} | {len(tier_features(matrix, label, 'strict'))} "
                     f"| {counts.get('defining', 0)} | {counts.get('never', 0)} "
                     f"| {counts.get('near_proxy', 0)} |")
    for label in names:
        lines += ["", f"## {label}", ""]
        for status in ("defining", "near_proxy"):
            found = matrix.loc[matrix[label] == status, "feature"].tolist()
            lines += [f"**{status}** ({len(found)}): " + (", ".join(f"`{f}`" for f in found) or "none"), ""]
    everywhere = matrix[(matrix[names] == "never").all(axis=1)]
    lines += ["", "## Never a feature for any label", ""]
    for modality, part in everywhere.groupby("modality", sort=True):
        lines += [f"**{modality}** ({len(part)}): " + ", ".join(f"`{f}`" for f in part["feature"]), ""]
    lines += ["## Full matrix", "", "| Feature | Modality | Source | " + " | ".join(names) + " | Note |",
              "|---|---|---|" + "---|" * (len(names) + 1)]
    for row in matrix.itertuples():
        lines.append(f"| `{row.feature}` | {row.modality} | {row.source} | "
                     + " | ".join(getattr(row, label) for label in names) + f" | {row.note} |")
    return "\n".join(lines) + "\n"


def render_feature_sets(matrix: pd.DataFrame) -> dict[str, str]:
    out = {}
    for label in labels(matrix):
        for tier in TIERS:
            body = yaml.safe_dump({"label": label, "tier": tier, "n_features": len(tier_features(matrix, label, tier)),
                                   "features": tier_features(matrix, label, tier)}, sort_keys=False, width=120)
            out[f"{label}_{tier}.yaml"] = GENERATED_HEADER + body
    return out


def generate(matrix_path: Path = MATRIX_PATH, doc_path: Path = DOC_PATH, sets_dir: Path = FEATURE_SETS_DIR) -> list[Path]:
    """Write the Markdown table and the feature-set files from the matrix."""
    matrix = load_matrix(matrix_path)
    written = []
    doc_path.write_text(render_markdown(matrix), encoding="utf-8", newline="\n")
    written.append(doc_path)
    sets_dir.mkdir(parents=True, exist_ok=True)
    wanted = render_feature_sets(matrix)
    for stale in sets_dir.glob("*.yaml"):
        if stale.name not in wanted:
            stale.unlink()
    for name, text in wanted.items():
        (sets_dir / name).write_text(text, encoding="utf-8", newline="\n")
        written.append(sets_dir / name)
    return written


def out_of_sync(matrix_path: Path = MATRIX_PATH, doc_path: Path = DOC_PATH, sets_dir: Path = FEATURE_SETS_DIR) -> list[str]:
    """Names of generated files that do not match the matrix (empty when everything is in sync)."""
    matrix = load_matrix(matrix_path)
    expected = {doc_path: render_markdown(matrix)}
    expected.update({sets_dir / name: text for name, text in render_feature_sets(matrix).items()})
    stale = [p.name for p, text in expected.items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
    stale += [p.name for p in sets_dir.glob("*.yaml") if p not in expected] if sets_dir.is_dir() else []
    return sorted(stale)


if __name__ == "__main__":
    for path in generate():
        print(path)
