"""Frozen participant-level development/test split and outer folds.

The split is built once with iterative stratification (Sechidis et al. 2011)
on cohort and on the availability and positive indicators of the three
primary labels, then frozen: a later run must reproduce it exactly or fail.
Test-set identifiers and features can only be loaded in an explicit
final-evaluation mode.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

KEY = "PATNO"
FINAL_EVALUATION_ENV = "COPATH_FINAL_EVALUATION"
SPLIT_NAME = "split_v1"


class SplitError(RuntimeError):
    """The split cannot be built, or does not match the frozen one."""


class TestSetAccessError(PermissionError):
    """Test-set identifiers or features were requested outside final-evaluation mode."""

    __test__ = False  # not a pytest class


def iterative_stratification(indicators: np.ndarray, ratios: list[float], seed: int) -> np.ndarray:
    """Assign each row to a part so every indicator keeps its proportion in every part.

    The rarest indicator is distributed first; each of its rows goes to the
    part that still wants most of that indicator, ties going to the part that
    still wants most rows overall and then to a seeded random choice.
    """
    y = np.asarray(indicators, dtype=bool)
    n, _ = y.shape
    share = np.asarray(ratios, dtype=float) / float(np.sum(ratios))
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    want_rows = n * share
    want_label = y.sum(axis=0)[:, None] * share[None, :]
    assigned = np.full(n, -1, dtype=int)
    remaining = np.ones(n, dtype=bool)

    def place(i: int, part: int) -> None:
        assigned[i], remaining[i] = part, False
        want_label[y[i], part] -= 1
        want_rows[part] -= 1

    while remaining.any():
        counts = y[remaining].sum(axis=0)
        if counts.max() == 0:
            break
        label = int(np.argmin(np.where(counts > 0, counts, np.inf)))
        for i in order:
            if not remaining[i] or not y[i, label]:
                continue
            best = np.flatnonzero(np.isclose(want_label[label], want_label[label].max()))
            if len(best) > 1:
                best = best[np.isclose(want_rows[best], want_rows[best].max())]
            place(i, int(best[0] if len(best) == 1 else rng.choice(best)))
    for i in order:
        if remaining[i]:
            place(i, int(np.argmax(want_rows)))
    return assigned


def merge_sparse(indicators: pd.DataFrame, min_count: int) -> tuple[pd.DataFrame, list[str]]:
    """Deterministic fallback for rare strata: merge them instead of creating singletons.

    Cohorts with fewer than ``min_count`` participants are merged into one
    ``cohort_other`` indicator; any other indicator that rare is dropped, so
    those participants are stratified on their remaining indicators.
    """
    out, notes = indicators.copy(), []
    cohorts = [c for c in out.columns if c.startswith("cohort_") and c != "cohort_other"]
    rare = [c for c in cohorts if out[c].sum() < min_count]
    if rare:
        out["cohort_other"] = out[rare].any(axis=1)
        out = out.drop(columns=rare)
        notes.append(f"cohort indicators merged into cohort_other (fewer than {min_count} participants each): {', '.join(rare)}")
        if out["cohort_other"].sum() < min_count:
            notes.append("cohort_other is still rare and is kept only as a soft constraint")
    for column in [c for c in out.columns if not c.startswith("cohort_")]:
        if out[column].sum() < min_count:
            out = out.drop(columns=column)
            notes.append(f"indicator dropped from stratification (fewer than {min_count} participants): {column}")
    return out, notes


def stratification_indicators(frame: pd.DataFrame, cohort_column: str, cohorts: list[str], label_columns: list[str]) -> pd.DataFrame:
    """Cohort one-hot plus availability and positive indicators of the primary labels only."""
    out = pd.DataFrame(index=frame.index)
    for cohort in cohorts:
        out[f"cohort_{cohort}"] = frame[cohort_column] == cohort
    for column in label_columns:
        out[f"available_{column}"] = frame[column].notna()
        out[f"positive_{column}"] = frame[column] == 1
    return out


def make_split(ids: pd.Series, indicators: pd.DataFrame, seed: int, test_fraction: float = 0.2, n_folds: int = 5,
               min_stratum: int = 10) -> dict:
    """Development/test split and outer folds for the development set."""
    order = np.argsort(ids.astype(str).to_numpy(), kind="mergesort")  # independent of input row order
    ids = ids.astype(str).to_numpy()[order]
    used, notes = merge_sparse(indicators.iloc[order].reset_index(drop=True), min_stratum)
    part = iterative_stratification(used.to_numpy(), [1 - test_fraction, test_fraction], seed)
    dev = part == 0
    fold_used, fold_notes = merge_sparse(used[dev].reset_index(drop=True), min_stratum)
    folds = iterative_stratification(fold_used.to_numpy(), [1.0] * n_folds, seed + 1)
    dev_ids, test_ids = ids[dev], ids[~dev]
    if set(dev_ids) & set(test_ids) or len(set(ids)) != len(ids):
        raise SplitError("a participant would be in both the development and the test set")
    return {
        "dev_ids": dev_ids.tolist(), "test_ids": test_ids.tolist(),
        "folds": pd.DataFrame({KEY: dev_ids, "fold": folds}),
        "indicators": list(used.columns), "notes": notes + [f"folds: {n}" for n in fold_notes],
    }


def _digest(values: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def split_metadata(split: dict, seed: int, test_fraction: float, n_folds: int) -> dict:
    folds = split["folds"]
    return {
        "name": SPLIT_NAME, "seed": seed, "test_fraction": test_fraction, "n_folds": n_folds,
        "n_development": len(split["dev_ids"]), "n_test": len(split["test_ids"]),
        "stratification_indicators": split["indicators"], "fallback_notes": split["notes"],
        "dev_ids_sha256": _digest(split["dev_ids"]), "test_ids_sha256": _digest(split["test_ids"]),
        "folds_sha256": _digest([f"{p}:{f}" for p, f in zip(folds[KEY], folds["fold"])]),
    }


def freeze_split(split: dict, metadata: dict, splits_dir: Path, refreeze: bool = False) -> None:
    """Write the split, or verify that it equals the one already frozen."""
    splits_dir = Path(splits_dir)
    meta_path = splits_dir / f"{SPLIT_NAME}.json"
    if meta_path.is_file() and not refreeze:
        frozen = json.loads(meta_path.read_text(encoding="utf-8"))
        same = all(frozen.get(k) == metadata[k] for k in ("dev_ids_sha256", "test_ids_sha256", "folds_sha256"))
        if not same:
            raise SplitError("the split built now differs from the frozen split; nothing was overwritten "
                             "(use --refreeze only if the frozen split must be replaced)")
        return
    splits_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({KEY: split["dev_ids"]}).to_csv(splits_dir / f"{SPLIT_NAME}_dev_ids.csv", index=False)
    pd.DataFrame({KEY: split["test_ids"]}).to_csv(splits_dir / f"{SPLIT_NAME}_test_ids.csv", index=False)
    split["folds"].to_csv(splits_dir / f"{SPLIT_NAME}_dev_folds.csv", index=False)
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# loaders for later phases, with the test-set access guard
# --------------------------------------------------------------------------

def _require_final_evaluation(final_evaluation: bool) -> None:
    if not (final_evaluation and os.environ.get(FINAL_EVALUATION_ENV) == "1"):
        raise TestSetAccessError(
            "the test set is frozen: pass final_evaluation=True and set "
            f"{FINAL_EVALUATION_ENV}=1 to load it, once, after model selection")


def load_ids(splits_dir: Path, part: str = "dev", final_evaluation: bool = False) -> list[str]:
    """Participant identifiers of the development set, or of the test set in final-evaluation mode."""
    if part not in ("dev", "test"):
        raise ValueError("part must be 'dev' or 'test'")
    if part == "test":
        _require_final_evaluation(final_evaluation)
    frame = pd.read_csv(Path(splits_dir) / f"{SPLIT_NAME}_{part}_ids.csv", dtype=str)
    return frame[KEY].tolist()


def load_folds(splits_dir: Path) -> pd.DataFrame:
    return pd.read_csv(Path(splits_dir) / f"{SPLIT_NAME}_dev_folds.csv", dtype={KEY: str})


def load_analytic(processed_dir: Path, splits_dir: Path, part: str = "dev", final_evaluation: bool = False,
                  name: str = "analytic_bl_v1") -> pd.DataFrame:
    """Analytic rows of the development set (default) or, in final-evaluation mode, of the test set.

    Training code should call this and never read the full parquet directly:
    the development file contains no test participant at all.
    """
    if part == "dev":
        return pd.read_parquet(Path(processed_dir) / f"{name}_dev.parquet")
    ids = set(load_ids(splits_dir, "test", final_evaluation))
    frame = pd.read_parquet(Path(processed_dir) / f"{name}.parquet")
    return frame[frame[KEY].astype(str).isin(ids)].reset_index(drop=True)
