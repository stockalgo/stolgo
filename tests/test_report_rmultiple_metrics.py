"""Tests for stolgo.report.rmultiple_metrics (deterministic, no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from stolgo.report.rmultiple_metrics import compute_rmultiple_metrics


def _trades_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC", "DDD", "EEE"],
            "r_multiple": [4.0, -1.0, 4.0, -1.0, -1.0],
            "outcome": ["win", "loss", "win", "loss", "loss"],
            "holding_period_days": [5, 1, 3, 2, 4],
            "exit_date": pd.to_datetime(
                ["2026-01-06", "2026-01-03", "2026-01-10", "2026-01-08", "2026-01-12"], utc=True
            ),
        }
    )


def test_win_rate_and_expectancy() -> None:
    m = compute_rmultiple_metrics(_trades_df())
    assert m["total_trades"] == 5
    assert m["closed_trades"] == 5
    assert m["win_rate"] == pytest.approx(2 / 5)
    assert m["avg_r_multiple"] == pytest.approx((4 - 1 + 4 - 1 - 1) / 5)
    # profit_factor = gross_profit / gross_loss = (4+4) / (1+1+1) = 8/3
    assert m["profit_factor"] == pytest.approx(8 / 3)
    assert m["best_trade_r"] == pytest.approx(4.0)
    assert m["worst_trade_r"] == pytest.approx(-1.0)
    assert m["avg_holding_period_days"] == pytest.approx((5 + 1 + 3 + 2 + 4) / 5)


def test_equity_curve_and_max_drawdown_r() -> None:
    m = compute_rmultiple_metrics(_trades_df())
    # trades sorted by exit_date: BBB(-1), AAA(4), DDD(-1), CCC(4), EEE(-1)
    # cumulative R: -1, 3, 2, 6, 5
    expected_curve = [-1.0, 3.0, 2.0, 6.0, 5.0]
    assert list(m["equity_curve_r"].to_numpy()) == pytest.approx(expected_curve)
    # peak-to-trough drops: (-1 -> -1)=0 dd; peak 3 -> trough 2 => -1; peak 6 -> trough 5 => -1
    assert m["max_drawdown_r"] == pytest.approx(-1.0)


def test_open_trades_excluded_from_closed_stats() -> None:
    df = _trades_df()
    df.loc[len(df)] = ["FFF", 0.0, "open", 0, pd.NaT]
    m = compute_rmultiple_metrics(df)
    assert m["total_trades"] == 6
    assert m["open_trades"] == 1
    assert m["closed_trades"] == 5


def test_empty_trades_returns_zeroed_metrics() -> None:
    empty = pd.DataFrame(columns=["r_multiple", "outcome", "holding_period_days", "exit_date"])
    m = compute_rmultiple_metrics(empty)
    assert m["total_trades"] == 0
    assert m["win_rate"] == 0.0


def test_missing_required_column_raises() -> None:
    df = _trades_df().drop(columns=["outcome"])
    with pytest.raises(ValueError):
        compute_rmultiple_metrics(df)
