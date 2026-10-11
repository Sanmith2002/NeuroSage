"""Nested cross-validation on the frozen outer folds.

For one label, one feature set and one model family, each outer fold does,
using its training rows only:

1. tune the hyperparameters (inner stratified CV), unless they are supplied;
2. fit the pipeline (preprocessing included) -> uncalibrated test predictions;
3. fit the calibrated model (``CalibratedClassifierCV``) -> calibrated test predictions;
4. choose the F1 threshold on inner out-of-fold calibrated predictions (the
   calibration folds: each member model predicts the third it was not trained on).

The outer-test fold is only ever predicted. Callers pass eligible
(non-masked) participants only.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from ..evaluation.metrics import best_f1_threshold
from ..models import baselines, candidates
from ..models.preprocessing import dropped_columns
from . import tuning

KEY = "PATNO"


class FoldError(RuntimeError):
    """A fold cannot be trained (for example too few participants of one class)."""


def fit_predict(model: str, X_train: pd.DataFrame, y_train: np.ndarray, X_test: pd.DataFrame, seed: int, cfg: dict,
                params: dict | None = None, calibration: str | None = None) -> dict:
    """Train on the training rows and predict the test rows. Returns predictions, threshold, parameters and the fitted model."""
    spec = cfg.get("calibration") or {}
    n_cal = int(spec.get("cv", 3))
    method = calibration or spec.get("method", "sigmoid")
    y_train = np.asarray(y_train, dtype=int)
    if min((y_train == 0).sum(), (y_train == 1).sum()) < 2 * n_cal:
        raise FoldError("too few participants of one class in the training rows")
    tuned = {}
    if model in candidates.CANDIDATES:
        if params is None:
            tuned = tuning.tune(model, X_train, y_train, seed, cfg)
            params = tuned["params"]
        pipeline = candidates.build(model, params, y_train, seed, cfg)
    else:
        params, method = {}, "none"  # baselines and the leakage check are neither tuned nor calibrated
        pipeline = baselines.build(model, seed, cfg)
    fitted = clone(pipeline).fit(X_train, y_train)
    p_uncal = fitted.predict_proba(X_test)[:, 1]
    inner = StratifiedKFold(n_splits=n_cal, shuffle=True, random_state=seed + 1)
    if method == "none":
        final, p_cal = fitted, p_uncal
        inner_oof = cross_val_predict(clone(pipeline), X_train, y_train, cv=inner, method="predict_proba")[:, 1]
    else:
        folds = StratifiedKFold(n_splits=n_cal, shuffle=True, random_state=seed)
        final = CalibratedClassifierCV(clone(pipeline), method=method, cv=folds).fit(X_train, y_train)
        p_cal = final.predict_proba(X_test)[:, 1]
        # Each member model was trained on two thirds of the training rows; its calibrated predictions for the
        # remaining third are the inner out-of-fold calibrated predictions the threshold is chosen on.
        inner_oof = np.empty(len(y_train))
        for member, (_, held) in zip(final.calibrated_classifiers_, folds.split(X_train, y_train)):
            inner_oof[held] = member.predict_proba(X_train.iloc[held])[:, 1]
    return {"p_uncal": p_uncal, "p_cal": p_cal, "threshold": best_f1_threshold(y_train, inner_oof), "params": params,
            "inner_log_loss": tuned.get("inner_log_loss"), "model": fitted, "calibrated": final,
            "prevalence": float(y_train.mean()), "dropped": dropped_columns(fitted),
            "n_failed_trials": tuned.get("n_failed_trials", 0), "trial_failures": tuned.get("trial_failures", {})}


def _one_fold(k: int, X: pd.DataFrame, y: np.ndarray, folds: np.ndarray, ids: np.ndarray, model: str, seed: int,
              cfg: dict, given: dict | None, calibration: str | None, keep_model: bool) -> tuple[dict, pd.DataFrame | None, object]:
    """One outer fold: train on the other folds, predict this one. Never raises; a failure is recorded."""
    import warnings

    warnings.simplefilter("ignore")  # library warnings can quote values (also inside worker processes)
    started = time.time()
    test, train = folds == k, folds != k
    record = {"fold": int(k), "n_train": int(train.sum()), "n_test": int(test.sum()), "failed": False}
    try:
        out = fit_predict(model, X[train], y[train], X[test], seed, cfg, params=given, calibration=calibration)
    except Exception as exc:  # noqa: BLE001 - never log a message that could quote data
        record.update(failed=True, error=type(exc).__name__)
        if isinstance(exc, (tuning.TuningError, FoldError)):
            record["error_detail"] = str(exc)  # written by this package: model name, counts and exception types only
        return record, None, None
    record.update(params=out["params"], threshold=out["threshold"], inner_log_loss=out["inner_log_loss"],
                  seconds=round(time.time() - started, 1), n_dropped=len(out["dropped"]), dropped_features=out["dropped"],
                  n_failed_trials=out["n_failed_trials"], trial_failures=out["trial_failures"])
    part = pd.DataFrame({KEY: ids[test], "fold": int(k), "y": y[test], "p_prev": out["prevalence"],
                         "p_uncal": out["p_uncal"], "p_cal": out["p_cal"], "threshold": out["threshold"],
                         "pred": (out["p_cal"] >= out["threshold"]).astype(int)})
    return record, part, (out["model"] if keep_model else None)


def outer_jobs(cfg: dict, model: str, n_folds: int) -> int:
    """How many outer folds to run at the same time (``outer_jobs`` in the configuration; 1 = one after another)."""
    spec = cfg.get("outer_jobs", 1)
    return max(1, min(int(spec.get(model, 1) if isinstance(spec, dict) else spec), n_folds))


def outer_cv(X: pd.DataFrame, y: np.ndarray, folds: np.ndarray, ids: np.ndarray, model: str, seed: int, cfg: dict,
             fold_params: dict | None = None, calibration: str | None = None, keep_models: bool = False,
             log=None) -> dict:
    """Run every outer fold. Returns the out-of-fold table, one record per fold and (optionally) the fold models.

    ``fold_params`` maps a fold to the hyperparameters to reuse; without it
    each fold is tuned. A fold that fails is recorded (exception type only)
    and left out of the out-of-fold table. With ``outer_jobs`` > 1 the folds
    run in separate processes, each with its share of the cores.
    """
    y, folds, ids = np.asarray(y, dtype=int), np.asarray(folds, dtype=int), np.asarray(ids)
    order = [int(k) for k in sorted(np.unique(folds))]
    jobs = outer_jobs(cfg, model, len(order))
    args = [(k, X, y, folds, ids, model, seed, cfg, None if fold_params is None else fold_params[k], calibration, keep_models)
            for k in order]
    if jobs == 1:
        results = []
        for a in args:
            results.append(_one_fold(*a))
            if log:
                log(f"fold {a[0]}: " + ("FAILED (" + results[-1][0]["error"] + ")" if results[-1][0]["failed"]
                                        else f"done in {results[-1][0]['seconds']:.0f}s"))
    else:
        import os

        from joblib import Parallel, delayed

        share = dict(cfg, n_jobs=max(1, (os.cpu_count() or jobs) // jobs))  # each process gets its share of the cores
        results = Parallel(n_jobs=jobs)(delayed(_one_fold)(*a[:7], share, *a[8:]) for a in args)
        if log:
            for record, _, _ in results:
                log(f"fold {record['fold']}: " + ("FAILED (" + record["error"] + ")" if record["failed"] else f"done in {record['seconds']:.0f}s"))
    records = [r for r, _, _ in results]
    parts = [part for _, part, _ in results if part is not None]
    models = {r["fold"]: m for r, _, m in results if m is not None}
    oof = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=[KEY, "fold", "y", "p_prev", "p_uncal", "p_cal", "threshold", "pred"])
    return {"oof": oof, "folds": records, "models": models}
