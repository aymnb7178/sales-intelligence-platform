"""Shared fixtures: a small SYNTHETIC in-memory database."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sales_intel.config import GenConfig  # noqa: E402
from sales_intel.datagen import generate  # noqa: E402
from sales_intel.db import build_database  # noqa: E402


@pytest.fixture(scope="session")
def frames():
    return generate(GenConfig(n_customers=300, seed=7))


@pytest.fixture()
def conn(frames):
    c = build_database(":memory:", frames)
    yield c
    c.close()
