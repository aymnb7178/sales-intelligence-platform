"""Charts, dashboard, CSV export and CLI tests."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from sales_intel.analysis import run_analysis
from sales_intel.charts import render_all
from sales_intel.cli import main
from sales_intel.export import build_dim_date, export_csvs
from sales_intel.report import build_dashboard


@pytest.fixture()
def analysis(conn):
    return run_analysis(conn)


def test_charts_are_real_pngs(analysis, tmp_path):
    charts = render_all(analysis, tmp_path)
    assert len(charts) == 7
    for p in charts.values():
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_dashboard_is_self_contained(analysis, tmp_path):
    out = build_dashboard(analysis, render_all(analysis, tmp_path / "c"), tmp_path / "d.html")
    text = out.read_text(encoding="utf-8")
    assert text.count("data:image/png;base64,") == 7
    assert "Synthetic data" in text
    assert "<script" not in text and "http://" not in text and "https://" not in text


def test_csv_export_contents(conn, analysis, tmp_path):
    counts = export_csvs(conn, analysis, tmp_path)
    assert (tmp_path / "fact_order_items.csv").exists()
    fact = pd.read_csv(tmp_path / "fact_order_items.csv")
    assert len(fact) == counts["fact_order_items.csv"]
    assert fact["revenue"].sum() == pytest.approx(analysis.kpis["revenue"], rel=1e-3)
    assert set(fact["customer_id"]) <= set(pd.read_csv(tmp_path / "dim_customers.csv")["customer_id"])


def test_dim_date_complete():
    d = build_dim_date("2024-01-01", "2024-12-31")
    assert len(d) == 366 and d["date"].is_unique


def test_cli_generate_kpis_forecast(tmp_path, capsys):
    db = tmp_path / "t.db"
    assert main(["generate", "--db", str(db), "--customers", "200"]) == 0
    assert db.exists()
    capsys.readouterr()
    assert main(["kpis", "--db", str(db)]) == 0
    assert json.loads(capsys.readouterr().out)["customers"] == 200
    assert main(["forecast", "--db", str(db)]) == 0
    assert "MAPE" in capsys.readouterr().out


def test_cli_missing_db_exits(tmp_path):
    with pytest.raises(SystemExit):
        main(["kpis", "--db", str(tmp_path / "nope.db")])


def test_cli_all_end_to_end(tmp_path, capsys):
    rc = main(["all", "--db", str(tmp_path / "a.db"), "--customers", "200", "--out", str(tmp_path / "d.html"),
               "--charts-dir", str(tmp_path / "c"), "--export-dir", str(tmp_path / "e")])
    assert rc == 0
    assert (tmp_path / "d.html").exists() and (tmp_path / "e" / "forecast.csv").exists()
