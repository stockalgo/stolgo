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
    assert r1.positions.qty.iloc[1] == 10.0
    fill = [e.fill for e in r1.events if hasattr(e, "fill") and getattr(e.fill, "tag", None) != "END_OF_DATA"][0]
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
    fill2 = [e.fill for e in r2.events if hasattr(e, "fill") and getattr(e.fill, "tag", None) != "END_OF_DATA"][0]
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
    fills = [e.fill for e in r.events if hasattr(e, "fill") and getattr(e.fill, "tag", None) != "END_OF_DATA"]
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
    fills_open = [e.fill for e in r_open.events if hasattr(e, "fill") and getattr(e.fill, "tag", None) != "END_OF_DATA"]
    assert len(fills_open) == 1
    assert fills_open[0].price == 102.0

    # 2. next_close: fills at bar 2 close = 102.2
    r_next_close = Backtest(SignalOnBar1(), df, cash=10_000, fill_on="next_close").run()
    fills_nc = [e.fill for e in r_next_close.events if hasattr(e, "fill") and getattr(e.fill, "tag", None) != "END_OF_DATA"]
    assert len(fills_nc) == 1
    assert fills_nc[0].price == 102.2

    # Deprecated alias "close" gives warning and fills at 102.2
    with pytest.deprecated_call():
        r_dep = Backtest(SignalOnBar1(), df, cash=10_000, fill_on="close").run()
    fills_dep = [e.fill for e in r_dep.events if hasattr(e, "fill") and getattr(e.fill, "tag", None) != "END_OF_DATA"]
    assert len(fills_dep) == 1
    assert fills_dep[0].price == 102.2

    # 3. signal_close: fills at bar 1 close = 101.2
    r_sig = Backtest(SignalOnBar1(), df, cash=10_000, fill_on="signal_close").run()
    fills_sig = [e.fill for e in r_sig.events if hasattr(e, "fill") and getattr(e.fill, "tag", None) != "END_OF_DATA"]
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


def test_close_at_end_true_and_false():
    class BuyAndHold(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=10)

    # 3 bars: 100, 105, 110
    df = pd.DataFrame(
        {
            "open": [100.0, 105.0, 110.0],
            "high": [102.0, 107.0, 112.0],
            "low": [99.0, 104.0, 109.0],
            "close": [101.0, 106.0, 111.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=idx[:3],
    )

    # 1. close_at_end=True (default): position is closed at end of data at bar 2 close
    r_true = Backtest(BuyAndHold(), df, cash=10_000, close_at_end=True).run()
    assert len(r_true.trades) == 1
    t_true = r_true.trades.iloc[0]
    assert t_true.exit_price == 111.0
    assert t_true.tag == "END_OF_DATA" or getattr(t_true, "exit_reason", None) == "END_OF_DATA"
    assert r_true.positions.qty.iloc[-1] == 0.0

    # 2. close_at_end=False: trade row emitted with exit_reason="OPEN" and net_pnl = MTM
    r_false = Backtest(BuyAndHold(), df, cash=10_000, close_at_end=False).run()
    assert len(r_false.trades) == 1
    t_false = r_false.trades.iloc[0]
    assert t_false.tag == "OPEN" or getattr(t_false, "exit_reason", None) == "OPEN"
    assert t_false.net_pnl == pytest.approx((111.0 - 105.0) * 10.0)  # entered at bar 1 open 105, marked at bar 2 close 111
    assert r_false.positions.qty.iloc[-1] == 10.0  # position still open in portfolio


def test_lookahead_probe():
    from stolgo.core.lookahead import probe
    from stolgo.core.exceptions import LookaheadError

    # 1. Non-causal strategy: entries leak future data by looking 1 bar ahead
    class NonCausalStrat(Strategy):
        def on_start(self, ctx):
            close = ctx.data.close
            # Lookahead: shifted by -1 so it looks at tomorrow's close
            self.entries = np.r_[close[1:] > close[:-1], False]
            self.exits = np.zeros(len(close), dtype=bool)

    df = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(20)],
            "high": [101.0 + i for i in range(20)],
            "low": [99.0 + i for i in range(20)],
            "close": [100.0 + i for i in range(20)],
            "volume": [1.0] * 20,
        },
        index=pd.date_range("2024-01-01", periods=20, freq="D", tz="UTC"),
    )

    with pytest.raises(LookaheadError):
        probe(NonCausalStrat, df)

    with pytest.raises(LookaheadError):
        Backtest(NonCausalStrat(), df, cash=10_000, lookahead_check=True).run()

    # 2. Causal vector strategy passes
    class CausalStrat(Strategy):
        def on_start(self, ctx):
            close = ctx.data.close
            # Strictly backward-looking (mom > 0)
            self.entries = np.r_[False, close[1:] > close[:-1]]
            self.exits = np.zeros(len(close), dtype=bool)

    probe(CausalStrat, df)
    res = Backtest(CausalStrat(), df, cash=10_000, lookahead_check=True).run()
    assert len(res.equity) == 20


def test_lookahead_probe_examples():
    from stolgo.core.lookahead import probe
    from examples.vector_momentum_backtest import FastMomentum

    df = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(100)],
            "high": [101.0 + i for i in range(100)],
            "low": [99.0 + i for i in range(100)],
            "close": [100.0 + i for i in range(100)],
            "volume": [1.0] * 100,
        },
        index=pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC"),
    )
    probe(FastMomentum, df)


def test_parabolic_short_gap_stop():
    from stolgo.strategy.builtins.parabolic_short import (
        ParabolicShortConfig,
        detect_setups,
        simulate_trade,
    )
    from tests.test_strategy_parabolic_short import _RED_DAY, _build_df

    cfg = ParabolicShortConfig()
    # Base + Rally + Red Day: entry=28.0, stop=33.5 -> 1R = 5.5
    # Next day gaps up to open=35.15 (which is 28.0 + 1.3 * 5.5 = 1.3R above entry)
    tail = [
        _RED_DAY,
        (35.15, 36.0, 34.0, 34.5, 4000),  # open 35.15 > stop 33.5
    ]
    df = _build_df(tail)
    setups = detect_setups(df, cfg, symbol="TESTUSDT")
    assert len(setups) == 1
    trade = simulate_trade(df, setups[0], cfg)
    assert trade is not None
    assert trade.exit_reason == "stop"
    assert trade.exit_price == 35.15
    assert trade.r_multiple == pytest.approx(-1.3, abs=1e-4)


def test_accounting_error_raised():
    from stolgo.core.exceptions import AccountingError
    from stolgo.report.run_metrics import compute_run_metrics

    daily = pd.DataFrame({"session": ["2024-01-01", "2024-01-02"], "pnl": [100.0, -50.0]})
    trades = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "entry_time": pd.Timestamp("2024-01-01", tz="UTC"),
                "exit_time": pd.Timestamp("2024-01-02", tz="UTC"),
                "net_pnl": 200.0,
                "gross_pnl": 200.0,
                "fees": 0.0,
                "slippage": 0.0,
            }
        ]
    )
    with pytest.raises(AccountingError):
        compute_run_metrics(trades, 10_000.0, daily)


def test_export_all_mark_to_market_equity(tmp_path):
    import json
    from stolgo.report.exporters import export_all

    class HoldStrat(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=100)
            elif ctx.i == 2:
                ctx.close()

    # 3 daily bars: 100 -> 70 -> 101
    dt_idx = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0, 70.0, 101.0],
            "high": [100.0, 70.0, 101.0],
            "low": [100.0, 70.0, 101.0],
            "close": [100.0, 70.0, 101.0],
            "volume": [1.0, 1.0, 1.0],
        },
        index=dt_idx,
    )
    res = Backtest(HoldStrat(), df, cash=10_000, fill_on="signal_close").run()
    run_dir = tmp_path / "test_run"
    export_all(res, run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["metrics"]["equity_basis"] == "mark_to_market"
    assert manifest["metrics"]["max_drawdown"] == pytest.approx(-0.30, abs=0.001)


def test_btc_run_utc_and_24h_candles(tmp_path):
    import json
    from stolgo.report.exporters import export_all
    from stolgo.ui.adapters import candles

    class DummyStrat(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=1)
            elif ctx.i == 23:
                ctx.close()

    # 24 hourly bars covering 1 full UTC day: 2024-01-01 00:00 to 23:00 UTC
    dt_idx = pd.date_range("2024-01-01 00:00:00", periods=24, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [40000.0 + i for i in range(24)],
            "high": [40050.0 + i for i in range(24)],
            "low": [39950.0 + i for i in range(24)],
            "close": [40010.0 + i for i in range(24)],
            "volume": [10.0] * 24,
        },
        index=dt_idx,
    )
    res = Backtest(DummyStrat(), df, cash=100_000, symbol="BTCUSDT").run()
    run_dir = tmp_path / "btc_run"
    export_all(res, run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["instrument"]["timezone"] == "UTC"
    assert manifest["instrument"]["exchange"] is None
    assert manifest["instrument"]["currency"] is None
    assert manifest["instrument"]["markets"] == ["BTCUSDT"]

    # Read daily and candles
    daily = pd.read_parquet(run_dir / "parquet" / "daily.parquet")
    assert list(daily["session"]) == ["2024-01-01"]

    # 1H candles should cover all 24 hours of the day
    c = candles(df, tf="1H", tz="UTC", session_close="24:00")
    assert len(c["rows"]) == 24










