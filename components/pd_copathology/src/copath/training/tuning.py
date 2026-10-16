"""Inner-loop hyperparameter tuning: Optuna TPE, stratified inner CV, mean log loss.

Tuning only ever sees the rows it is given (an outer-training set). Trials run
one after another with a seeded sampler so that a run is reproducible; speed
comes from multi-threaded models and, for logistic regression, from fitting
the inner folds in parallel.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold

from ..models import candidates


class TuningError(RuntimeError):
    """Every Optuna trial failed. The message names the model and the exception types only, never data."""


def stratified_splits(y: np.ndarray, n_splits: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    return list(StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(np.zeros(len(y)), y))


def _fold_loss(model: str, params: dict, X: pd.DataFrame, y: np.ndarray, train: np.ndarray, valid: np.ndarray,
               seed: int, cfg: dict) -> float:
    pipeline = candidates.build(model, params, y[train], seed, cfg).fit(X.iloc[train], y[train])
    return float(log_loss(y[valid], pipeline.predict_proba(X.iloc[valid])[:, 1], labels=[0, 1]))


def tune(model: str, X: pd.DataFrame, y: np.ndarray, seed: int, cfg: dict) -> dict:
    """Best hyperparameters for ``model`` on (X, y).

    Returns ``params``, ``inner_log_loss``, ``n_trials``, ``n_failed_trials`` and ``trial_failures`` (exception
    type -> count). A trial that raises is counted and skipped; if no trial completes, :class:`TuningError` is raised.
    """
    import optuna

    optuna.logging.set_verbosity(optuna.logging.ERROR)  # a failed trial would otherwise print the exception text
    spec = cfg.get("tuning") or {}
    n_trials = int((spec.get("trials") or {}).get(model, 25))
    splits = stratified_splits(y, int(spec.get("inner_folds", 3)), seed)
    fold_jobs = len(splits) if model in candidates.LINEAR else 1  # the linear solvers are single-threaded; the tree models use every core themselves

    def objective(trial) -> float:
        try:
            params = candidates.suggest(trial, model)
            trial.set_user_attr("params", params)
            losses = Parallel(n_jobs=fold_jobs, prefer="threads")(
                delayed(_fold_loss)(model, params, X, y, train, valid, seed, cfg) for train, valid in splits)
            return float(np.mean(losses))
        except Exception as exc:  # noqa: BLE001 - only the type is kept
            trial.set_user_attr("error", type(exc).__name__)
            raise

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, catch=(Exception,))
    failures = Counter(t.user_attrs.get("error", "unknown") for t in study.trials if t.state != optuna.trial.TrialState.COMPLETE)
    n_failed = int(sum(failures.values()))
    if n_failed >= len(study.trials):
        raise TuningError(f"all {len(study.trials)} Optuna trials failed for model {model} "
                          f"(exception types: {', '.join(f'{k} x{v}' for k, v in sorted(failures.items()))})")
    return {"params": study.best_trial.user_attrs["params"], "inner_log_loss": float(study.best_value), "n_trials": n_trials,
            "n_failed_trials": n_failed, "trial_failures": dict(failures)}
