"""Participant-level joins with hard guarantees.

Every table is brought to one row per participant before it is joined, and a
join can never add rows or participants to the backbone.
"""

from __future__ import annotations

import pandas as pd

KEY = "PATNO"


class JoinError(RuntimeError):
    """A join would break the one-row-per-participant rule."""


def assert_one_row_per_participant(frame: pd.DataFrame, what: str, key: str = KEY) -> None:
    if key not in frame.columns:
        raise JoinError(f"{what}: key column {key} is missing")
    if frame[key].isna().any() or (frame[key].astype(str) == "").any():
        raise JoinError(f"{what}: blank participant key")
    if frame[key].duplicated().any():
        raise JoinError(f"{what}: more than one row per participant")


def left_join(base: pd.DataFrame, other: pd.DataFrame, name: str, flow: list[dict], key: str = KEY) -> pd.DataFrame:
    """Left-join a participant-level table onto the backbone.

    Asserts key uniqueness on both sides before the join, and that the result
    has exactly the backbone's rows and participants afterwards.
    """
    assert_one_row_per_participant(base, f"backbone before {name}", key)
    assert_one_row_per_participant(other, f"{name} before join", key)
    clash = sorted((set(base.columns) & set(other.columns)) - {key})
    if clash:
        raise JoinError(f"{name}: column names already present in the backbone: {clash}")
    n_before, ids_before = len(base), set(base[key])
    out = base.merge(other, on=key, how="left", validate="one_to_one")
    if len(out) != n_before or set(out[key]) != ids_before:
        raise JoinError(f"{name}: the join changed the participant set")
    assert_one_row_per_participant(out, f"backbone after {name}", key)
    flow.append({
        "step": name, "n_participants_before": n_before, "n_participants_after": len(out),
        "n_source_participants": len(other), "n_matched_in_universe": int(other[key].isin(ids_before).sum()),
        "n_columns_added": len(other.columns) - 1,
    })
    return out
