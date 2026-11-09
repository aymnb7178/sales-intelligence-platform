"""Data generator, schema and SQL query tests."""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from sales_intel.config import GenConfig
from sales_intel.datagen import generate
from sales_intel.db import create_schema, read_sql_file, run_query


def test_generator_is_deterministic():
    a = generate(GenConfig(n_customers=50, seed=1))
    b = generate(GenConfig(n_customers=50, seed=1))
    for k in a:
        pd.testing.assert_frame_equal(a[k], b[k])


def test_different_seed_changes_data():
    a = generate(GenConfig(n_customers=50, seed=1))["orders"]
    b = generate(GenConfig(n_customers=50, seed=2))["orders"]
    assert len(a) != len(b) or not a["order_date"].equals(b["order_date"])


def test_every_customer_has_an_order(frames):
    assert set(frames["customers"]["customer_id"]) == set(frames["orders"]["customer_id"])


def test_referential_integrity(conn):
    conn.execute("PRAGMA foreign_keys = ON")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_schema_rejects_bad_discount():
    c = sqlite3.connect(":memory:")
    create_schema(c)
    c.execute("INSERT INTO customers VALUES (1,'C1','West','organic','2022-01-01')")
    c.execute("INSERT INTO products VALUES (1,'P','Home',1,2)")
    c.execute("INSERT INTO orders VALUES (1,1,'2022-01-02','web')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO order_items VALUES (1,1,1,1,2.0,1.5)")


def test_missing_sql_file_raises():
    with pytest.raises(FileNotFoundError):
        read_sql_file("does_not_exist")


def test_monthly_revenue_sums_to_total(conn, frames):
    monthly = run_query(conn, "monthly_revenue")
    items = frames["order_items"]
    expected = (items["quantity"] * items["unit_price"] * (1 - items["discount"])).sum()
    assert monthly["revenue"].sum() == pytest.approx(expected, rel=1e-4)


def test_monthly_growth_matches_manual(conn):
    m = run_query(conn, "monthly_revenue")
    manual = (m["revenue"].iloc[5] / m["revenue"].iloc[4] - 1) * 100
    assert m["mom_growth_pct"].iloc[5] == pytest.approx(manual, abs=0.01)
    assert pd.isna(m["mom_growth_pct"].iloc[0])
    assert pd.isna(m["yoy_growth_pct"].iloc[11])
    assert pd.notna(m["yoy_growth_pct"].iloc[12])


def test_top_products_limit_and_order(conn):
    t = run_query(conn, "top_products", {"limit": 5})
    assert len(t) == 5
    assert t["revenue"].is_monotonic_decreasing


def test_margin_by_category_consistent(conn):
    m = run_query(conn, "margin_by_category")
    assert (m["revenue"] - m["cogs"] - m["profit"]).abs().max() < 0.05
    assert m["margin_pct"].between(0, 100).all()


def test_abc_classes_cover_all_products_and_order(conn):
    abc = run_query(conn, "abc_analysis")
    assert set(abc["abc_class"]) <= {"A", "B", "C"}
    assert abc["abc_class"].iloc[0] == "A"
    assert abc["cum_share_pct"].iloc[-1] == pytest.approx(100.0, abs=0.1)
    order = {"A": 0, "B": 1, "C": 2}
    assert abc["abc_class"].map(order).is_monotonic_increasing
