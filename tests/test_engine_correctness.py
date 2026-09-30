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


def test_exit_not_blocked_by_drawdown():
    class Hold(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=100)
            if ctx.i == 4:
                ctx.close()

    r = Backtest(Hold(), frame([100, 100, 40, 40, 40, 30, 30, 30, 30, 30], 0), cash=10_000).run()
    assert r.positions.qty.iloc[-1] == 0
    assert len(r.trades) == 1

    # With halt_drawdown=0.5, a new buy after breach is rejected and close still goes through
    class BuyAfterHalt(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=100)
            if ctx.i == 3:
                ctx.buy(qty=50)  # should be rejected by risk halt
            if ctx.i == 4:
                ctx.close()  # should be accepted

    r2 = Backtest(
        BuyAfterHalt(),
        frame([100, 100, 40, 40, 40, 30, 30, 30, 30, 30], 0),
        cash=10_000,
        halt_drawdown=0.5,
    ).run()
    assert r2.positions.qty.iloc[-1] == 0
    assert len(r2.trades) == 1
    assert r2.trades.iloc[0]["qty"] == 100.0
    from stolgo.core.events import RiskHaltEvent
    halts = [e for e in r2.events if isinstance(e, RiskHaltEvent)]
    assert len(halts) == 1
    assert halts[0].drawdown >= 0.5


def test_size_pct_does_not_overspend_cash():
    class AllIn(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(size_pct=1.0)

    df = frame([100] + [150] * 9, 0)
    r = Backtest(AllIn(), df, cash=10_000, commission=0.001).run()
    cash_series = r.positions.equity - r.positions.qty * df["close"].values
    assert cash_series.min() >= 0
    # Fill qty should be around 10,000 / (150 * 1.001) = 66.6
    assert r.positions.qty.iloc[1] == pytest.approx(10_000 / (150 * 1.001), rel=1e-3)

    # When allow_leverage=False (default), buying more than cash allows emits ORDER_REJECTED
    class Overbuy(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=1000)  # Requires 150,000 but cash is 10,000

    r2 = Backtest(Overbuy(), df, cash=10_000, commission=0.001).run()
    assert r2.positions.qty.iloc[1] == 0
    from stolgo.core.events import OrderRejectedEvent
    rejections = [e for e in r2.events if isinstance(e, OrderRejectedEvent)]
    assert len(rejections) == 1
    assert rejections[0].reason == "insufficient_cash"
