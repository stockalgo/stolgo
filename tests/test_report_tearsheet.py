"""Tests for stolgo.report.tearsheet (M3)."""

from pathlib import Path

import pandas as pd
import pytest

from stolgo.report import Report


def test_html_contains_plotly_and_traces(tmp_path):
    index = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    equity = pd.Series([100.0, 101.0, 102.0, 101.0, 103.0], index=index)
    ohlcv = pd.DataFrame(
        {
            "open": [100, 101, 102, 101, 103],
            "high": [101, 102, 103, 102, 104],
            "low": [99, 100, 101, 100, 102],
            "close": [100.5, 101.5, 102.5, 101.5, 103.5],
            "volume": [1000] * 5,
        },
        index=index,
    )
    trades = pd.DataFrame(
        {
            "entry_ts": [index[1]],
            "exit_ts": [index[3]],
            "entry_price": [101.0],
            "exit_price": [102.0],
        }
    )
    path = tmp_path / "t.html"
    Report(equity, trades, ohlcv=ohlcv, metrics={"total_return": 0.03}).to_html(path)
    html = path.read_text().lower()
    assert "plotly" in html
    assert "equity" in html
    assert "drawdown" in html


def test_m3_tearsheet_from_backtest(synthetic_100bars_df):
    from stolgo import Backtest, Strategy
    from stolgo.strategy.context import Context

    class BuySell(Strategy):
        def on_bar(self, ctx: Context) -> None:
            if ctx.i == 10 and ctx.position.flat:
                ctx.buy(qty=5.0)
            if ctx.i == 50 and not ctx.position.flat:
                ctx.close()

    result = Backtest(BuySell(), synthetic_100bars_df, cash=100_000).run()
    assert len(result.trades) >= 1
    path = Path("stolgo_tearsheet_test.html")
    result.report.to_html(path)
    html = path.read_text().lower()
    assert "plotly" in html
    path.unlink(missing_ok=True)
