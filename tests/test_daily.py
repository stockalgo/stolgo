from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from stolgo.report.daily import build_daily, sessions_from_ohlcv


def test_two_trades_same_session_sum():
    sessions = pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"])
    trades = pd.DataFrame(
        {
            "entry_ts": [
                pd.Timestamp("2024-01-01 04:00:00+00:00"),
                pd.Timestamp("2024-01-01 05:00:00+00:00"),
            ],
            "exit_ts": [
                pd.Timestamp("2024-01-01 09:00:00+00:00"),
                pd.Timestamp("2024-01-01 09:30:00+00:00"),
            ],
            "net_pnl": [150.0, 250.0],
        }
    )
    daily = build_daily(trades, capital=10000.0, sessions=sessions)
    assert len(daily) == 1
    assert daily.iloc[0]["pnl"] == 400.0
    assert daily.iloc[0]["trades_closed"] == 2
    assert daily.iloc[0]["equity"] == 10400.0


def test_idle_sessions_are_zero():
    sessions = pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"])
    trades = pd.DataFrame(
        {
            "entry_ts": [pd.Timestamp("2024-01-01 04:00:00+00:00")],
            "exit_ts": [pd.Timestamp("2024-01-03 09:00:00+00:00")],
            "net_pnl": [500.0],
        }
    )
    daily = build_daily(trades, capital=10000.0, sessions=sessions)
    assert len(daily) == 3
    assert daily.iloc[0]["session"] == "2024-01-01"
    assert daily.iloc[0]["pnl"] == 0.0
    assert daily.iloc[0]["trades_closed"] == 0
    assert daily.iloc[1]["session"] == "2024-01-02"
    assert daily.iloc[1]["pnl"] == 0.0
    assert daily.iloc[1]["trades_closed"] == 0
    assert daily.iloc[2]["session"] == "2024-01-03"
    assert daily.iloc[2]["pnl"] == 500.0
    assert daily.iloc[2]["trades_closed"] == 1


def test_exit_on_non_session_date_raises():
    sessions = pd.DatetimeIndex(["2024-01-01", "2024-01-02"])
    trades = pd.DataFrame(
        {
            "entry_ts": [pd.Timestamp("2024-01-01 04:00:00+00:00")],
            "exit_ts": [pd.Timestamp("2024-01-05 09:00:00+00:00")],
            "net_pnl": [100.0],
        }
    )
    with pytest.raises(ValueError, match="2024-01-05"):
        build_daily(trades, capital=10000.0, sessions=sessions)


def test_drawdown_includes_initial_capital():
    # A first-day loss of 10 on capital 100 gives drawdown -0.10
    sessions = pd.DatetimeIndex(["2024-01-01", "2024-01-02"])
    trades = pd.DataFrame(
        {
            "entry_ts": [
                pd.Timestamp("2024-01-01 04:00:00+00:00"),
                pd.Timestamp("2024-01-02 04:00:00+00:00"),
            ],
            "exit_ts": [
                pd.Timestamp("2024-01-01 09:00:00+00:00"),
                pd.Timestamp("2024-01-02 09:00:00+00:00"),
            ],
            "net_pnl": [-10.0, 5.0],
        }
    )
    daily = build_daily(trades, capital=100.0, sessions=sessions)
    assert np.isclose(daily.iloc[0]["drawdown"], -0.10)
    assert np.isclose(daily.iloc[1]["drawdown"], -0.05)


def test_sessions_from_ohlcv():
    ohlcv = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
        },
        index=pd.DatetimeIndex([
            "2024-01-01 03:45:00+00:00",
            "2024-01-02 03:45:00+00:00",
        ], name="timestamp"),
    )
    sessions = sessions_from_ohlcv(ohlcv)
    assert len(sessions) == 2
    assert sessions[0] == pd.Timestamp("2024-01-01")
    assert sessions[1] == pd.Timestamp("2024-01-02")
