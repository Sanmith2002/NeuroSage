"""Discrimination, calibration and threshold metrics for out-of-fold predictions.

Every function takes plain arrays. Nothing here reads data or writes files.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score

EPS = 1e-6
LABEL_METRICS = ["auroc", "auprc", "brier", "bss", "cal_slope", "cal_intercept", "ece", "f1", "precision", "recall"]


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def calibration_slope_intercept(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Logistic recalibration: y ~ intercept + slope * logit(p). NaN when it cannot be fitted."""
    y, x = np.asarray(y, dtype=int), logit(p)
    if len(np.unique(y)) < 2 or np.ptp(x) < 1e-9:
        return float("nan"), float("nan")
    try:
        fit = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=1000).fit(x.reshape(-1, 1), y)
    except Exception:  # noqa: BLE001 - a recalibration that does not converge is reported as not available
        return float("nan"), float("nan")
    return float(fit.coef_[0, 0]), float(fit.intercept_[0])


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    index = np.minimum((p * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        inside = index == b
        if inside.any():
            total += inside.mean() * abs(y[inside].mean() - p[inside].mean())
    return float(total)


def best_f1_threshold(y: np.ndarray, p: np.ndarray) -> float:
    """The probability threshold that maximises F1 (prediction = p >= threshold)."""
    y = np.asarray(y, dtype=int)
    if y.sum() == 0:
        return 0.5
    precision, recall, thresholds = precision_recall_curve(y, p)
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    return float(thresholds[int(np.argmax(f1))])


def threshold_metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    y, pred = np.asarray(y, dtype=int), np.asarray(pred, dtype=int)
    tp, fp, fn = int(((pred == 1) & (y == 1)).sum()), int(((pred == 1) & (y == 0)).sum()), int(((pred == 0) & (y == 1)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"f1": f1, "precision": precision, "recall": recall}


def label_metrics(y: np.ndarray, p: np.ndarray, p_ref: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    """All per-label metrics. ``p_ref`` is the prevalence prediction the Brier Skill Score is measured against."""
    y, p, p_ref = np.asarray(y, dtype=int), np.asarray(p, dtype=float), np.asarray(p_ref, dtype=float)
    both = len(np.unique(y)) == 2
    brier, brier_ref = float(np.mean((p - y) ** 2)), float(np.mean((p_ref - y) ** 2))
    slope, intercept = calibration_slope_intercept(y, p)
    out = {
        "auroc": float(roc_auc_score(y, p)) if both else float("nan"),
        "auprc": float(average_precision_score(y, p)) if both else float("nan"),
        "brier": brier, "bss": 1 - brier / brier_ref if brier_ref > 0 else float("nan"),
        "cal_slope": slope, "cal_intercept": intercept, "ece": expected_calibration_error(y, p),
    }
    out.update(threshold_metrics(y, pred))
    return out


def summarise(oof: pd.DataFrame, prob: str = "p_cal", pred: str = "pred") -> dict:
    """Pooled and per-fold metrics of out-of-fold predictions, with mean, SD and SE across folds."""
    def one(part: pd.DataFrame) -> dict[str, float]:
        return label_metrics(part["y"].to_numpy(), part[prob].to_numpy(), part["p_prev"].to_numpy(), part[pred].to_numpy())

    folds = {int(k): one(part) for k, part in oof.groupby("fold", sort=True)}
    table = pd.DataFrame(folds).T
    k = max(len(table), 1)
    return {"pooled": one(oof), "folds": folds, "mean": table.mean().to_dict(), "sd": table.std(ddof=1).to_dict(),
            "se": (table.std(ddof=1) / np.sqrt(k)).to_dict()}


def multilabel(preds: dict[str, pd.DataFrame], key: str = "PATNO") -> dict:
    """Hamming loss and macro-F1 on participants eligible for every label (pooled and per fold).

    ``preds`` maps each label to its out-of-fold table (``key``, ``fold``, ``y``, ``pred``).
    """
    merged = None
    for label, frame in preds.items():
        part = frame[[key, "fold", "y", "pred"]].rename(columns={"y": f"y_{label}", "pred": f"pred_{label}"})
        merged = part if merged is None else merged.merge(part, on=[key, "fold"], how="inner")
    if merged is None or merged.empty:
        return {"n_all_eligible": 0, "hamming_loss": float("nan"), "macro_f1_all_eligible": float("nan"), "folds": {}}

    def one(part: pd.DataFrame) -> tuple[float, float]:
        wrong = [(part[f"y_{label}"] != part[f"pred_{label}"]).mean() for label in preds]
        f1 = [threshold_metrics(part[f"y_{label}"], part[f"pred_{label}"])["f1"] for label in preds]
        return float(np.mean(wrong)), float(np.mean(f1))

    hamming, macro = one(merged)
    folds = {int(k): one(part) for k, part in merged.groupby("fold", sort=True)}
    values = np.array(list(folds.values()))
    return {"n_all_eligible": int(len(merged)), "hamming_loss": hamming, "macro_f1_all_eligible": macro,
            "mean_hamming_loss": float(values[:, 0].mean()), "sd_hamming_loss": float(values[:, 0].std(ddof=1)) if len(values) > 1 else float("nan"),
            "mean_macro_f1_all_eligible": float(values[:, 1].mean()),
            "sd_macro_f1_all_eligible": float(values[:, 1].std(ddof=1)) if len(values) > 1 else float("nan")}


def bootstrap_ci(statistic, n: int, n_boot: int, seed: int) -> dict[str, tuple[float, float]]:
    """Percentile 95% intervals of ``statistic(index_array) -> dict`` over ``n_boot`` resamples of ``n`` rows."""
    rng = np.random.default_rng(seed)
    draws: dict[str, list[float]] = {}
    for _ in range(n_boot):
        for name, value in statistic(rng.integers(0, n, n)).items():
            if value is not None and np.isfinite(value):
                draws.setdefault(name, []).append(float(value))
    return {name: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for name, v in draws.items() if len(v) >= 0.5 * n_boot}
