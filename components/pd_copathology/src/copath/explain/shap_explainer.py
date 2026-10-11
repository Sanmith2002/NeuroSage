"""SHAP attributions for the uncalibrated predictive model, and ranking stability.

TreeExplainer is used for the tree models and LinearExplainer for logistic
regression. The space the SHAP values live in differs between estimators
(log-odds for a linear or boosted margin, probability for a random forest),
so it is never assumed: :func:`explain` checks which model output the values
add up to and records that. Sigmoid calibration is monotonic, so it does not
change feature rankings.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from ..evaluation.metrics import logit

EXPLAINERS = {"lr_l2": "LinearExplainer", "lr_enet": "LinearExplainer", "rf": "TreeExplainer", "xgb": "TreeExplainer", "hgb": "TreeExplainer"}


def explain(model: str, pipeline, X_background: pd.DataFrame, X: pd.DataFrame) -> dict:
    """SHAP values (rows x features) of a fitted candidate pipeline for the rows of ``X``.

    Returns ``values``, ``explainer``, ``space`` (verified against the model's
    own output) and ``additivity_error``.
    """
    import shap

    estimator = pipeline.named_steps["model"]
    prep = pipeline[:-1] if len(pipeline.steps) > 1 else None
    data = np.asarray(prep.transform(X) if prep is not None else X, dtype=float)
    if model in ("lr_l2", "lr_enet"):
        background = np.asarray(prep.transform(X_background), dtype=float)
        explainer = shap.LinearExplainer(estimator, shap.maskers.Independent(background, max_samples=min(len(background), 1000)))
        values, base = explainer.shap_values(data), explainer.expected_value
    else:
        explainer = shap.TreeExplainer(estimator)
        values, base = explainer.shap_values(data, check_additivity=False), explainer.expected_value
    if isinstance(values, list):  # one array per class: keep the positive class
        values = values[-1]
    values, base = np.asarray(values), np.atleast_1d(np.asarray(base, dtype=float))
    if values.ndim == 3:  # (rows, features, classes): keep the positive class
        values = values[:, :, -1]
    total = values.sum(axis=1) + base[-1]
    probability = estimator.predict_proba(data)[:, 1]
    if hasattr(estimator, "decision_function"):
        margin = np.asarray(estimator.decision_function(data), dtype=float)
    elif model == "xgb":
        margin = np.asarray(estimator.predict(data, output_margin=True), dtype=float)
    else:
        margin = logit(probability)
    errors = {"log-odds (raw margin of the uncalibrated model)": float(np.max(np.abs(total - margin))),
              "probability (of the uncalibrated model)": float(np.max(np.abs(total - probability)))}
    space, error = min(errors.items(), key=lambda kv: kv[1])
    if error > 1e-2:
        space = "not verified (SHAP values do not add up to the margin or to the probability)"
    return {"values": values, "explainer": EXPLAINERS[model], "space": space, "additivity_error": error}


def mean_abs(values: np.ndarray, features: list[str]) -> pd.Series:
    return pd.Series(np.abs(values).mean(axis=0), index=features)


def stability(rankings: list[pd.Series], top_k: int = 10) -> dict:
    """Mean pairwise top-k Jaccard and Kendall tau between importance vectors over the same features."""
    if len(rankings) < 2:
        return {"n_rankings": len(rankings), "mean_jaccard": float("nan"), "mean_kendall_tau": float("nan")}
    tops = [set(r.sort_values(ascending=False, kind="mergesort").index[:top_k]) for r in rankings]
    jaccard, tau = [], []
    for i, j in combinations(range(len(rankings)), 2):
        jaccard.append(len(tops[i] & tops[j]) / len(tops[i] | tops[j]))
        value = kendalltau(rankings[i].to_numpy(), rankings[j].reindex(rankings[i].index).to_numpy()).statistic
        if np.isfinite(value):
            tau.append(float(value))
    return {"n_rankings": len(rankings), "mean_jaccard": float(np.mean(jaccard)),
            "mean_kendall_tau": float(np.mean(tau)) if tau else float("nan")}


def dependence(values: pd.Series, shap_values: np.ndarray, bins: int = 10, min_n: int = 5) -> pd.DataFrame:
    """Binned means only: mean feature value and mean SHAP per quantile bin; bins below ``min_n`` are dropped."""
    frame = pd.DataFrame({"x": pd.to_numeric(values, errors="coerce").to_numpy(), "shap": shap_values}).dropna()
    if frame.empty:
        return pd.DataFrame(columns=["bin", "n_in_bin", "mean_feature_value", "mean_shap"])
    if frame["x"].nunique() <= bins:
        frame["bin"] = frame["x"].rank(method="dense").astype(int)
    else:
        frame["bin"] = pd.qcut(frame["x"], bins, labels=False, duplicates="drop") + 1
    out = frame.groupby("bin").agg(n_in_bin=("x", "size"), mean_feature_value=("x", "mean"), mean_shap=("shap", "mean"))
    return out[out["n_in_bin"] >= min_n].reset_index()
