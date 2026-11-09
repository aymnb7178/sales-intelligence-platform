"""Cohort retention matrix."""

from __future__ import annotations

import sqlite3

import pandas as pd

from .db import run_query


def retention_matrix(activity: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pivot cohort activity into (counts, retention %) matrices.

    Rows are cohorts (month of first order), columns are month offsets. Offset 0 is
    100% by construction. Cells for months that have not happened yet stay NaN.
    """
    counts = activity.pivot(index="cohort_month", columns="month_index", values="active_customers")
    pct = counts.div(counts[0], axis=0) * 100.0
    return counts, pct.round(2)


def compute_cohorts(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the cohort SQL and return (counts, retention %)."""
    return retention_matrix(run_query(conn, "cohort_activity"))


def average_retention(pct: pd.DataFrame, max_offset: int = 12) -> pd.Series:
    """Unweighted mean retention per month offset across cohorts."""
    cols = [c for c in pct.columns if c <= max_offset]
    return pct[cols].mean(axis=0).round(2)


def to_long(counts: pd.DataFrame, pct: pd.DataFrame) -> pd.DataFrame:
    """Long format (one row per cohort and offset), convenient for BI tools."""
    c = counts.stack().rename("active_customers").reset_index()
    p = pct.stack().rename("retention_pct").reset_index()
    out = c.merge(p, on=["cohort_month", "month_index"])
    out["cohort_size"] = out["cohort_month"].map(counts[0])
    return out
