"""Candidate model families: pipelines and hyperparameter search spaces.

All preprocessing lives inside the scikit-learn ``Pipeline`` returned by
:func:`build`, so it is fitted on whatever training rows the pipeline is
fitted on and on nothing else. No model uses missingness indicators. Every
pipeline starts with ``drop`` (:class:`DropDegenerateColumns`), which removes the
columns that have fewer than two distinct non-missing values in the training rows.

    lr_l2    standard L2 logistic regression on all features (lbfgs); median imputation + standardisation
    lr_enet  elastic-net logistic regression (saga); median imputation + standardisation
    rf       random forest; median imputation
    xgb      XGBoost; native missing-value handling
    hgb      histogram gradient boosting; native missing-value handling
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .preprocessing import DropDegenerateColumns

CANDIDATES = ("lr_l2", "lr_enet", "rf", "xgb", "hgb")
SIMPLICITY = ("lr_l2", "lr_enet", "hgb", "rf", "xgb")  # simplest first; the last tie-breaker of the selection protocol
LINEAR = ("lr_l2", "lr_enet")


def suggest(trial, model: str) -> dict:
    """One point of the model's search space (the spaces are fixed by the Phase 3 specification)."""
    weight = trial.suggest_categorical("class_weight", ["none", "balanced"])
    if model == "lr_l2":
        return {"C": trial.suggest_float("C", 1e-3, 1e2, log=True), "class_weight": weight}
    if model == "lr_enet":
        return {"C": trial.suggest_float("C", 1e-3, 1e2, log=True), "l1_ratio": trial.suggest_float("l1_ratio", 0.0, 1.0),
                "class_weight": weight}
    if model == "rf":
        depth = trial.suggest_categorical("max_depth", [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, "none"])
        return {"n_estimators": trial.suggest_int("n_estimators", 200, 600), "max_depth": None if depth == "none" else depth,
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 20),
                "max_features": trial.suggest_categorical("max_features", ["sqrt", 0.3, 0.5]), "class_weight": weight}
    if model == "xgb":
        return {"learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                "max_depth": trial.suggest_int("max_depth", 2, 6),
                "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 10.0),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
                "n_estimators": trial.suggest_int("n_estimators", 100, 600), "class_weight": weight}
    if model == "hgb":
        return {"learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                "max_depth": trial.suggest_int("max_depth", 2, 8),
                "max_leaf_nodes": trial.suggest_int("max_leaf_nodes", 8, 63),
                "l2_regularization": trial.suggest_float("l2_regularization", 1e-3, 10.0, log=True),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 5, 50), "class_weight": weight}
    raise ValueError(f"unknown model: {model}")


def build(model: str, params: dict, y_train: np.ndarray, seed: int, cfg: dict | None = None) -> Pipeline:
    """An unfitted pipeline. ``y_train`` is used only for XGBoost's ``scale_pos_weight = neg / pos``."""
    cfg = cfg or {}
    params = dict(params)
    balanced = params.pop("class_weight", "none") == "balanced"
    weight = "balanced" if balanced else None
    n_jobs = int(cfg.get("n_jobs", -1))
    drop = ("drop", DropDegenerateColumns())
    impute = ("impute", SimpleImputer(strategy="median", keep_empty_features=True))
    if model == "lr_l2":
        spec = cfg.get("lr_l2") or {}
        estimator = LogisticRegression(solver="lbfgs", C=params["C"], class_weight=weight,
                                       max_iter=int(spec.get("max_iter", 2000)), random_state=seed)
        return Pipeline([drop, impute, ("scale", StandardScaler()), ("model", estimator)])
    if model == "lr_enet":
        spec = cfg.get("lr_enet") or {}
        estimator = LogisticRegression(solver="saga", C=params["C"], l1_ratio=params["l1_ratio"], class_weight=weight,
                                       max_iter=int(spec.get("max_iter", 2000)), tol=float(spec.get("tol", 1e-3)),
                                       random_state=seed)
        return Pipeline([drop, impute, ("scale", StandardScaler()), ("model", estimator)])
    if model == "rf":
        return Pipeline([drop, impute, ("model", RandomForestClassifier(**params, class_weight=weight, n_jobs=n_jobs, random_state=seed))])
    if model == "xgb":
        from xgboost import XGBClassifier

        y = np.asarray(y_train)
        ratio = float((y == 0).sum() / max((y == 1).sum(), 1)) if balanced else 1.0
        return Pipeline([drop, ("model", XGBClassifier(**params, scale_pos_weight=ratio, tree_method="hist", n_jobs=n_jobs,
                                                 random_state=seed, eval_metric="logloss", verbosity=0))])
    if model == "hgb":
        spec = cfg.get("hgb") or {}
        return Pipeline([drop, ("model", HistGradientBoostingClassifier(**params, class_weight=weight, early_stopping=False,
                                                                  max_iter=int(spec.get("max_iter", 300)), random_state=seed))])
    raise ValueError(f"unknown model: {model}")
