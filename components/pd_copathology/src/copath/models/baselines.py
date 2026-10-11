"""Baselines and the missingness-only leakage check. None of them is tuned.

    b0a          prevalence: a constant prediction equal to the training prevalence
    b0b          logistic regression on age and sex only (the floor every candidate must beat on AUPRC)
    missingness  logistic regression on missingness indicators only. A leakage
                 CHECK, never a candidate: it shows how much of a label can be
                 predicted from which measurements exist.
"""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import MissingIndicator, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASELINES = ("b0a", "b0b")
LEAKAGE_CHECK = "missingness"


def build(model: str, seed: int, cfg: dict | None = None) -> Pipeline:
    cfg = cfg or {}
    if model == "b0a":
        return Pipeline([("model", DummyClassifier(strategy="prior"))])
    if model == "b0b":
        columns = list(cfg.get("baseline_columns") or ["age", "SEX"])
        keep = ColumnTransformer([("keep", Pipeline([("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                                                     ("scale", StandardScaler())]), columns)], remainder="drop")
        return Pipeline([("columns", keep), ("model", LogisticRegression(max_iter=1000, random_state=seed))])
    if model == LEAKAGE_CHECK:
        return Pipeline([("indicators", MissingIndicator(features="all")),
                         ("model", LogisticRegression(max_iter=1000, random_state=seed))])
    raise ValueError(f"unknown baseline: {model}")
