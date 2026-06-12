"""Tests for stolgo.core.events."""

from __future__ import annotations

from dataclasses import asdict

from stolgo.core.events import BarEvent, FillEvent, OrderEvent
from stolgo.core.types import Bar, Fill, Order, OrderStatus, OrderType, Side


def test_fill_event_links_order() -> None:
    bar = Bar(ts=1, open=1, high=1, low=1, close=1, volume=1, symbol="X")
    order = Order(
        order_id="oid-1",
        symbol="X",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=1.0,
        status=OrderStatus.FILLED,
    )
    fill = Fill(
        fill_id="f1",
        order_id="oid-1",
        symbol="X",
        side=Side.BUY,
        qty=1.0,
        price=1.0,
        commission=0.0,
        ts=1,
    )
    ev = FillEvent(fill=fill, order_id="oid-1", index=0)
    assert ev.order_id == fill.order_id
    _ = BarEvent(bar=bar, index=0)
    _ = OrderEvent(order=order, index=0)
    d = asdict(ev)
    assert d["order_id"] == "oid-1"
