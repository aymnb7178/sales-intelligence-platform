"""Headline KPI computation."""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd

from .db import run_query


def compute_kpis(conn: sqlite3.Connection, monthly: pd.DataFrame | None = None) -> dict[str, Any]:
    """Compute headline KPIs from the database.

    ``repeat_customer_rate_pct`` is the share of customers with 2+ orders.
    ``yoy_growth_last_12m_pct`` compares the last 12 months with the 12 before them
    (None if fewer than 24 months of data).
    """
    row = run_query(conn, "kpi_summary").iloc[0]
    if monthly is None:
        monthly = run_query(conn, "monthly_revenue")
    freq = run_query(conn, "rfm_base", {"ref_date": "9999-12-31"})["frequency"]

    revenue = float(row["revenue"])
    cogs = float(row["cogs"])
    orders = int(row["orders"])
    customers = int(row["customers"])
    kpis: dict[str, Any] = {
        "revenue": round(revenue, 2),
        "gross_profit": round(revenue - cogs, 2),
        "gross_margin_pct": round(100 * (revenue - cogs) / revenue, 2) if revenue else 0.0,
        "orders": orders,
        "customers": customers,
        "units": int(row["units"]),
        "avg_order_value": round(revenue / orders, 2) if orders else 0.0,
        "revenue_per_customer": round(revenue / customers, 2) if customers else 0.0,
        "repeat_customer_rate_pct": round(100 * float((freq >= 2).mean()), 2) if len(freq) else 0.0,
        "first_order_date": row["first_order_date"],
        "last_order_date": row["last_order_date"],
        "yoy_growth_last_12m_pct": None,
    }
    if len(monthly) >= 24:
        rev = monthly["revenue"].to_numpy()
        last, prev = rev[-12:].sum(), rev[-24:-12].sum()
        kpis["revenue_last_12m"] = round(float(last), 2)
        kpis["yoy_growth_last_12m_pct"] = round(100 * float(last - prev) / float(prev), 2)
    return kpis
