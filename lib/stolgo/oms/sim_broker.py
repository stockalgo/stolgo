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
        fill_on: Literal["next_open", "next_close", "signal_close", "close"] = "next_open",
        allow_leverage: bool = False,
    ) -> None:
        self._fill_model = fill_model
        self._slippage = slippage
        self._commission = commission
        self._fill_on = fill_on
        self._allow_leverage = allow_leverage
        self._pending: list[Order] = []
        self._book = OrderBook()
        self._seq = 0
        self._fill_seq = 0

    def submit(self, order: Order) -> str:
        if order.order_type == OrderType.STOP_LIMIT:
            raise NotImplementedError("STOP_LIMIT orders are not implemented")
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

    def _next_fill_id(self) -> str:
        self._fill_seq += 1
        return f"fill-{self._fill_seq}"

    def match(
        self,
        bar: Bar,
        *,
        bar_index: int,
        portfolio: Any = None,
        events: list[Any] | None = None,
    ) -> list[FillEvent]:
        fill_events: list[FillEvent] = []
        still_pending: list[Order] = []
        for order in self._pending:
            if order.order_type != OrderType.MARKET:
                self._book.add(order)
                continue
            price = self._fill_model.fill_price(order, bar, bar_index=bar_index)
            if price is None:
                still_pending.append(order)
                continue
            fe = self._make_fill(order, bar, price, bar_index, portfolio=portfolio, events=events)
            if fe is not None:
                fill_events.append(fe)
        self._pending = still_pending

        for order, price in self._book.match(bar):
            fe = self._make_fill(order, bar, price, bar_index, portfolio=portfolio, events=events)
            if fe is not None:
                fill_events.append(fe)

        return fill_events if fill_events else list(_EMPTY_FILLS)

    def match_signal_close(
        self,
        bar: Bar,
        *,
        bar_index: int,
        portfolio: Any = None,
        events: list[Any] | None = None,
    ) -> list[FillEvent]:
        fill_events: list[FillEvent] = []
        still_pending: list[Order] = []
        for order in self._pending:
            if order.order_type == OrderType.MARKET:
                fe = self._make_fill(order, bar, bar.close, bar_index, portfolio=portfolio, events=events)
                if fe is not None:
                    fill_events.append(fe)
            else:
                self._book.add(order)
        self._pending = still_pending
        return fill_events if fill_events else list(_EMPTY_FILLS)


    def _make_fill(
        self,
        order: Order,
        bar: Bar,
        price: float,
        bar_index: int,
        *,
        portfolio: Any = None,
        events: list[Any] | None = None,
    ) -> FillEvent | None:
        px = self._slippage.adjust(order.side, price, order.qty)
        qty = order.qty

        if order.size_pct is not None and portfolio is not None:
            comm_rate = getattr(self._commission, "_rate", 0.0)
            cost_per_unit = px * (1.0 + comm_rate)
            qty = (portfolio.cash * order.size_pct) / cost_per_unit if cost_per_unit > 0 else 0.0

        if qty <= 0:
            if not self._allow_leverage and order.side == Side.BUY and portfolio is not None and portfolio.cash <= 0:
                if events is not None:
                    from stolgo.core.events import OrderRejectedEvent
                    events.append(OrderRejectedEvent(order_id=order.order_id, reason="insufficient_cash", index=bar_index))
            return None

        fee = self._commission.fee(order.side, px, qty)
        if not self._allow_leverage and order.side == Side.BUY and portfolio is not None:
            required_cash = px * qty + fee
            if portfolio.cash - required_cash < -1e-7:
                if events is not None:
                    from stolgo.core.events import OrderRejectedEvent
                    events.append(OrderRejectedEvent(order_id=order.order_id, reason="insufficient_cash", index=bar_index))
                return None

        fill = Fill(
            fill_id=self._next_fill_id(),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            qty=qty,
            price=px,
            commission=fee,
            ts=bar.ts,
            risk_per_unit=order.risk_per_unit,
            tag=order.tag,
        )
        return FillEvent(fill=fill, order_id=order.order_id, index=bar_index)

    def create_order(
        self,
        symbol: str,
        side: Side,
        qty: float,
        order_type: OrderType,
        *,
        limit_price: float | None = None,
        stop_price: float | None = None,
        tag: str | None = None,
        size_pct: float | None = None,
        oco_group: str | None = None,
        risk_per_unit: float | None = None,
    ) -> Order:
        return Order(
            order_id=self._next_id(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            limit_price=limit_price,
            stop_price=stop_price,
            tag=tag,
            size_pct=size_pct,
            oco_group=oco_group,
            risk_per_unit=risk_per_unit,
        )
