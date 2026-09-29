"""Golden-shape tests for UI adapters."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stolgo.ui import adapters


def test_clean_helper() -> None:
    raw = {
        "nan": float("nan"),
        "inf": float("inf"),
        "neg_inf": float("-inf"),
        "val": 42.5,
        "bool": False,
        "int": np.int64(7),
        "nested": [float("nan"), 10],
    }
    cleaned = adapters._clean(raw)
    assert cleaned["nan"] is None
    assert cleaned["inf"] is None
    assert cleaned["neg_inf"] is None
    assert cleaned["val"] == 42.5
    assert cleaned["bool"] is False
    assert cleaned["int"] == 7
    assert cleaned["nested"] == [None, 10]


def test_run_summary_v2_and_detail_v2() -> None:
    manifest = {
        "schema_version": 2,
        "run_id": "run-test",
        "name": "Test Run",
        "status": "ok",
        "status_reasons": [],
        "instrument": {"markets": ["NIFTY"], "structure": "short_strangle", "dte": [0]},
        "group": {"id": "g-1", "label": "Group 1", "axes": {"market": "NIFTY"}},
        "window": {"start": "2023-01-01", "end": "2023-12-31", "sessions": 250},
        "config": {"capital": 200000.0},
        "metrics": {
            "net_pnl": 15000.0,
            "total_return": 0.075,
            "cagr": 0.075,
            "sharpe": 1.25,
            "max_drawdown": -0.05,
            "profit_factor": 1.6,
            "hit_rate": 0.6,
            "num_trades": 50,
            "expectancy": 300.0,
            "annualised_from_short_window": False,
        },
        "robustness": {"p_net_positive": 0.95, "net_without_top5": 10000.0},
        "diagnostics": {
            "data_quality": {"trades_with_missing_data": 0, "trades_total": 50},
        },
        "has": {"ohlcv": True, "legs": True, "intraday_equity": False, "audit": False},
        "created_at": "2026-09-28T12:00:00+00:00",
    }

    summary = adapters.run_summary_v2(manifest)
    assert summary["id"] == "run-test"
    assert summary["name"] == "Test Run"
    assert summary["status"] == "ok"
    assert summary["markets"] == ["NIFTY"]
    assert summary["structure"] == "short_strangle"
    assert summary["dte"] == [0]
    assert summary["group"]["id"] == "g-1"
    assert summary["window"]["sessions"] == 250
    assert summary["capital"] == 200000.0
    assert summary["metrics"]["sharpe"] == 1.25
    assert summary["robustness"]["p_net_positive"] == 0.95
    assert summary["data_quality"]["trades_with_missing_data"] == 0
    assert summary["has"]["ohlcv"] is True

    detail = adapters.run_detail_v2(manifest)
    assert "instrument" in detail
    assert "config" in detail
    assert "metric_defs" in detail
    assert len(detail["metric_defs"]) > 0
    assert any(m["key"] == "sharpe" for m in detail["metric_defs"])


def test_trades_v2_rows() -> None:
    df = pd.DataFrame(
        {
            "trade_id": [1, 2],
            "session_date": ["2023-01-02", "2023-01-03"],
            "entry_ts": [
                pd.Timestamp("2023-01-02 03:45:00", tz="UTC"),
                pd.Timestamp("2023-01-03 03:45:00", tz="UTC"),
            ],
            "exit_ts": [
                pd.Timestamp("2023-01-02 09:45:00", tz="UTC"),
                pd.Timestamp("2023-01-03 09:45:00", tz="UTC"),
            ],
            "net_pnl": [500.0, float("nan")],
            "r_multiple": [1.5, float("nan")],
        }
    )
    res = adapters.trades_v2_rows(df)
    assert "rows" in res and "columns" in res
    assert res["columns"] == ["trade_id", "session_date", "entry_ts", "exit_ts", "net_pnl", "r_multiple"]
    assert len(res["rows"]) == 2
    assert isinstance(res["rows"][0]["entry_ts"], int)
    assert res["rows"][1]["net_pnl"] is None
    assert res["rows"][1]["r_multiple"] is None


def test_daily_and_monthly_rows() -> None:
    daily_df = pd.DataFrame(
        {
            "session": ["2023-01-02", "2023-01-03", "2023-02-01"],
            "pnl": [100.0, 200.0, -50.0],
            "equity": [100100.0, 100300.0, 100250.0],
            "drawdown": [0.0, 0.0, -0.0005],
            "trades_closed": [1, 2, 1],
        }
    )
    d_res = adapters.daily_rows(daily_df)
    assert len(d_res["rows"]) == 3
    assert d_res["rows"][0]["session"] == "2023-01-02"
    assert d_res["rows"][0]["pnl"] == 100.0

    m_res = adapters.monthly_rows(daily_df, capital=100000.0)
    assert len(m_res["rows"]) == 2
    jan = m_res["rows"][0]
    assert jan["month"] == "2023-01"
    assert jan["pnl"] == 300.0
    assert jan["return_pct"] == pytest.approx(0.003)
    assert jan["trades"] == 3


def test_candles_and_trade_detail() -> None:
    idx = pd.date_range("2023-01-02 03:45:00", periods=5, freq="15min", tz="UTC")
    ohlcv = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [102.0, 103.0, 104.0, 105.0, 106.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0],
            "volume": [10, 20, 30, 40, 50],
        },
        index=idx,
    )

    c_1d = adapters.candles(ohlcv, tf="1D")
    assert len(c_1d["rows"]) == 1
    assert c_1d["rows"][0]["open"] == 100.0
    assert c_1d["rows"][0]["close"] == 105.0

    trades_df = pd.DataFrame(
        {
            "trade_id": [1],
            "session_date": ["2023-01-02"],
            "entry_ts": [idx[0]],
            "exit_ts": [idx[-1]],
            "net_pnl": [50.0],
        }
    )
    legs_df = pd.DataFrame(
        {
            "trade_id": [1, 1],
            "leg_id": [1, 2],
            "action": ["SELL", "SELL"],
            "entry_ts": [idx[0], idx[0]],
            "exit_ts": [idx[-1], idx[-1]],
        }
    )

    detail = adapters.trade_detail(trades_df, legs_df, ohlcv, trade_id=1)
    assert detail["trade"]["trade_id"] == 1
    assert len(detail["legs"]) == 2
    assert len(detail["bars"]) == 5

    # With matching market
    trades_df_mkt = trades_df.copy()
    trades_df_mkt["market"] = "NIFTY"
    detail_matching = adapters.trade_detail(trades_df_mkt, legs_df, ohlcv, trade_id=1, ohlcv_market="NIFTY")
    assert len(detail_matching["bars"]) == 5

    # With mismatched market (e.g. SENSEX trade with NIFTY bars)
    trades_df_mkt["market"] = "SENSEX"
    detail_mismatch = adapters.trade_detail(trades_df_mkt, legs_df, ohlcv, trade_id=1, ohlcv_market="NIFTY")
    assert len(detail_mismatch["bars"]) == 0

    with pytest.raises(KeyError):
        adapters.trade_detail(trades_df, legs_df, ohlcv, trade_id=999)
