"""Configuration constants and dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"

DEFAULT_DB = PROJECT_ROOT / "data" / "sales.db"
DEFAULT_CHARTS_DIR = PROJECT_ROOT / "docs"
DEFAULT_DASHBOARD = PROJECT_ROOT / "docs" / "sample_dashboard.html"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "output" / "powerbi_csv"


@dataclass(frozen=True)
class GenConfig:
    """Parameters of the SYNTHETIC data generator."""

    n_customers: int = 1500
    products_per_category: int = 10
    start: str = "2022-01-01"
    end: str = "2025-12-31"
    seed: int = 42


@dataclass(frozen=True)
class AnalysisConfig:
    """Parameters of the analytics layer."""

    holdout_months: int = 6
    forecast_horizon: int = 6
    top_n: int = 10
    abc_a_threshold: float = 80.0
    abc_b_threshold: float = 95.0
