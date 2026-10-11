"""Fold-safe preprocessing shared by every candidate model.

:class:`DropDegenerateColumns` is the first step of every candidate pipeline. It is
fitted on the training rows only and removes the columns that have fewer than two
distinct non-missing values there (all missing, or constant). At transform time it
keeps exactly the columns it kept at fit time, whatever the new rows look like.
Without it, histogram gradient boosting cannot bin such a column and stops with
"window shape cannot be larger than input array shape".
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class DropDegenerateColumns(BaseEstimator, TransformerMixin):
    """Drop columns with fewer than ``min_distinct`` distinct non-missing values in the training rows."""

    def __init__(self, min_distinct: int = 2):
        self.min_distinct = min_distinct

    def fit(self, X, y=None):
        frame = X if isinstance(X, pd.DataFrame) else pd.DataFrame(np.asarray(X))
        distinct = frame.nunique(dropna=True).to_numpy()
        self.n_features_in_ = frame.shape[1]
        self.columns_in_ = [str(c) for c in frame.columns]
        self.keep_ = distinct >= self.min_distinct
        self.kept_ = [c for c, k in zip(self.columns_in_, self.keep_) if k]
        self.dropped_ = [c for c, k in zip(self.columns_in_, self.keep_) if not k]
        if not self.keep_.any():
            raise ValueError("every column is degenerate in the training rows (fewer than two distinct non-missing values)")
        return self

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            if [str(c) for c in X.columns] == self.columns_in_:
                return X.loc[:, self.keep_]
            return X.loc[:, self.kept_]  # by name; a missing column is an error, never a silent NaN column
        return np.asarray(X)[:, self.keep_]

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.kept_, dtype=object)


def dropped_columns(fitted) -> list[str]:
    """Names of the columns the fitted pipeline's first step removed (names only; empty when there is no such step)."""
    step = getattr(fitted, "named_steps", {}).get("drop")
    return list(step.dropped_) if step is not None else []
