"""Command line interface: ``python -m sales_intel <command>``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .analysis import run_analysis
from .charts import render_all
from .config import (
    DEFAULT_CHARTS_DIR,
    DEFAULT_DASHBOARD,
    DEFAULT_DB,
    DEFAULT_EXPORT_DIR,
    AnalysisConfig,
    GenConfig,
)
from .datagen import generate
from .db import build_database, connect
from .export import export_csvs
from .report import build_dashboard

log = logging.getLogger("sales_intel")


def _add_db(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")


def _add_gen(p: argparse.ArgumentParser) -> None:
    p.add_argument("--customers", type=int, default=GenConfig.n_customers, help="number of synthetic customers")
    p.add_argument("--seed", type=int, default=GenConfig.seed, help="random seed")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sales_intel", description="Sales analytics on SYNTHETIC retail data.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate synthetic data into SQLite")
    _add_db(g)
    _add_gen(g)

    k = sub.add_parser("kpis", help="print headline KPIs as JSON")
    _add_db(k)

    f = sub.add_parser("forecast", help="backtest and forecast monthly revenue")
    _add_db(f)
    f.add_argument("--holdout", type=int, default=AnalysisConfig.holdout_months)
    f.add_argument("--horizon", type=int, default=AnalysisConfig.forecast_horizon)

    r = sub.add_parser("report", help="write the self-contained HTML dashboard")
    _add_db(r)
    r.add_argument("--out", type=Path, default=DEFAULT_DASHBOARD)
    r.add_argument("--charts-dir", type=Path, default=DEFAULT_CHARTS_DIR)

    e = sub.add_parser("export", help="export BI-ready CSV files (Power BI import)")
    _add_db(e)
    e.add_argument("--out", type=Path, default=DEFAULT_EXPORT_DIR)

    a = sub.add_parser("all", help="generate -> analyse -> charts -> dashboard -> CSV export")
    _add_db(a)
    _add_gen(a)
    a.add_argument("--out", type=Path, default=DEFAULT_DASHBOARD)
    a.add_argument("--charts-dir", type=Path, default=DEFAULT_CHARTS_DIR)
    a.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    return p


def _require_db(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Database not found: {path}. Run `python -m sales_intel generate` first.")


def _print_backtest(a) -> None:  # noqa: ANN001
    bt = a.backtest
    print(f"Backtest: train on all but the last {bt.holdout} months, MAPE on the holdout")
    for name, v in sorted(bt.metrics.items(), key=lambda kv: kv[1]):
        print(f"  {name:<22} MAPE {v:6.2f}%")
    print(f"Best model: {bt.best_model} ({bt.improvement_vs_naive_pct:.1f}% lower MAPE than naive)")
    print(f"\nForecast (refit on all data, model={bt.best_model}):")
    print(a.forecast[["month", "forecast"]].to_string(index=False))


def _generate(args: argparse.Namespace):
    cfg = GenConfig(n_customers=args.customers, seed=args.seed)
    frames = generate(cfg)
    conn = build_database(args.db, frames)
    print(f"Wrote {args.db}: " + ", ".join(f"{k}={len(v):,}" for k, v in frames.items()))
    return conn


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    if args.command == "generate":
        _generate(args).close()
        return 0

    if args.command == "all":
        conn = _generate(args)
    else:
        _require_db(args.db)
        conn = connect(args.db)

    try:
        if args.command == "kpis":
            print(json.dumps(run_analysis(conn).kpis, indent=2, default=str))
            return 0
        if args.command == "forecast":
            cfg = AnalysisConfig(holdout_months=args.holdout, forecast_horizon=args.horizon)
            _print_backtest(run_analysis(conn, cfg))
            return 0

        analysis = run_analysis(conn)
        if args.command in ("report", "all"):
            charts = render_all(analysis, args.charts_dir)
            build_dashboard(analysis, charts, args.out)
            print(f"Dashboard: {args.out}")
            print(f"Charts:    {args.charts_dir} ({len(charts)} PNG files)")
        if args.command in ("export", "all"):
            out = args.export_dir if args.command == "all" else args.out
            counts = export_csvs(conn, analysis, out)
            print(f"CSV export ({out}): " + ", ".join(f"{k}={v:,}" for k, v in counts.items()))
        if args.command == "all":
            print(json.dumps({k: analysis.kpis[k] for k in ("revenue", "orders", "customers", "gross_margin_pct", "avg_order_value", "repeat_customer_rate_pct", "yoy_growth_last_12m_pct")}, indent=2))
            _print_backtest(analysis)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
