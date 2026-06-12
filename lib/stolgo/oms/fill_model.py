# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from typing import Literal, Protocol

from stolgo.core.types import Bar, Order, OrderType


class FillModel(Protocol):
    def fill_price(self, order: Order, bar: Bar, *, bar_index: int) -> float | None: ...


class NextOpenFill:
    def fill_price(self, order: Order, bar: Bar, *, bar_index: int) -> float | None:
        if order.order_type == OrderType.MARKET:
            return bar.open
        return None


class CloseFill:
    def fill_price(self, order: Order, bar: Bar, *, bar_index: int) -> float | None:
        if order.order_type == OrderType.MARKET:
            return bar.close
        return None
