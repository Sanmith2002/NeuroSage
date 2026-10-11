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
