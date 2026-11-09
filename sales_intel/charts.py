"""Matplotlib charts (Agg backend, written as PNG)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .analysis import Analysis  # noqa: E402

BLUE = "#2563eb"
ORANGE = "#ea580c"
GREY = "#6b7280"
GREEN = "#059669"
SIZE = (9, 4.2)
DPI = 110

plt.rcParams.update(
    {
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "font.size": 10,
        "axes.titleweight": "bold",
    }
)


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def revenue_forecast(a: Analysis, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=SIZE)
    x = pd.PeriodIndex(a.monthly["month"], freq="M").to_timestamp()
    ax.plot(x, a.monthly["revenue"] / 1e3, color=BLUE, lw=2, label="Actual (synthetic)")
    fx = pd.PeriodIndex(a.forecast["month"], freq="M").to_timestamp()
    ax.plot(
        fx, a.forecast["forecast"] / 1e3, color=ORANGE, lw=2, ls="--", marker="o", ms=4,
        label=f"Forecast ({a.forecast['model'].iloc[0]})",
    )
    ax.set_title("Monthly revenue and 6-month forecast")
    ax.set_ylabel("Revenue (thousands)")
    ax.legend(frameon=False)
    return _save(fig, path)


def backtest_chart(a: Analysis, path: Path) -> Path:
    bt = a.backtest
    fig, ax = plt.subplots(figsize=SIZE)
    idx = bt.predictions.index.to_timestamp()
    ax.plot(idx, bt.predictions["actual"] / 1e3, color="black", lw=2.2, marker="o", label="Actual")
    colors = {"naive": GREY, "seasonal_naive": GREEN, "seasonal_naive_drift": BLUE, "trend_seasonal_lr": ORANGE}
    for name in bt.metrics:
        ax.plot(
            idx, bt.predictions[name] / 1e3, color=colors.get(name, GREY), lw=1.6, ls="--",
            label=f"{name} (MAPE {bt.metrics[name]:.1f}%)",
        )
    ax.set_title(f"Holdout backtest (last {bt.holdout} months)")
    ax.set_ylabel("Revenue (thousands)")
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, path)


def top_products_chart(a: Analysis, path: Path) -> Path:
    df = a.top_products.iloc[::-1]
    fig, ax = plt.subplots(figsize=SIZE)
    ax.barh(df["name"], df["revenue"] / 1e3, color=BLUE)
    ax.set_title("Top products by revenue")
    ax.set_xlabel("Revenue (thousands)")
    ax.grid(axis="y", visible=False)
    return _save(fig, path)


def category_margin_chart(a: Analysis, path: Path) -> Path:
    df = a.category_margin.sort_values("margin_pct")
    fig, ax = plt.subplots(figsize=SIZE)
    bars = ax.barh(df["category"], df["margin_pct"], color=GREEN)
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.set_title("Gross margin by category")
    ax.set_xlabel("Gross margin (%)")
    ax.set_xlim(0, max(df["margin_pct"].max() * 1.15, 1))
    ax.grid(axis="y", visible=False)
    return _save(fig, path)


def rfm_chart(a: Analysis, path: Path) -> Path:
    df = a.rfm_summary
    fig, ax = plt.subplots(figsize=SIZE)
    bars = ax.bar(df["segment"], df["customers"], color=BLUE)
    ax.bar_label(bars, padding=2)
    ax.set_title("Customers per RFM segment")
    ax.set_ylabel("Customers")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    ax.grid(axis="x", visible=False)
    return _save(fig, path)


def cohort_heatmap(a: Analysis, path: Path, max_offset: int = 18) -> Path:
    pct = a.cohort_pct[[c for c in a.cohort_pct.columns if c <= max_offset]]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    data = np.ma.masked_invalid(pct.to_numpy())
    im = ax.imshow(data, aspect="auto", cmap="Blues", vmin=0, vmax=60)
    ax.set_title("Cohort retention (% of cohort active, month 0 = 100% not coloured to scale)")
    ax.set_xlabel("Months since first order")
    ax.set_ylabel("Cohort (first-order month)")
    step = 6
    ax.set_yticks(range(0, len(pct), step), labels=list(pct.index[::step]))
    ax.set_xticks(range(0, pct.shape[1], 3))
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="Retention %")
    return _save(fig, path)


def abc_chart(a: Analysis, path: Path) -> Path:
    df = a.abc.reset_index(drop=True)
    colors = df["abc_class"].map({"A": BLUE, "B": ORANGE, "C": GREY})
    fig, ax = plt.subplots(figsize=SIZE)
    ax.bar(range(len(df)), df["revenue"] / 1e3, color=colors)
    ax.set_ylabel("Revenue (thousands)")
    ax.set_xlabel("Products ranked by revenue")
    ax2 = ax.twinx()
    ax2.plot(range(len(df)), df["cum_share_pct"], color="black", lw=1.5)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("Cumulative share (%)")
    ax2.grid(False)
    counts = df["abc_class"].value_counts()
    ax.set_title(f"ABC analysis: A={counts.get('A', 0)}, B={counts.get('B', 0)}, C={counts.get('C', 0)} products")
    return _save(fig, path)


CHART_FUNCS = {
    "revenue_forecast": revenue_forecast,
    "backtest": backtest_chart,
    "top_products": top_products_chart,
    "category_margin": category_margin_chart,
    "rfm_segments": rfm_chart,
    "cohort_retention": cohort_heatmap,
    "abc_analysis": abc_chart,
}


def render_all(a: Analysis, out_dir: Path) -> dict[str, Path]:
    """Render every chart into ``out_dir`` and return name -> path."""
    return {name: fn(a, out_dir / f"{name}.png") for name, fn in CHART_FUNCS.items()}
