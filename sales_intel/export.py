"""CSV export for Power BI (or any BI tool) import."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .analysis import Analysis
from .cohorts import to_long
from .db import run_query


def build_dim_date(start: str, end: str) -> pd.DataFrame:
    """Calendar dimension covering ``start`` to ``end`` inclusive."""
    d = pd.date_range(start, end, freq="D")
    return pd.DataFrame(
        {
            "date": d.strftime("%Y-%m-%d"),
            "year": d.year,
            "quarter": d.quarter,
            "month": d.month,
            "month_name": d.strftime("%B"),
            "year_month": d.strftime("%Y-%m"),
            "is_weekend": (d.dayofweek >= 5).astype(int),
        }
    )


def export_csvs(conn: sqlite3.Connection, a: Analysis, out_dir: Path) -> dict[str, int]:
    """Write all BI-ready CSV files and return {filename: row count}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    first = a.kpis["first_order_date"][:4] + "-01-01"
    last = a.kpis["last_order_date"][:4] + "-12-31"
    tables: dict[str, pd.DataFrame] = {
        "dim_customers": pd.read_sql_query("SELECT * FROM customers", conn),
        "dim_products": pd.read_sql_query("SELECT * FROM products", conn),
        "dim_date": build_dim_date(first, last),
        "fact_order_items": run_query(conn, "fact_items"),
        "rfm_segments": a.rfm,
        "cohort_retention": to_long(a.cohort_counts, a.cohort_pct),
        "monthly_revenue": a.monthly,
        "forecast": a.forecast,
        "abc_analysis": a.abc,
        "backtest_metrics": pd.DataFrame({"model": list(a.backtest.metrics), "mape_pct": list(a.backtest.metrics.values())}),
    }
    counts = {}
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False, encoding="utf-8")
        counts[f"{name}.csv"] = len(df)
    return counts
