"""Shared pytest fixtures for stolgo backtest tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def pytest_collection_modifyitems(config, items):
    """Skip legacy tests that import pre-greenfield stolgo modules."""
    skip_legacy = pytest.mark.skip(reason="legacy stolgo module; greenfield backtest tests only")
    for item in items:
        if "test_nse_option_chain" in item.nodeid:
            item.add_marker(skip_legacy)


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture
def synthetic_100bars_df() -> pd.DataFrame:
    path = FIXTURE_DIR / "synthetic_100bars.csv"
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.set_index("timestamp")


@pytest.fixture
def run_config_defaults() -> dict:
    return {
        "mode": "backtest",
        "seed": 42,
        "cash": 100_000.0,
        "commission": 0.0,
        "slippage_bps": 0.0,
        "fill_on": "next_open",
        "fast": False,
    }


@pytest.fixture
def mock_bandl_client():
    """Offline bandl double — no network (IMPLEMENTATION_PLAN §G.3)."""

    class _MockFacet:
        def get_ohlcv_dataframe(self, symbol, interval, start, end, **kwargs):
            path = FIXTURE_DIR / "bandl_btcusdt_1h_mock.json"
            rows = json.loads(path.read_text())
            df = pd.DataFrame(rows)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            return df

    class _Mock:
        crypto = _MockFacet()
        equity = _MockFacet()

    return _Mock()
