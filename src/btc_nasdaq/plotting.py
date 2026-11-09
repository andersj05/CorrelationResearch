"""A consistent, readable notebook visual language and portable figure exports."""

from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

PALETTE = ["#246BCE", "#ED9641", "#2B9C8F", "#8B6BB1", "#D65B67", "#65758B", "#B39B46"]


def set_theme() -> None:
    sns.set_theme(style="whitegrid", palette=PALETTE, context="notebook")
    plt.rcParams.update({"figure.figsize": (12, 5), "figure.dpi": 110, "savefig.dpi": 160,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.titlesize": 14,
                         "axes.labelsize": 11, "grid.alpha": .22,
                         "figure.constrained_layout.use": True})


def save_figure(fig, root: Path, name: str) -> None:
    path = root / "reports/figures"
    path.mkdir(parents=True, exist_ok=True)
    fig.savefig(path / f"{name}.png", bbox_inches="tight", facecolor="white")


def shade_holdout(ax, start="2024-01-01") -> None:
    import pandas as pd
    ax.axvline(pd.Timestamp(start), color="#374151", linestyle="--", alpha=.65,
               label="Holdout boundary")
