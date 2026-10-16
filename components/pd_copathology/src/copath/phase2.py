"""Phase 2: analytic cohort, labels, leakage check and frozen split.

Run it with::

    python -m copath.phase2

Reads the PPMI download in place (``PPMI_DATA_ROOT``), writes participant-level
outputs only to the git-ignored ``data/processed`` and ``data/splits`` folders
and aggregate reports to ``reports/phase2``. No model is trained here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .data import cohort as cohort_mod
from .data import split as split_mod
from .data.load import COMPONENT_DIR, REPO_DIR, DataRootError, resolve_data_root
from .data.medications import DrugRules
from .data.merge import KEY, JoinError
from .data.privacy import safe_pct, scan_reports_for_ids, suppress
from .data.provenance import error_record, git_state, package_versions
from .data.sources import SourceError, SourceLoader
from .features import leakage_guard
from .targets import builders

PHASE2_VERSION = "1.1.0"
ANALYTIC_NAME = "analytic_bl_v1"
THRESHOLD = 5


class PrivacyCheckError(RuntimeError):
    """A participant identifier was found in a generated report."""


@dataclass
class Paths:
    config: Path = COMPONENT_DIR / "configs" / "phase2.yaml"
    drug_classes: Path = COMPONENT_DIR / "configs" / "drug_classes.yaml"
    leakage_matrix: Path = leakage_guard.MATRIX_PATH
    feature_sets: Path = leakage_guard.FEATURE_SETS_DIR
    leakage_doc: Path = leakage_guard.DOC_PATH
    targets: Path = COMPONENT_DIR / "targets"
    frozen: Path = COMPONENT_DIR / "configs" / "frozen"
    processed: Path = COMPONENT_DIR / "data" / "processed"
    splits: Path = COMPONENT_DIR / "data" / "splits"
    reports: Path = COMPONENT_DIR / "reports" / "phase2"
    audit_manifest: Path = COMPONENT_DIR / "reports" / "audit" / "audit_manifest.json"
    registry: Path = COMPONENT_DIR / "experiments" / "registry.csv"


@dataclass
class State:
    """What a run has produced so far, and which step it is in (for error reports)."""

    step: str = "start"
    written: list[Path] = field(default_factory=list)


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def S(n: int) -> int | str:
    return suppress(int(n), THRESHOLD)


def part_of(part: int, whole: int) -> int | str:
    """A count shown next to its total: withheld when the remainder would be a small cell."""
    if 0 < whole - part < THRESHOLD and whole >= THRESHOLD:
        return "suppressed"
    return S(part)


def P(num: int, den: int) -> float | str:
    return safe_pct(int(num), int(den), THRESHOLD)


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(1024 * 1024):
            sha.update(block)
    return sha.hexdigest()


def _groups(frame: pd.DataFrame, cohorts: list[str]) -> list[tuple[str, pd.Series]]:
    return [("ALL", pd.Series(True, index=frame.index))] + [(c, frame["cohort"] == c) for c in cohorts]


def label_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c.startswith(builders.LABEL_PREFIX)]


# --------------------------------------------------------------------------
# aggregate reports
# --------------------------------------------------------------------------

def label_prevalence(frame: pd.DataFrame, cohorts: list[str], dev: pd.Series) -> pd.DataFrame:
    rows = []
    for name, part in (("all", pd.Series(True, index=frame.index)), ("development", dev), ("test", ~dev)):
        for cohort, members in _groups(frame, cohorts):
            mask = part & members
            for column in label_columns(frame):
                values = frame.loc[mask, column]
                n, eligible, positive = len(values), int(values.notna().sum()), int((values == 1).sum())
                rows.append({
                    "label": column[len(builders.LABEL_PREFIX):], "split": name, "cohort": cohort,
                    "n_participants": S(n), "n_eligible": part_of(eligible, n), "n_masked": part_of(n - eligible, n),
                    "n_positive": part_of(positive, eligible), "n_negative": part_of(eligible - positive, eligible),
                    "pct_positive_of_eligible": P(positive, eligible),
                })
    return pd.DataFrame(rows)


def label_cooccurrence(frame: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    rows = []
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            a, b = frame[builders.label_column(first)], frame[builders.label_column(second)]
            both = a.notna() & b.notna()
            cells = {f"n_{x}{y}": int((both & (a == x) & (b == y)).sum()) for x in (1, 0) for y in (1, 0)}
            small = any(0 < v < THRESHOLD for v in cells.values())
            rows.append({"label_a": first, "label_b": second, "n_both_eligible": S(int(both.sum())),
                         # one small cell would be recoverable from the others, so all four are withheld together
                         **{k: ("suppressed" if small else v) for k, v in cells.items()},
                         "note": "a=1/0 is the first digit, b=1/0 the second"})
    return pd.DataFrame(rows)


def split_balance(frame: pd.DataFrame, indicators: pd.DataFrame, dev: pd.Series, folds: pd.Series) -> pd.DataFrame:
    rows = []
    table = indicators.copy()
    for column in label_columns(frame):
        table[f"eligible_{column}"] = frame[column].notna()
        table[f"positive_{column}"] = frame[column] == 1
    parts = [("development", dev), ("test", ~dev)] + [(f"development fold {k}", dev & (folds == k)) for k in sorted(folds.dropna().unique())]
    for column in table.columns:
        overall = P(int(table[column].sum()), len(table))
        for name, mask in parts:
            n = int(mask.sum())
            rows.append({"indicator": column, "part": name, "n_in_part": S(n),
                         "n_with_indicator": part_of(int((table[column] & mask).sum()), n),
                         "pct_with_indicator": P(int((table[column] & mask).sum()), n),
                         "pct_with_indicator_overall": overall})
    return pd.DataFrame(rows)


def feature_set_summary(matrix: pd.DataFrame, available: list[str]) -> pd.DataFrame:
    rows, present = [], set(available)
    for label in leakage_guard.labels(matrix):
        for tier in leakage_guard.TIERS:
            chosen = matrix[matrix["feature"].isin(leakage_guard.tier_features(matrix, label, tier))]
            for modality, part in [("ALL", chosen)] + list(chosen.groupby("modality", sort=True)):
                rows.append({"label": label, "tier": tier, "modality": modality, "n_features_in_matrix": len(part),
                             "n_features_in_dataset": int(part["feature"].isin(present).sum())})
    return pd.DataFrame(rows)


def vascular_prevalence(frame: pd.DataFrame, cohorts: list[str]) -> pd.DataFrame:
    rows = []
    flags = ["htn_bp", "htn_med_definite", "htn_med_conditional", "dm_med", "dyslipid_med", "htn_evaluable",
             "comp_htn", "comp_dm", "comp_dyslip", "med_record_any"]
    for cohort, members in _groups(frame, cohorts):
        part = frame[members]
        n = len(part)

        def add(measure: str, value: str, count: int, of: int = n) -> None:
            rows.append({"cohort": cohort, "measure": measure, "value": value, "n_in_group": S(of),
                         "n_participants": part_of(count, of), "pct_of_group": P(count, of)})

        for flag in flags:
            add(flag, "yes", int((part[flag] == 1).sum()))
        add("htn_bp", "not measured", int(part["htn_bp"].isna().sum()))
        for source in ("BL", "SC_fallback", "missing"):
            add("bp_source", source, int((part["bp_source"] == source).sum()))
        for k in range(4):
            add("vascular_component_count", str(k), int((part["vascular_component_count"] == k).sum()))
        no_record = part[~part["med_record_any"].astype(bool)]
        for name in ("vascular_v1", "vascular_v2"):
            values = no_record[builders.label_column(name)]
            for text, count in (("positive", int((values == 1).sum())), ("negative", int((values == 0).sum())),
                                ("masked", int(values.isna().sum()))):
                add(f"no medication-log record, by {name}", text, count, len(no_record))
    return pd.DataFrame(rows)


def construct_check(frame: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Plausibility summaries on the development set. Never used to redefine a label."""
    names = cfg.get("construct_check") or {}
    rows = []

    def summary(check: str, label: str, variable: str | None, kind: str) -> None:
        if not variable or variable not in frame.columns:
            rows.append({"check": check, "label": label, "status": "variable not in the dataset", "n_participants": "",
                         "mean_value": "", "median_value": "", "pct_value": ""})
            return
        for status, text in ((1, "positive"), (0, "negative")):
            values = pd.to_numeric(frame.loc[frame[builders.label_column(label)] == status, variable], errors="coerce").dropna()
            small = len(values) < THRESHOLD
            row = {"check": check, "label": label, "status": text, "n_participants": S(len(values)),
                   "mean_value": "", "median_value": "", "pct_value": ""}
            if not small and kind == "numeric":
                row["mean_value"], row["median_value"] = round(float(values.mean()), 3), round(float(values.median()), 3)
            elif not small:
                row["pct_value"] = P(int((values >= 1).sum()), len(values))
            rows.append(row)

    summary("MoCA by AD-like status", "ad_like_v1", names.get("moca"), "numeric")
    summary("APOE e4 carriers (%) by AD-like status", "ad_like_v1", names.get("apoe_e4"), "carrier")
    summary("age by AD-like status", "ad_like_v1", names.get("age"), "numeric")
    summary("age by vascular status", "vascular_v1", names.get("age"), "numeric")
    summary("WM hypointensity volume by vascular status", "vascular_v1", names.get("wm_hypointensities"), "numeric")
    out = pd.DataFrame(rows)
    out.insert(0, "computed_on", "development set only")
    return out


def cohort_flow_md(observed: dict, flow: list[dict], notes: dict, limits: dict, frame: pd.DataFrame, lumipulse_note: str) -> str:
    lines = ["# Phase 2 cohort flow", "",
             f"Aggregate only; counts below {THRESHOLD} are shown as `<{THRESHOLD}`. One row per participant is "
             "asserted before and after every join; no join may add a participant.", "",
             "## Baseline universe (drift guard passed)", "",
             "| Cohort | Participants |", "|---|---|"]
    lines += [f"| {name} | {S(count)} |" for name, count in sorted(observed.items(), key=lambda kv: (kv[0] != "ALL", kv[0]))]
    lines += ["", "## Joins", "", "| Step | Before | After | Source participants | Matched in universe | Columns added |",
              "|---|---|---|---|---|---|"]
    for row in flow:
        lines.append(f"| {row['step']} | {row['n_participants_before']} | {row['n_participants_after']} "
                     f"| {S(row['n_source_participants'])} | {S(row['n_matched_in_universe'])} | {row['n_columns_added']} |")
    lines += ["", f"Final analytic table: {len(frame)} participants x {len(frame.columns)} columns.", "",
              "## Processing notes", "", "| Item | Count |", "|---|---|"]
    lines += [f"| {name} | {S(count)} |" for name, count in notes.items()]
    lines += ["", "## AD-like censored measurements (Elecsys, baseline)", "",
              "The curated cut discards out-of-range Elecsys values and keeps only limit flags. A flagged value is "
              "replaced by the limit itself: a **boundary substitution for a censored assay measurement, not the "
              "participant's true value** (a flagged high ABeta42 could truly be well above the limit). "
              "`ad_like_v1_censored` marks these participants; `ad_like_v1_uncensored` masks them.", "",
              "| Item | Participants |", "|---|---|"]
    lines += [f"| {name} | {S(count)} |" for name, count in limits.items()]
    lines += ["", "## Lumipulse threshold", "", lumipulse_note, ""]
    return "\n".join(lines) + "\n"


def drift_report_md(expected: dict, observed: dict) -> str:
    lines = ["# Phase 2 drift report", "",
             "**The baseline universe differs from the frozen universe. Nothing was built.**", "",
             "| Cohort | Frozen | Observed now |", "|---|---|---|"]
    for name in sorted(set(expected) | set(observed), key=lambda n: (n != "ALL", n)):
        lines.append(f"| {name} | {expected.get(name, 0)} | {S(observed.get(name, 0))} |")
    lines += ["", "Check that the same PPMI download (curated data cut file) is in place. If the data release has "
              "changed on purpose, the frozen counts in `configs/phase2.yaml` and the decisions document must be "
              "updated together, deliberately.", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def _write_csv(frame: pd.DataFrame, path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
    state.written.append(path)


def _write_text(text: str, path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    state.written.append(path)


GMM_FILE = "lumipulse_gmm_v1.json"
MANIFEST_FILE = "phase2_manifest.json"
GMM_HASH_KEY = "lumipulse_gmm_sha256"
REFREEZE_HINT = "Run `python -m copath.phase2 --refreeze` to refit and record it (allowed only before any Phase 3 run)."


def verify_frozen_gmm(target: Path, manifest_path: Path) -> None:
    """A normal run needs the frozen GMM file and a manifest hash that matches it; nothing is regenerated.

    Raises :class:`copath.data.split.SplitError` (never mentioning data) when the file is missing, when the
    manifest has no recorded hash (written before this check existed) or when the two differ.
    """
    if not Path(target).is_file():
        raise split_mod.SplitError(f"the frozen Lumipulse threshold file {GMM_FILE} is missing; it is not regenerated "
                                   f"silently. {REFREEZE_HINT}")
    recorded = None
    if Path(manifest_path).is_file():
        try:
            recorded = json.loads(Path(manifest_path).read_text(encoding="utf-8")).get(GMM_HASH_KEY)
        except ValueError:
            recorded = None
    if not recorded:
        raise split_mod.SplitError(f"{MANIFEST_FILE} has no recorded hash of {GMM_FILE} (manifests written before this "
                                   f"check do not). {REFREEZE_HINT}")
    if recorded != _sha256(target):
        raise split_mod.SplitError(f"{GMM_FILE} does not match the hash recorded in {MANIFEST_FILE}; the frozen "
                                   f"threshold was changed or replaced. {REFREEZE_HINT}")


def _lumipulse(frame: pd.DataFrame, dev: pd.Series, cfg: dict, paths: Paths, refreeze: bool,
               initial: bool = False) -> tuple[pd.Series, str, str]:
    """Fit the mixture on development participants only, freeze it, apply it to everyone.

    Returns the label, a report note and the SHA-256 of the frozen file ("not fitted" if there is none).
    ``refreeze`` refits and overwrites the file. ``initial`` is the very first freeze (no split exists yet): the
    file is created. In every other case the file must already exist and match the manifest (see
    :func:`verify_frozen_gmm`).
    """
    column = builders.label_column("ad_like_lumipulse_v1")
    gmm = cfg.get("lumipulse_gmm") or {}
    eligible_dev = frame.loc[dev, "lumi_ratio_4240"].dropna()
    if len(eligible_dev) < int(gmm.get("min_development_n", 30)):
        return pd.Series(np.nan, index=frame.index, name=column), (
            "Not fitted: too few eligible development-set participants. The Lumipulse label is masked for everyone."), "not fitted"
    target = paths.frozen / GMM_FILE
    create = refreeze or (initial and not target.is_file())
    if not create:
        verify_frozen_gmm(target, paths.reports / MANIFEST_FILE)
    fitted = builders.fit_lumipulse_threshold(eligible_dev, int(cfg["seed"]), int(gmm.get("n_init", 5)),
                                              int(gmm.get("min_development_n", 30)))
    if create:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(fitted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        frozen = fitted
    else:
        frozen = json.loads(target.read_text(encoding="utf-8"))
        if not np.isclose(frozen["threshold_ratio"], fitted["threshold_ratio"], rtol=1e-9):
            raise split_mod.SplitError("the Lumipulse threshold fitted now differs from the frozen one; nothing was "
                                       "overwritten (use --refreeze only if it must be replaced)")
    note = (f"2-component Gaussian mixture on log(ABeta42/ABeta40), fitted on {S(frozen['n_development_participants'])} "
            f"eligible development-set participants only; threshold ratio = {frozen['threshold_ratio']:.5f}; "
            f"positive = ratio below the threshold. Frozen in `configs/frozen/{GMM_FILE}` (kept local, hash recorded in "
            "the Phase 2 manifest) and applied unchanged to the test set.")
    return builders.ad_like_lumipulse(frame["lumi_ratio_4240"], frozen).rename(column), note, _sha256(target)


def registry_has_runs(path: Path) -> bool:
    """True when the experiment registry holds at least one run (a split may then never be replaced)."""
    path = Path(path)
    if not path.is_file():
        return False
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return len(lines) > 1


def run_phase2(data_root: Path, paths: Paths | None = None, refreeze: bool = False, state: State | None = None) -> dict:
    """Build the cohort, labels and split. Returns a small summary; raises on any violated rule."""
    paths, state = paths or Paths(), state or State()
    if refreeze and registry_has_runs(paths.registry):
        raise split_mod.SplitError("--refreeze refused: experiments/registry.csv already holds Phase 3 runs. The split "
                                   "was re-frozen once before training and can never be replaced again.")
    warnings.simplefilter("ignore")  # library warnings can quote cell values
    cfg = yaml.safe_load(Path(paths.config).read_text(encoding="utf-8"))
    seed = int(cfg["seed"])

    state.step = "target cards"
    cards = builders.load_cards(paths.targets)
    builders.ad_like_parameters(cards["ad_like_v1"])  # stops here if the card lacks the formula or the cut-off
    parents = builders.variant_parents(cards)

    state.step = "leakage matrix"
    matrix = leakage_guard.load_matrix(paths.leakage_matrix)
    stale = leakage_guard.out_of_sync(paths.leakage_matrix, paths.leakage_doc, paths.feature_sets)
    if stale:
        raise leakage_guard.LeakageError(
            f"generated leakage files are out of date ({len(stale)}); run `python -m copath.features.leakage_guard`")
    missing_cards = sorted(set(cards) - set(leakage_guard.labels(matrix)))
    if missing_cards:
        raise leakage_guard.LeakageError(f"labels without a leakage-matrix column: {missing_cards}")
    names = leakage_guard.labels(matrix)
    feature_columns = set(matrix.loc[(matrix[names] != "never").any(axis=1), "feature"])

    state.step = "drug rules"
    rules = DrugRules.from_yaml(paths.drug_classes)

    state.step = "backbone: curated cut"
    loader = SourceLoader(Path(data_root), list(cfg.get("forbidden_tables") or []))
    base = cohort_mod.backbone(loader, cfg)
    _log(f"Curated cut read: {len(base)} baseline rows.")

    state.step = "drift guard"
    paths.reports.mkdir(parents=True, exist_ok=True)
    drift_path = paths.reports / "drift_report.md"
    try:
        observed = cohort_mod.check_drift(base, cfg)
    except cohort_mod.DriftError as drift:
        _write_text(drift_report_md(drift.expected, drift.observed), drift_path, state)
        raise
    drift_path.unlink(missing_ok=True)

    state.step = "cohort build"
    frame, flow, notes = cohort_mod.build(loader, cfg, cards, rules, feature_columns, base)
    _log("Sources joined; one row per participant verified.")

    state.step = "labels"
    frame, limits = cohort_mod.add_labels(frame, cards)

    state.step = "frozen split"
    cohorts = [c for c in cfg["universe"]["cohort_codes"].values() if (frame["cohort"] == c).any()]
    primary = [builders.label_column(name) for name in builders.PRIMARY_LABELS]
    indicators = split_mod.stratification_indicators(frame, "cohort", cohorts, primary)
    spec = cfg.get("split") or {}
    initial_freeze = not (paths.splits / f"{split_mod.SPLIT_NAME}.json").is_file()
    split = split_mod.make_split(frame[KEY], indicators, seed, float(spec.get("test_fraction", 0.2)),
                                 int(spec.get("n_folds", 5)), int(spec.get("min_stratum", 10)))
    metadata = split_mod.split_metadata(split, seed, float(spec.get("test_fraction", 0.2)), int(spec.get("n_folds", 5)))
    split_mod.freeze_split(split, metadata, paths.splits, refreeze)
    dev = frame[KEY].astype(str).isin(set(split["dev_ids"]))
    folds = frame[KEY].astype(str).map(dict(zip(split["folds"][KEY], split["folds"]["fold"])))
    _log(f"Split frozen: {metadata['n_development']} development, {metadata['n_test']} test.")

    state.step = "Lumipulse threshold (development set only)"
    lumipulse, lumipulse_note, gmm_sha = _lumipulse(frame, dev, cfg, paths, refreeze, initial_freeze)
    frame[lumipulse.name] = lumipulse.to_numpy()

    state.step = "leakage check"
    leakage_guard.assert_columns_classified(matrix, list(frame.columns))
    for label in names:
        for tier in leakage_guard.TIERS:
            leakage_guard.assert_allowed(leakage_guard.features_for(matrix, label, tier, list(frame.columns)),
                                         matrix, label, tier, parents)

    state.step = "participant-level outputs"
    paths.processed.mkdir(parents=True, exist_ok=True)
    full, dev_file = paths.processed / f"{ANALYTIC_NAME}.parquet", paths.processed / f"{ANALYTIC_NAME}_dev.parquet"
    frame.to_parquet(full, index=False)
    frame[dev].assign(fold=folds[dev].astype(int)).to_parquet(dev_file, index=False)
    hashes = {p.name: _sha256(p) for p in (full, dev_file)}
    for p in (full, dev_file):
        p.with_suffix(".sha256").write_text(f"{hashes[p.name]}  {p.name}\n", encoding="utf-8")

    state.step = "aggregate reports"
    r = paths.reports
    _write_text(cohort_flow_md(observed, flow, notes, limits, frame, lumipulse_note), r / "cohort_flow.md", state)
    _write_csv(label_prevalence(frame, cohorts, dev), r / "label_prevalence_by_cohort.csv", state)
    _write_csv(label_cooccurrence(frame, [n for n in cards]), r / "label_cooccurrence.csv", state)
    _write_csv(split_balance(frame, indicators, dev, folds), r / "split_balance.csv", state)
    _write_csv(feature_set_summary(matrix, list(frame.columns)), r / "feature_set_summary.csv", state)
    _write_csv(vascular_prevalence(frame, cohorts), r / "vascular_component_prevalence.csv", state)
    _write_csv(construct_check(frame[dev], cfg), r / "construct_check.csv", state)

    state.step = "manifest"
    config_files = [paths.config, paths.drug_classes, paths.leakage_matrix] + sorted(Path(paths.targets).glob("*.yaml"))
    manifest = {
        "phase2_version": PHASE2_VERSION, "seed": seed, "git": git_state(REPO_DIR),
        "python_version": platform.python_version(), "package_versions": package_versions(),
        "phase1_audit_manifest_sha256": _sha256(paths.audit_manifest) if Path(paths.audit_manifest).is_file() else "not found",
        "phase2_config_sha256": hashlib.sha256("".join(_sha256(p) for p in config_files).encode()).hexdigest(),
        "config_files": {p.name: _sha256(p) for p in config_files},
        GMM_HASH_KEY: gmm_sha, "source_tables": loader.used, "universe": observed,
        "outputs": {"analytic_sha256": hashes, "n_participants": int(len(frame)), "n_columns": int(len(frame.columns)),
                    "split": metadata},
    }
    _write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", r / MANIFEST_FILE, state)

    state.step = "report privacy self-check"
    findings = scan_reports_for_ids(r, loader.seen_ids)
    if findings:
        for path in state.written:
            path.unlink(missing_ok=True)
        detail = "; ".join(f"{f['file']} [{f['location']}] x{f['n_matches']}" for f in findings[:20])
        raise PrivacyCheckError("Privacy self-check failed: a participant identifier appears in a Phase 2 report. "
                                f"The reports were deleted. Locations: {detail}")
    return {"n_participants": int(len(frame)), "n_development": metadata["n_development"], "n_test": metadata["n_test"],
            "analytic": full, "reports": r, "n_identifiers_checked": len(loader.seen_ids)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m copath.phase2",
                                     description="Phase 2: cohort, labels, leakage check and frozen split. No modelling.")
    parser.add_argument("--data-root", help="Raw PPMI directory. Default: PPMI_DATA_ROOT from the environment or .env.")
    parser.add_argument("--refreeze", action="store_true",
                        help="Replace an existing frozen split and Lumipulse threshold instead of verifying against them.")
    args = parser.parse_args(argv)
    state = State()
    try:
        result = run_phase2(resolve_data_root(args.data_root), refreeze=args.refreeze, state=state)
    except DataRootError as exc:
        _log(f"Configuration error: {exc}")
        return 2
    except cohort_mod.DriftError:
        _log("DRIFT: the baseline universe differs from the frozen universe. Nothing was built. "
             "See reports/phase2/drift_report.md.")
        return 4
    except PrivacyCheckError as exc:
        _log(str(exc))
        return 3
    except (builders.CardError, leakage_guard.LeakageError, split_mod.SplitError, JoinError, SourceError) as exc:
        _log(f"Phase 2 stopped at step '{state.step}': {exc}")  # these messages are written by this package; no data
        return 1
    except Exception as exc:  # noqa: BLE001 - never print a message that may quote data
        record = error_record("", "", state.step, exc)
        _log(f"Phase 2 failed at step '{state.step}': {record['exception_type']} at {record['location'] or 'unknown location'}")
        return 1
    _log(f"Phase 2 finished: {result['n_participants']} participants "
         f"({result['n_development']} development, {result['n_test']} test).")
    _log(f"Privacy self-check passed ({result['n_identifiers_checked']} identifiers checked).")
    _log(f"Participant-level outputs (git-ignored): {result['analytic'].parent} and data/splits")
    _log(f"Aggregate reports: {result['reports']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
