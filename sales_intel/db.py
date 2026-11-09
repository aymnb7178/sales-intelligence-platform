"""SQLite helpers: build the database and run the queries in ``sql/``."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .config import SQL_DIR

log = logging.getLogger(__name__)

TABLE_LOAD_ORDER = ["customers", "products", "orders", "order_items"]


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection (``":memory:"`` is allowed)."""
    return sqlite3.connect(str(path))


def read_sql_file(name: str) -> str:
    """Return the text of ``sql/<name>.sql``."""
    path = SQL_DIR / f"{name}.sql"
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes from ``sql/schema.sql``."""
    conn.executescript(read_sql_file("schema"))


def build_database(path: str | Path, frames: Mapping[str, pd.DataFrame]) -> sqlite3.Connection:
    """Create a fresh database at ``path`` and load the generated frames."""
    if str(path) != ":memory:":
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            p.unlink()
    conn = connect(path)
    create_schema(conn)
    for table in TABLE_LOAD_ORDER:
        frames[table].to_sql(table, conn, if_exists="append", index=False)
    conn.commit()
    log.info("Database ready at %s", path)
    return conn


def run_query(conn: sqlite3.Connection, name: str, params: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """Execute ``sql/<name>.sql`` through sqlite3 and return a DataFrame."""
    return pd.read_sql_query(read_sql_file(name), conn, params=dict(params or {}))
