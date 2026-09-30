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


def test_limit_intent_fills_and_gap_improvement():
    from stolgo.core.types import OrderIntent, OrderType, Side

    # Test 1: Limit buy fills at limit
    class LimitStrat(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx._intents.append(
                    OrderIntent(
                        symbol=ctx.position.symbol,
                        side=Side.BUY,
                        order_type=OrderType.LIMIT,
                        qty=10,
                        limit_price=95.0,
                    )
                )

    # Bar 0: open 100, close 100
    # Bar 1: open 98, high 102, low 94, close 99 (bar opens at 98, goes down to 94 through 95)
    df1 = pd.DataFrame(
        {
            "open": [100.0, 98.0, 99.0],
            "high": [101.0, 102.0, 100.0],
            "low": [99.0, 94.0, 98.0],
            "close": [100.0, 99.0, 99.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=idx[:3],
    )
    r1 = Backtest(LimitStrat(), df1, cash=10_000).run()
    assert len(r1.trades) == 0  # Not closed yet, but position opened
    assert r1.positions.qty.iloc[1] == 10.0
    fill = [e.fill for e in r1.events if hasattr(e, "fill")][0]
    assert fill.price == 95.0

    # Test 2: Gap-through open fills at open (min(open, limit) = 90)
    df2 = pd.DataFrame(
        {
            "open": [100.0, 90.0, 91.0],
            "high": [101.0, 92.0, 92.0],
            "low": [99.0, 89.0, 90.0],
            "close": [100.0, 91.0, 91.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=idx[:3],
    )
    r2 = Backtest(LimitStrat(), df2, cash=10_000).run()
    assert r2.positions.qty.iloc[1] == 10.0
    fill2 = [e.fill for e in r2.events if hasattr(e, "fill")][0]
    assert fill2.price == 90.0


def test_stop_limit_raises_not_implemented():
    from stolgo.core.types import OrderIntent, OrderType, Side

    class StopLimitStrat(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx._intents.append(
                    OrderIntent(
                        symbol=ctx.position.symbol,
                        side=Side.BUY,
                        order_type=OrderType.STOP_LIMIT,
                        qty=10,
                        stop_price=105.0,
                        limit_price=106.0,
                    )
                )

    with pytest.raises(NotImplementedError):
        Backtest(StopLimitStrat(), frame([100, 101, 102], 0), cash=10_000).run()


def test_oco_both_hit_on_same_bar_fills_stop():
    from stolgo.core.types import OrderIntent, OrderType, Side

    class OCOStrat(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                # Target limit at 110, stop at 90 with same oco_group
                ctx._intents.append(
                    OrderIntent(
                        symbol=ctx.position.symbol,
                        side=Side.SELL,
                        order_type=OrderType.LIMIT,
                        qty=10,
                        limit_price=110.0,
                        oco_group="bracket-1",
                    )
                )
                ctx._intents.append(
                    OrderIntent(
                        symbol=ctx.position.symbol,
                        side=Side.SELL,
                        order_type=OrderType.STOP,
                        qty=10,
                        stop_price=90.0,
                        oco_group="bracket-1",
                    )
                )

    # Bar 0: open 100, close 100
    # Bar 1: wide bar: open 100, high 115, low 85, close 100 (both 110 limit and 90 stop hit)
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 115.0, 101.0],
            "low": [99.0, 85.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=idx[:3],
    )
    r = Backtest(OCOStrat(), df, cash=10_000).run()
    fills = [e.fill for e in r.events if hasattr(e, "fill")]
    assert len(fills) == 1
    # Adverse-first: fill the STOP order (at stop price 90.0)
    assert fills[0].price == 90.0


def test_fill_on_modes():
    class SignalOnBar1(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 1:
                ctx.buy(qty=10)

    # Bar 0: open 100.0, close 100.0
    # Bar 1: open 101.0, close 101.2
    # Bar 2: open 102.0, close 102.2
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [100.5, 101.5, 102.5],
            "low": [99.5, 100.5, 101.5],
            "close": [100.0, 101.2, 102.2],
            "volume": [1.0, 1.0, 1.0],
        },
        index=idx[:3],
    )

    # 1. next_open (default): fills at bar 2 open = 102.0
    r_open = Backtest(SignalOnBar1(), df, cash=10_000, fill_on="next_open").run()
    fills_open = [e.fill for e in r_open.events if hasattr(e, "fill")]
    assert len(fills_open) == 1
    assert fills_open[0].price == 102.0

    # 2. next_close: fills at bar 2 close = 102.2
    r_next_close = Backtest(SignalOnBar1(), df, cash=10_000, fill_on="next_close").run()
    fills_nc = [e.fill for e in r_next_close.events if hasattr(e, "fill")]
    assert len(fills_nc) == 1
    assert fills_nc[0].price == 102.2

    # Deprecated alias "close" gives warning and fills at 102.2
    with pytest.deprecated_call():
        r_dep = Backtest(SignalOnBar1(), df, cash=10_000, fill_on="close").run()
    fills_dep = [e.fill for e in r_dep.events if hasattr(e, "fill")]
    assert len(fills_dep) == 1
    assert fills_dep[0].price == 102.2

    # 3. signal_close: fills at bar 1 close = 101.2
    r_sig = Backtest(SignalOnBar1(), df, cash=10_000, fill_on="signal_close").run()
    fills_sig = [e.fill for e in r_sig.events if hasattr(e, "fill")]
    assert len(fills_sig) == 1
    assert fills_sig[0].price == 101.2


def test_bracket_sizing_and_intrabar_stop():
    from stolgo.trade import long

    class BracketStrat(Strategy):
        def __init__(self):
            self.b = None

        def on_bar(self, ctx):
            if ctx.i == 0:
                # equity = 10,000, risk 2% = 200 risk
                # bar 0: close 100, low 95 -> risk_per_unit = 5
                # expected qty = 200 / 5 = 40
                self.b = long(ctx, stop="candle_low", size_risk_pct=0.02, rr=(1, 2))

    # Case 1: Intrabar stop hit on bar 1
    # Bar 0: open 100, high 105, low 95, close 100
    # Bar 1: open 100 (fills entry at 100), high 102, low 94 (touches stop 95 intrabar), close 96
    df1 = pd.DataFrame(
        {
            "open": [100.0, 100.0],
            "high": [105.0, 102.0],
            "low": [95.0, 94.0],
            "close": [100.0, 96.0],
            "volume": [1.0, 1.0],
        },
        index=idx[:2],
    )
    r1 = Backtest(BracketStrat(), df1, cash=10_000).run()
    assert len(r1.trades) == 1
    t1 = r1.trades.iloc[0]
    assert t1.side == "LONG"
    assert t1.entry_price == 100.0
    assert t1.qty == 40.0
    assert t1.exit_price == 95.0

    # Case 2: Gap down on bar 2 below stop 95 -> exits at gap open
    df2 = pd.DataFrame(
        {
            "open": [100.0, 100.0, 90.0],
            "high": [105.0, 102.0, 92.0],
            "low": [95.0, 98.0, 89.0],
            "close": [100.0, 99.0, 91.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=idx[:3],
    )
    r2 = Backtest(BracketStrat(), df2, cash=10_000).run()
    assert len(r2.trades) == 1
    t2 = r2.trades.iloc[0]
    assert t2.side == "LONG"
    assert t2.entry_price == 100.0
    assert t2.qty == 40.0
    assert t2.exit_price == 90.0


def test_r_multiple_vs_return_on_notional():
    from stolgo.trade import long

    class NoBracketStrat(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=10)
            elif ctx.i == 1:
                ctx.sell(qty=10)

    # 1. Trade without bracket: return_on_notional is set, r_multiple is NaN
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 110.0],
            "high": [101.0, 101.0, 111.0],
            "low": [99.0, 99.0, 109.0],
            "close": [100.0, 100.0, 110.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=idx[:3],
    )
    r1 = Backtest(NoBracketStrat(), df, cash=10_000).run()
    assert len(r1.trades) == 1
    t1 = r1.trades.iloc[0]
    assert "return_on_notional" in r1.trades.columns
    assert t1.return_on_notional == pytest.approx(0.1)  # 100 net / 1000 notional
    assert np.isnan(t1.r_multiple)

    # 2. Trade with bracket: risk per unit known, r_multiple is set
    class BracketStrat(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                long(ctx, stop="candle_low", qty=10, rr=(1, 2))

    # bar 0: close 100, low 95 -> risk_per_unit = 5. target = 110
    # bar 1: open 100, high 112 (hits target 110 intrabar), low 99, close 111
    df2 = pd.DataFrame(
        {
            "open": [100.0, 100.0],
            "high": [105.0, 112.0],
            "low": [95.0, 99.0],
            "close": [100.0, 111.0],
            "volume": [1.0, 1.0],
        },
        index=idx[:2],
    )
    r2 = Backtest(BracketStrat(), df2, cash=10_000).run()
    assert len(r2.trades) == 1
    t2 = r2.trades.iloc[0]
    assert t2.exit_price == 110.0
    assert t2.return_on_notional == pytest.approx(0.1)  # 100 / 1000
    assert t2.r_multiple == pytest.approx(2.0)  # 10 gain / 5 risk per unit



