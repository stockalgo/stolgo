"""Tests reproducing engine and report correctness bugs from Plan 04."""

import numpy as np
import pandas as pd
import pytest

from stolgo import Backtest, Strategy

idx = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")


def frame(px, spread=1.0):
    px = np.asarray(px, float)
    return pd.DataFrame(
        {
            "open": px,
            "high": px + spread,
            "low": px - spread,
            "close": px,
            "volume": 1.0,
        },
        index=idx[: len(px)],
    )


def test_short_round_trip():
    class ShortRT(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 2:
                ctx.sell(qty=10)
            if ctx.i == 6:
                ctx.buy(qty=10)

    # Prices: [100, 101, 102, 103, 104, 103, 102, 101, 100, 99]
    # On bar 2 (close 102), ctx.sell(qty=10) -> fills on bar 3 open = 103
    # On bar 6 (close 102), ctx.buy(qty=10) -> fills on bar 7 open = 101
    r = Backtest(ShortRT(), frame([100, 101, 102, 103, 104, 103, 102, 101, 100, 99]), cash=10_000).run()
    assert len(r.trades) == 1
    t = r.trades.iloc[0]
    assert t["side"] == "SHORT"
    assert t["entry_price"] == 103.0
    assert t["exit_price"] == 101.0
    assert t["qty"] == 10.0
    assert t["gross_pnl"] == 20.0
