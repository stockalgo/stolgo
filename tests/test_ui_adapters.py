"""Golden-shape tests for UI adapters."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stolgo.ui import adapters


def test_run_summary_and_metric_cards_types() -> None:
    manifest = {
        "run_id": "run-1",
        "strategy": "TrendBreakout",
        "params": {"symbol": "SYN", "interval": "1d"},
        "metrics": {
            "total_return": 0.12,
            "cagr": 0.03,
            "sharpe": 1.1,
            "max_drawdown": -0.04,
            "profit_factor": 1.8,
            "hit_rate": 0.55,
            "expectancy": 12.5,
            "num_trades": 7,
        },
        "created_at": "2026-07-06T10:00:00+00:00",
    }

    summary = adapters.run_summary(manifest)
    assert set(summary) == {
        "id",
        "strategy",
        "market",
        "timeframe",
        "return",
        "sharpe",
        "drawdown",
        "trades",
        "created_at",
    }
    assert isinstance(summary["trades"], int)

    cards = adapters.metric_cards(manifest["metrics"])
    assert all(set(card) == {"key", "label", "value", "fmt"} for card in cards)
    assert len(cards) == 8


def test_series_and_trades_match_frontend_mock_shapes(tmp_path) -> None:
    index = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    ohlcv = pd.DataFrame(
        {
            "open": [10.0, 11.0],
            "high": [12.0, 13.0],
            "low": [9.0, 10.0],
            "close": [11.0, 10.5],
            "volume": [100.0, 200.0],
        },
        index=index,
    )
    equity = pd.Series([100.0, 99.0], index=index)
    drawdown = pd.Series([0.0, -1.0], index=index)
    series = adapters.series(ohlcv, equity, drawdown)

    assert set(series) == {"candles", "volume", "equity", "drawdown"}
    assert set(series["candles"][0]) == {"time", "open", "high", "low", "close"}
    assert set(series["volume"][0]) == {"time", "value", "color"}
    assert set(series["equity"][0]) == {"time", "value"}
    assert set(series["drawdown"][0]) == {"time", "value"}
    assert isinstance(series["candles"][0]["time"], int)

    trades_df = pd.DataFrame(
        {
            "entry_ts": [index[0]],
            "exit_ts": [index[1]],
            "entry_price": [11.0],
            "exit_price": [10.5],
            "qty": [1.0],
            "net_pnl": [-0.5],
            "r_multiple": [-0.25],
            "tag": ["exit"],
        }
    )
    trades = adapters.trades(trades_df)
    assert set(trades[0]) == {
        "id",
        "entryTime",
        "exitTime",
        "entryPrice",
        "exitPrice",
        "qty",
        "pnl",
        "r",
        "side",
        "tag",
        "pnlClass",
    }
    assert trades[0]["side"] == "Long"
    assert isinstance(trades[0]["entryTime"], int)


def test_adapters_read_existing_output_dir_shape() -> None:
    output = Path("/tmp/stolgo_step2_run")
    if not output.exists():
        return
    manifest = json.loads((output / "manifest.json").read_text())
    ohlcv = pd.read_parquet(output / "parquet" / "ohlcv.parquet")
    equity = pd.read_parquet(output / "parquet" / "equity.parquet")["equity"]
    drawdown = pd.read_parquet(output / "parquet" / "drawdown.parquet")["drawdown"]
    trades = pd.read_parquet(output / "parquet" / "trades.parquet")

    assert adapters.run_summary(manifest)["id"] == "stolgo_step2_run"
    assert adapters.series(ohlcv, equity, drawdown)["candles"]
    assert adapters.trades(trades)
