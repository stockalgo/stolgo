"""Regression coverage for PR #100 order timing and callback visibility."""

import pandas as pd
import pytest

from stolgo import Backtest, Strategy
from stolgo.core.events import FillEvent
from stolgo.core.types import OrderType, Side


def _bars():
    return pd.DataFrame(
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1.0},
        index=pd.date_range("2024-01-01", periods=6, tz="UTC"),
    )


@pytest.mark.parametrize("fill_on", ["next_open", "next_close", "signal_close"])
@pytest.mark.parametrize("order_type", [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP])
def test_explicit_activation_defers_every_order_type(fill_on, order_type):
    class Deferred(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.order(
                    side=Side.BUY, order_type=order_type, qty=1, active_from=3,
                    limit_price=100.0, stop_price=100.0,
                )

    bars = _bars()
    bars.loc[bars.index[3], ["open", "high", "close"]] = [102.0, 104.0, 103.0]
    result = Backtest(Deferred(), bars, fill_on=fill_on, close_at_end=False).run()
    fills = [event for event in result.events if isinstance(event, FillEvent)]
    assert [event.index for event in fills] == [3]
    expected_price = 103.0 if fill_on in {"next_close", "signal_close"} else 102.0
    if order_type == OrderType.LIMIT:
        expected_price = 100.0
    elif order_type == OrderType.STOP:
        expected_price = 102.0
    assert fills[0].fill.price == expected_price


def test_on_fill_cannot_see_future_bars_for_on_start_entry():
    class Observe(Strategy):
        def on_start(self, ctx):
            ctx.buy(qty=1)

        def on_fill(self, ctx, event):
            if event.fill.side == Side.BUY:
                self.available_closes = ctx.data.close.copy()

    strategy = Observe()
    Backtest(strategy, _bars(), close_at_end=False).run()
    # The first open has no completed candles; on_start's full vector view
    # must be restricted before any runtime callback.
    assert len(strategy.available_closes) == 0


def test_dynamic_reduce_only_size_cannot_reverse_a_position():
    class CloseByPercent(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=10)
            elif ctx.i == 1:
                ctx.order(side=Side.SELL, size_pct=1.0, reduce_only=True)

    result = Backtest(CloseByPercent(), _bars(), cash=10_000, close_at_end=False).run()
    assert result.positions.qty.iloc[2] == 0
    assert len(result.trades) == 1


def test_repeated_close_intents_do_not_open_a_reverse_position():
    class CloseTwice(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.buy(qty=10)
            elif ctx.i == 1:
                ctx.close()
                ctx.close()

    result = Backtest(CloseTwice(), _bars(), close_at_end=False).run()
    assert result.positions.qty.iloc[2] == 0
    assert len(result.trades) == 1


def test_end_of_data_closes_short_even_when_loss_exceeds_cash():
    class Short(Strategy):
        def on_bar(self, ctx):
            if ctx.i == 0:
                ctx.sell(qty=10)

    bars = _bars()
    bars.loc[bars.index[2]:, ["open", "high", "low", "close"]] = 300.0
    result = Backtest(Short(), bars, cash=1000).run()
    assert result.positions.qty.iloc[-1] == 0
    assert result.trades.net_pnl.sum() == -2000.0
    assert result.metrics["total_return"] == -2.0


def test_signal_close_preserves_orders_submitted_by_fill_callback():
    from stolgo.core.types import Bar
    from stolgo.oms.commission import BpsCommission
    from stolgo.oms.fill_model import NextOpenFill
    from stolgo.oms.sim_broker import SimBroker
    from stolgo.oms.slippage import BpsSlippage

    broker = SimBroker(NextOpenFill(), BpsSlippage(0), BpsCommission(0), fill_on="signal_close")
    broker.submit(broker.create_order("SYN", Side.BUY, 1, OrderType.MARKET))

    def on_fill(event):
        broker.submit(broker.create_order("SYN", Side.SELL, 1, OrderType.MARKET, active_from=2))

    broker.match_signal_close(Bar(1, 100, 101, 99, 100, 1, "SYN"), bar_index=1, on_fill=on_fill)
    assert len(broker.open_orders()) == 1
    assert broker.open_orders()[0].side == Side.SELL
