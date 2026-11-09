"""KPI, RFM, cohort and forecast tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sales_intel.analysis import run_analysis
from sales_intel.cohorts import average_retention, retention_matrix
from sales_intel.forecast import (
    backtest,
    forecast_future,
    mape,
    monthly_series,
    naive,
    seasonal_naive,
)
from sales_intel.kpis import compute_kpis
from sales_intel.rfm import assign_segment, compute_rfm, score_rfm


def test_kpis_internally_consistent(conn):
    k = compute_kpis(conn)
    assert k["avg_order_value"] == pytest.approx(k["revenue"] / k["orders"], abs=0.01)
    assert k["gross_profit"] < k["revenue"]
    assert 0 <= k["repeat_customer_rate_pct"] <= 100


def test_mape_known_value():
    assert mape(np.array([100, 200]), np.array([110, 180])) == pytest.approx(10.0)


def test_mape_all_zero_raises():
    with pytest.raises(ValueError):
        mape(np.array([0, 0]), np.array([1, 1]))


def _series(n=36):
    idx = pd.period_range("2022-01", periods=n, freq="M")
    season = np.tile([1.0, 0.9, 1.1, 1.0, 1.2, 0.8, 1.0, 1.0, 0.9, 1.1, 1.3, 1.4], n // 12 + 1)[:n]
    return pd.Series((1000 + 20 * np.arange(n)) * season, index=idx)


def test_naive_and_seasonal_naive_shapes():
    s = _series()
    assert naive(s, 4).tolist() == [s.iloc[-1]] * 4
    assert seasonal_naive(s, 3).tolist() == s.iloc[-12:-9].tolist()


def test_backtest_beats_naive_on_seasonal_trend_series():
    bt = backtest(_series(), holdout=6)
    assert bt.metrics["trend_seasonal_lr"] < bt.metrics["naive"]
    assert bt.improvement_vs_naive_pct > 0
    assert len(bt.predictions) == 6


def test_backtest_does_not_leak_holdout():
    s = _series()
    modified = s.copy()
    modified.iloc[-6:] *= 100  # change only the holdout actuals
    a = backtest(s, 6).predictions["trend_seasonal_lr"].to_numpy()
    b = backtest(modified, 6).predictions["trend_seasonal_lr"].to_numpy()
    np.testing.assert_allclose(a, b)


def test_backtest_bad_holdout():
    with pytest.raises(ValueError):
        backtest(_series(), holdout=0)


def test_forecast_future_months_follow_series():
    s = _series()
    f = forecast_future(s, "trend_seasonal_lr", 6)
    assert f["month"].iloc[0] == "2025-01"
    assert len(f) == 6 and (f["forecast"] > 0).all()


def test_monthly_series_fills_gaps():
    m = pd.DataFrame({"month": ["2024-01", "2024-03"], "revenue": [5.0, 7.0]})
    s = monthly_series(m)
    assert s.tolist() == [5.0, 0.0, 7.0]


def test_monthly_series_from_sql(conn):
    from sales_intel.db import run_query

    s = monthly_series(run_query(conn, "monthly_revenue"))
    assert len(s) >= 47 and s.index.is_monotonic_increasing and s.index.freqstr == "M"


def test_rfm_scores_and_segments(conn):
    r = compute_rfm(conn)
    assert r[["r_score", "f_score", "m_score"]].stack().between(1, 5).all()
    assert r["segment"].notna().all()
    sizes = r["r_score"].value_counts()
    assert sizes.max() - sizes.min() <= 1  # quintiles are balanced


def test_recent_frequent_customer_scores_high():
    base = pd.DataFrame(
        {"customer_id": range(1, 11), "recency_days": [1, 50, 90, 120, 150, 200, 250, 300, 350, 400],
         "frequency": [20, 9, 8, 7, 6, 5, 4, 3, 2, 1], "monetary": [900, 800, 700, 600, 500, 400, 300, 200, 100, 50]}
    )
    s = score_rfm(base).set_index("customer_id")
    assert s.loc[1, "rfm_code"] == "555" and s.loc[1, "segment"] == "Champions"
    assert s.loc[10, "segment"] == "Hibernating"


def test_assign_segment_rules():
    assert assign_segment(5, 5) == "Champions"
    assert assign_segment(1, 4) == "At Risk"
    assert assign_segment(5, 1) == "New Customers"


def test_cohort_matrix_properties(conn):
    from sales_intel.cohorts import compute_cohorts

    counts, pct = compute_cohorts(conn)
    assert (pct[0] == 100).all()
    assert pct.stack().max() <= 100.0
    assert counts[0].sum() == 300  # every customer belongs to exactly one cohort
    assert average_retention(pct, 3).index.max() == 3


def test_retention_matrix_toy():
    act = pd.DataFrame({"cohort_month": ["a", "a", "a", "b", "b"], "month_index": [0, 1, 2, 0, 1],
                        "active_customers": [10, 5, 2, 4, 1]})
    _, pct = retention_matrix(act)
    assert pct.loc["a", 1] == 50.0 and pd.isna(pct.loc["b", 2])


def test_run_analysis_bundle(conn):
    a = run_analysis(conn)
    assert len(a.forecast) == 6 and a.backtest.best_model in a.backtest.metrics
    assert a.rfm_summary["customers"].sum() == len(a.rfm)
