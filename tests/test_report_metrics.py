"""Tests for stolgo.report.metrics."""

import numpy as np
import pandas as pd

from stolgo.report.metrics import compute_metrics


def test_metrics_on_uptrend():
    equity = pd.Series(np.linspace(100, 110, 252))
    trades = pd.DataFrame({"net_pnl": [1.0, -0.5, 2.0], "qty": [1, 1, 1], "entry_price": [1, 1, 1], "exit_price": [1, 1, 1]})
    m = compute_metrics(equity, trades)
    assert m["total_return"] > 0
    assert m["num_trades"] == 3
    assert m["hit_rate"] > 0
    assert "sharpe" in m
    assert "sortino" in m
    assert "calmar" in m


def test_zero_trades_safe():
    equity = pd.Series([100.0, 100.0])
    m = compute_metrics(equity, pd.DataFrame())
    assert m["num_trades"] == 0
    assert m["expectancy"] == 0


def test_sortino_formula():
    rets = np.array([0.01, -0.02, 0.01, 0.0])
    equity = pd.Series(100.0 * np.cumprod(np.insert(1.0 + rets, 0, 1.0)))
    m = compute_metrics(equity, pd.DataFrame())
    downside_rms = np.sqrt(np.mean(np.minimum(rets, 0.0) ** 2))
    expected_sortino = float(rets.mean() / downside_rms * np.sqrt(252.0))
    assert np.isclose(m["sortino"], expected_sortino)


def test_no_losses_profit_factor_nan():
    equity = pd.Series([100.0, 105.0])
    trades = pd.DataFrame({"net_pnl": [10.0, 20.0]})
    m = compute_metrics(equity, trades)
    assert np.isnan(m["profit_factor"])
    assert np.isnan(m["payoff"])
