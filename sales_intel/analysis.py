"""Run the full analytics pipeline once and bundle the results."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

import pandas as pd

from .cohorts import compute_cohorts
from .config import AnalysisConfig
from .db import run_query
from .forecast import BacktestResult, backtest, forecast_future, monthly_series
from .kpis import compute_kpis
from .rfm import compute_rfm, summarize_segments

log = logging.getLogger(__name__)


@dataclass
class Analysis:
    kpis: dict
    monthly: pd.DataFrame
    top_products: pd.DataFrame
    category_margin: pd.DataFrame
    rfm: pd.DataFrame
    rfm_summary: pd.DataFrame
    cohort_counts: pd.DataFrame
    cohort_pct: pd.DataFrame
    abc: pd.DataFrame
    backtest: BacktestResult
    forecast: pd.DataFrame


def run_analysis(conn: sqlite3.Connection, cfg: AnalysisConfig | None = None) -> Analysis:
    """Execute every SQL query and Python model and return the results."""
    cfg = cfg or AnalysisConfig()
    monthly = run_query(conn, "monthly_revenue")
    series = monthly_series(monthly)
    bt = backtest(series, cfg.holdout_months)
    fc = forecast_future(series, bt.best_model, cfg.forecast_horizon)
    rfm = compute_rfm(conn)
    counts, pct = compute_cohorts(conn)
    result = Analysis(
        kpis=compute_kpis(conn, monthly),
        monthly=monthly,
        top_products=run_query(conn, "top_products", {"limit": cfg.top_n}),
        category_margin=run_query(conn, "margin_by_category"),
        rfm=rfm,
        rfm_summary=summarize_segments(rfm),
        cohort_counts=counts,
        cohort_pct=pct,
        abc=run_query(conn, "abc_analysis"),
        backtest=bt,
        forecast=fc,
    )
    log.info("Analysis complete; best backtest model: %s", bt.best_model)
    return result
