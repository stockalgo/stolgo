import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stolgo.report.daily import build_daily
from stolgo.report.run_metrics import compute_run_metrics

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_nifty_0dte_benchmark_metrics():
    trades_path = FIXTURES_DIR / "nifty_0dte_benchmark_trades.parquet"
    sessions_path = FIXTURES_DIR / "nse_sessions_2023_2026.parquet"

    trades = pd.read_parquet(trades_path)
    sessions_df = pd.read_parquet(sessions_path)
    sessions = pd.DatetimeIndex(sessions_df["session"])

    capital = 180000.0
    daily = build_daily(trades, capital, sessions)

    metrics = compute_run_metrics(trades, capital, daily)

    expected_path = Path(__file__).parent.parent / "docs/plans/fixtures/expected_after_migration.json"
    data = json.loads(expected_path.read_text())
    expected = data["runs"]["nifty-0dte-strangle-benchmark"]["expected"]

    # Assert total_return within rel=1e-6
    assert math.isclose(metrics["total_return"], expected["total_return"], rel_tol=1e-6)

    # Assert cagr, sharpe, sortino, max_drawdown within abs=1e-3
    assert math.isclose(metrics["cagr"], expected["cagr"], abs_tol=1e-3)
    assert math.isclose(metrics["sharpe"], expected["sharpe"], abs_tol=1e-3)
    assert math.isclose(metrics["sortino"], expected["sortino"], abs_tol=1e-3)
    assert math.isclose(metrics["max_drawdown"], expected["max_drawdown"], abs_tol=1e-3)

    # Specific benchmark values check
    assert math.isclose(metrics["total_return"], 0.168504, abs_tol=1e-5)
    assert math.isclose(metrics["cagr"], 0.053554, abs_tol=1e-3)
    assert math.isclose(metrics["sharpe"], 0.733541, abs_tol=1e-3)
    assert math.isclose(metrics["sortino"], 1.558107, abs_tol=1e-3)

    # Required keys present, no NaN or Inf
    for k, v in metrics.items():
        if isinstance(v, float):
            assert not np.isnan(v)
            assert not np.isinf(v)

    assert metrics["basis"] == "calendar_daily"
    assert metrics["annualised_from_short_window"] is False
