# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from stolgo.core.types import Bar, Order, OrderType, Side


class OrderBook:
    def __init__(self) -> None:
        self._resting: list[Order] = []

    def add(self, order: Order) -> None:
        if order.order_type in (OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT):
            self._resting.append(order)

    def cancel(self, order_id: str) -> None:
        self._resting = [o for o in self._resting if o.order_id != order_id]

    def match(self, bar: Bar) -> list[tuple[Order, float]]:
        filled: list[tuple[Order, float]] = []
        remaining: list[Order] = []
        for order in self._resting:
            price = None
            if order.order_type == OrderType.LIMIT and order.limit_price is not None:
                if order.side == Side.BUY and bar.low <= order.limit_price:
                    price = order.limit_price
                elif order.side == Side.SELL and bar.high >= order.limit_price:
                    price = order.limit_price
            elif order.order_type == OrderType.STOP and order.stop_price is not None:
                if order.side == Side.BUY and bar.high >= order.stop_price:
                    price = bar.open
                elif order.side == Side.SELL and bar.low <= order.stop_price:
                    price = bar.open
            if price is not None:
                filled.append((order, price))
            else:
                remaining.append(order)
        self._resting = remaining
        return filled
