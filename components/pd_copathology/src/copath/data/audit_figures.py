"""Aggregate figures for the dataset audit."""

from __future__ import annotations

from pathlib import Path

_BAR = "#2F6FB0"
_INK = "#1F2933"
_MUTED = "#6B7280"
_GRID = "#E5E7EB"
_OFF = "#D5DAE1"


def plot_modality_upset(upset: dict, group_sizes: dict[str, object], path: Path, max_patterns: int = 15) -> bool:
    """UpSet-style plot of exact modality-group combinations.

    Only patterns at or above the suppression threshold are passed in, so no
    small cell is drawn. Returns ``False`` when there is nothing to plot.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups: list[str] = upset.get("groups", [])
    patterns = upset.get("patterns", [])[:max_patterns]
    if not groups or not patterns:
        return False

    fig, (ax_bar, ax_dot) = plt.subplots(
        2, 1, figsize=(max(7.0, 0.6 * len(patterns) + 4.0), 6.5), sharex=True,
        gridspec_kw={"height_ratios": [3, 2], "hspace": 0.06},
    )
    xs = list(range(len(patterns)))
    counts = [count for _, count in patterns]
    ax_bar.bar(xs, counts, width=0.55, color=_BAR)
    for x, count in zip(xs, counts):
        ax_bar.text(x, count, f"{count:,}", ha="center", va="bottom", fontsize=8, color=_INK)
    ax_bar.set_ylabel("Participants", color=_MUTED, fontsize=9)
    ax_bar.yaxis.grid(True, color=_GRID, linewidth=0.8)
    ax_bar.set_axisbelow(True)
    ax_bar.tick_params(axis="both", length=0, labelsize=8, colors=_MUTED)
    for side in ("top", "right", "left"):
        ax_bar.spines[side].set_visible(False)
    ax_bar.spines["bottom"].set_color(_GRID)
    ax_bar.set_title(
        upset.get("title", "Participants by exact combination of modality groups"),
        loc="left", fontsize=10, color=_INK, pad=22, wrap=True,
    )
    hidden = upset.get("n_suppressed_patterns", 0)
    shown_note = f"Largest {len(patterns)} combinations shown." if len(upset.get("patterns", [])) > len(patterns) else ""
    ax_bar.text(
        0, 1.03, f"{shown_note} {hidden} combination(s) with a suppressed small count are not drawn.".strip(),
        transform=ax_bar.transAxes, fontsize=8, color=_MUTED,
    )

    ys = list(range(len(groups)))[::-1]
    row = dict(zip(groups, ys))
    for x, (held, _) in zip(xs, patterns):
        ax_dot.scatter([x] * len(groups), ys, s=42, color=_OFF, zorder=2)
        on = [row[g] for g in held]
        ax_dot.scatter([x] * len(on), on, s=42, color=_BAR, zorder=3)
        if len(on) > 1:
            ax_dot.plot([x, x], [min(on), max(on)], color=_BAR, linewidth=2, zorder=2.5)
    ax_dot.set_yticks(ys)
    ax_dot.set_yticklabels([f"{g}  (n = {group_sizes.get(g, '')})" for g in groups], fontsize=8, color=_INK)
    ax_dot.set_xticks([])
    ax_dot.set_ylim(-0.6, len(groups) - 0.4)
    ax_dot.tick_params(axis="both", length=0)
    for side in ("top", "right", "left", "bottom"):
        ax_dot.spines[side].set_visible(False)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True
