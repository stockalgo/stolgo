"""Tests for stolgo.core.types."""

from __future__ import annotations

import pytest

from stolgo.core.types import (
    Bar,
    Order,
    OrderIntent,
    OrderStatus,
    OrderType,
    Position,
    Side,
)


def test_bar_frozen() -> None:
    bar = Bar(ts=1, open=1.0, high=2.0, low=0.5, close=1.5, volume=100.0, symbol="TEST")
    with pytest.raises(AttributeError):
        bar.close = 2.0  # type: ignore[misc]


def test_side_enum_values() -> None:
    assert Side.BUY.value == "buy"
    assert Side.SELL.value == "sell"


def test_order_intent_rejects_zero_qty() -> None:
    with pytest.raises(ValueError, match="qty"):
        OrderIntent(symbol="X", side=Side.BUY, order_type=OrderType.MARKET, qty=0)


def test_position_flat() -> None:
    assert Position(symbol="X").flat is True
    assert Position(symbol="X", qty=10.0).flat is False


def test_order_hash_stable() -> None:
    o = Order(
        order_id="1",
        symbol="X",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=1.0,
        status=OrderStatus.OPEN,
    )
    assert hash(o) == hash(o)
