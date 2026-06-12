from stolgo.core.types import Bar, OrderType, Side
from stolgo.oms.commission import BpsCommission
from stolgo.oms.fill_model import NextOpenFill
from stolgo.oms.sim_broker import SimBroker
from stolgo.oms.slippage import NoSlippage


def test_market_fill_next_open():
    broker = SimBroker(NextOpenFill(), NoSlippage(), BpsCommission(0.0))
    order = broker.create_order("X", Side.BUY, 1.0, OrderType.MARKET)
    broker.submit(order)
    bar = Bar(ts=1, open=10.0, high=11, low=9, close=10.5, volume=1, symbol="X")
    fills = broker.match(bar, bar_index=1)
    assert len(fills) == 1
    assert fills[0].fill.price == 10.0
