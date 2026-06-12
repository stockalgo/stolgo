# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from stolgo.core.events import FillEvent
from stolgo.core.types import Bar, Fill, Order, OrderType, Side
from stolgo.oms.commission import CommissionModel
from stolgo.oms.fill_model import FillModel
from stolgo.oms.order_book import OrderBook
from stolgo.oms.slippage import SlippageModel

_EMPTY_FILLS: tuple[FillEvent, ...] = ()


class SimBroker:
    def __init__(
        self,
        fill_model: FillModel,
        slippage: SlippageModel,
        commission: CommissionModel,
        *,
        fill_on: Literal["next_open", "close"] = "next_open",
    ) -> None:
        self._fill_model = fill_model
        self._slippage = slippage
        self._commission = commission
        self._fill_on = fill_on
        self._pending: list[Order] = []
        self._book = OrderBook()
        self._seq = 0

    def submit(self, order: Order) -> str:
        self._pending.append(order)
        return order.order_id

    def cancel(self, order_id: str) -> None:
        self._pending = [o for o in self._pending if o.order_id != order_id]
        self._book.cancel(order_id)

    def open_orders(self) -> list[Order]:
        return list(self._pending) + list(self._book._resting)

    def _next_id(self) -> str:
        self._seq += 1
        return f"ord-{self._seq}"

    def match(self, bar: Bar, *, bar_index: int) -> list[FillEvent]:
        events: list[FillEvent] = []
        still_pending: list[Order] = []
        for order in self._pending:
            if order.order_type != OrderType.MARKET:
                self._book.add(order)
                continue
            price = self._fill_model.fill_price(order, bar, bar_index=bar_index)
            if price is None:
                still_pending.append(order)
                continue
            events.append(self._make_fill(order, bar, price, bar_index))
        self._pending = still_pending

        for order, price in self._book.match(bar):
            events.append(self._make_fill(order, bar, price, bar_index))

        return events if events else list(_EMPTY_FILLS)

    def _make_fill(self, order: Order, bar: Bar, price: float, bar_index: int) -> FillEvent:
        px = self._slippage.adjust(order.side, price, order.qty)
        fee = self._commission.fee(order.side, px, order.qty)
        fill = Fill(
            fill_id=self._next_id(),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            qty=order.qty,
            price=px,
            commission=fee,
            ts=bar.ts,
        )
        return FillEvent(fill=fill, order_id=order.order_id, index=bar_index)

    def create_order(self, symbol: str, side: Side, qty: float, order_type: OrderType) -> Order:
        return Order(
            order_id=self._next_id(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
        )
