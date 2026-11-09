"""RFM scoring and rule-based customer segments."""

from __future__ import annotations

import sqlite3

import pandas as pd

from .db import run_query

SEGMENT_ORDER = [
    "Champions",
    "Loyal",
    "Potential Loyalists",
    "New Customers",
    "Needs Attention",
    "At Risk",
    "Hibernating",
]


def assign_segment(r: int, f: int) -> str:
    """Map R and F scores (1-5) to a segment name. Rules are evaluated in order."""
    if r >= 4 and f >= 4:
        return "Champions"
    if f >= 4 and r >= 3:
        return "Loyal"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r >= 4 and f <= 1:
        return "New Customers"
    if r >= 3 and f >= 2:
        return "Potential Loyalists"
    if r <= 2:
        return "Hibernating"
    return "Needs Attention"


def _quintile(values: pd.Series, ascending: bool = True) -> pd.Series:
    """Quintile score 1-5. Ranking with ``method='first'`` breaks ties by row order,
    which keeps the five bins equal-sized even when many customers share a value."""
    ranks = values.rank(method="first", ascending=ascending)
    return pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)


def score_rfm(base: pd.DataFrame) -> pd.DataFrame:
    """Add r/f/m scores, a combined code and a segment to the raw RFM table."""
    df = base.copy()
    # lower recency_days is better -> rank descending so the most recent gets 5
    df["r_score"] = _quintile(df["recency_days"], ascending=False)
    df["f_score"] = _quintile(df["frequency"])
    df["m_score"] = _quintile(df["monetary"])
    df["rfm_code"] = df["r_score"].astype(str) + df["f_score"].astype(str) + df["m_score"].astype(str)
    df["segment"] = [assign_segment(r, f) for r, f in zip(df["r_score"], df["f_score"])]
    return df


def compute_rfm(conn: sqlite3.Connection, ref_date: str | None = None) -> pd.DataFrame:
    """Run the RFM SQL and score it. ``ref_date`` defaults to the day after the last order."""
    if ref_date is None:
        last = pd.read_sql_query("SELECT MAX(order_date) AS d FROM orders", conn)["d"].iloc[0]
        ref_date = (pd.Timestamp(last) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    base = run_query(conn, "rfm_base", {"ref_date": ref_date})
    return score_rfm(base)


def summarize_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    """Customers, average R/F/M and revenue share per segment."""
    g = rfm.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_recency_days=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum"),
    )
    g["revenue_share_pct"] = 100 * g["total_revenue"] / g["total_revenue"].sum()
    g = g.reindex([s for s in SEGMENT_ORDER if s in g.index]).reset_index()
    return g.round(2)
