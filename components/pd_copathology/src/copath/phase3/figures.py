"""Aggregate figures for reports/phase3/figures: curves, reliability diagrams and bar charts. No individual points."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402

MIN_BIN = 5


def _save(fig, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(folder / name, dpi=130)
    plt.close(fig)


def curves(by_model: dict[str, pd.DataFrame], label: str, folder: Path, prefix: str = "cv") -> None:
    """ROC, precision-recall and reliability diagram of calibrated out-of-fold predictions, one line per model."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for model, oof in by_model.items():
        y, p = oof["y"].to_numpy(), oof["p_cal"].to_numpy()
        if len(np.unique(y)) < 2:
            continue
        fpr, tpr, _ = roc_curve(y, p)
        precision, recall, _ = precision_recall_curve(y, p)
        axes[0].plot(fpr, tpr, label=model)
        axes[1].plot(recall, precision, label=model)
        index = np.minimum((p * 10).astype(int), 9)
        points = [(p[index == b].mean(), y[index == b].mean()) for b in range(10) if (index == b).sum() >= MIN_BIN]
        if points:
            axes[2].plot(*zip(*points), marker="o", label=model)
    axes[0].plot([0, 1], [0, 1], color="grey", linestyle=":")
    axes[2].plot([0, 1], [0, 1], color="grey", linestyle=":")
    for ax, title, xlabel, ylabel in ((axes[0], "ROC", "False positive rate", "True positive rate"),
                                      (axes[1], "Precision-recall", "Recall", "Precision"),
                                      (axes[2], f"Reliability (10 bins, n >= {MIN_BIN})", "Mean predicted probability", "Observed proportion")):
        ax.set(title=f"{label}: {title}", xlabel=xlabel, ylabel=ylabel)
        ax.legend(fontsize=8)
    _save(fig, folder, f"{prefix}_curves_{label}.png")


def ablation(table: pd.DataFrame, folder: Path) -> None:
    if table.empty or "delta_bss" not in table.columns:
        return
    done = table[table["status"] == "ok"]
    for label, part in done.groupby("label"):
        fig, ax = plt.subplots(figsize=(8, 4.6))
        values = pd.to_numeric(part["delta_bss"], errors="coerce")
        errors = pd.to_numeric(part["sd_delta_bss"], errors="coerce").fillna(0)
        ax.barh(part["analysis"], values, xerr=errors, color="#4477aa")
        ax.axvline(0, color="grey", linewidth=0.8)
        ax.set(title=f"{label}: change in Brier Skill Score (mean over folds, SD)", xlabel="BSS (ablated - full)")
        _save(fig, folder, f"ablation_{label}.png")


def shap_bars(top: pd.DataFrame, by_modality: pd.DataFrame, label: str, model: str, folder: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].barh(top["feature"][::-1], top["mean_abs_shap"][::-1], color="#4477aa")
    axes[0].set(title=f"{label} ({model}): top features", xlabel="mean |SHAP|")
    ordered = by_modality.sort_values("mean_abs_shap_sum")
    axes[1].barh(ordered["modality"], ordered["mean_abs_shap_sum"], color="#228833")
    axes[1].set(title=f"{label} ({model}): by modality", xlabel="sum of mean |SHAP|")
    _save(fig, folder, f"shap_{label}.png")


def reliability_points(y: np.ndarray, p: np.ndarray, bins: int = 10, min_n: int = MIN_BIN) -> list[tuple[float, float, int]]:
    """(mean predicted, observed proportion, n) for every equal-width probability bin that holds at least ``min_n`` rows."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    index = np.minimum((p * bins).astype(int), bins - 1)
    return [(float(p[index == b].mean()), float(y[index == b].mean()), int((index == b).sum())) for b in range(bins)
            if (index == b).sum() >= min_n]


def final_curves(test: pd.DataFrame, dev: pd.DataFrame, label: str, model: str, folder: Path) -> None:
    """Held-out ROC, precision-recall and reliability curves, each with the development out-of-fold curve of the same model."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for name, frame, style in (("held-out test", test, {"color": "#cc3311"}), ("development (out-of-fold)", dev, {"color": "#4477aa", "linestyle": "--"})):
        y, p = frame["y"].to_numpy(), frame["p_cal"].to_numpy()
        if len(np.unique(y)) < 2:
            continue
        fpr, tpr, _ = roc_curve(y, p)
        precision, recall, _ = precision_recall_curve(y, p)
        axes[0].plot(fpr, tpr, label=name, **style)
        axes[1].plot(recall, precision, label=name, **style)
        points = reliability_points(y, p)
        if points:
            axes[2].plot([a for a, _, _ in points], [b for _, b, _ in points], marker="o", label=name, **style)
    axes[0].plot([0, 1], [0, 1], color="grey", linestyle=":")
    axes[2].plot([0, 1], [0, 1], color="grey", linestyle=":")
    for ax, title, xlabel, ylabel in ((axes[0], "ROC", "False positive rate", "True positive rate"),
                                      (axes[1], "Precision-recall", "Recall", "Precision"),
                                      (axes[2], f"Reliability (10 bins, n >= {MIN_BIN})", "Mean predicted probability", "Observed proportion")):
        ax.set(title=f"{label} ({model}): {title}", xlabel=xlabel, ylabel=ylabel)
        ax.legend(fontsize=8)
    _save(fig, folder, f"final_test_curves_{label}.png")


def final_summary(table: pd.DataFrame, folder: Path) -> None:
    """Development (pooled out-of-fold) versus held-out AUROC, AUPRC and BSS per signal; held-out bars carry the 95% bootstrap CI."""
    metrics = ["auroc", "auprc", "bss"]
    labels = list(dict.fromkeys(table["label"]))
    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 4.6))
    x = np.arange(len(labels))
    for ax, metric in zip(axes, metrics):
        part = table[table["metric"] == metric].set_index("label").reindex(labels)
        dev = pd.to_numeric(part["dev_oof_pooled"], errors="coerce").to_numpy()
        test = pd.to_numeric(part["heldout"], errors="coerce").to_numpy()
        low, high = (pd.to_numeric(part[c], errors="coerce").to_numpy() for c in ("heldout_ci_low", "heldout_ci_high"))
        # a percentile interval may exclude the point estimate: draw such a bar with length 0 on that side rather than fail
        error = np.vstack([np.clip(np.nan_to_num(test - low), 0, None), np.clip(np.nan_to_num(high - test), 0, None)])
        ax.bar(x - 0.2, dev, 0.4, color="#4477aa", label="development (out-of-fold)")
        ax.bar(x + 0.2, test, 0.4, yerr=error, capsize=3, color="#cc3311", label="held-out test (95% CI)")
        ax.set(title=metric.upper(), xticks=x, xticklabels=labels)
        ax.tick_params(axis="x", rotation=20)
        ax.axhline(0, color="grey", linewidth=0.8)
    axes[0].legend(fontsize=8)
    _save(fig, folder, "final_test_summary.png")
