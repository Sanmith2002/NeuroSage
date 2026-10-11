"""Inner-loop hyperparameter tuning: Optuna TPE, stratified inner CV, mean log loss.

Tuning only ever sees the rows it is given (an outer-training set). Trials run
one after another with a seeded sampler so that a run is reproducible; speed
comes from multi-threaded models and, for logistic regression, from fitting
the inner folds in parallel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold

from ..models import candidates


def stratified_splits(y: np.ndarray, n_splits: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    return list(StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(np.zeros(len(y)), y))


def _fold_loss(model: str, params: dict, X: pd.DataFrame, y: np.ndarray, train: np.ndarray, valid: np.ndarray,
               seed: int, cfg: dict) -> float:
    pipeline = candidates.build(model, params, y[train], seed, cfg).fit(X.iloc[train], y[train])
    return float(log_loss(y[valid], pipeline.predict_proba(X.iloc[valid])[:, 1], labels=[0, 1]))


def tune(model: str, X: pd.DataFrame, y: np.ndarray, seed: int, cfg: dict) -> dict:
    """Best hyperparameters for ``model`` on (X, y). Returns ``params``, ``inner_log_loss`` and ``n_trials``."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    spec = cfg.get("tuning") or {}
    n_trials = int((spec.get("trials") or {}).get(model, 25))
    splits = stratified_splits(y, int(spec.get("inner_folds", 3)), seed)
    fold_jobs = len(splits) if model in candidates.LINEAR else 1  # the linear solvers are single-threaded; the tree models use every core themselves

    def objective(trial) -> float:
        params = candidates.suggest(trial, model)
        trial.set_user_attr("params", params)
        losses = Parallel(n_jobs=fold_jobs, prefer="threads")(
            delayed(_fold_loss)(model, params, X, y, train, valid, seed, cfg) for train, valid in splits)
        return float(np.mean(losses))

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials)
    return {"params": study.best_trial.user_attrs["params"], "inner_log_loss": float(study.best_value), "n_trials": n_trials}
