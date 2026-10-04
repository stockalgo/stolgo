from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, Literal

from stolgo.core.events import FillEvent
from stolgo.core.types import Bar, Fill, Order, OrderType, Side
from stolgo.oms.commission import CommissionModel
from stolgo.oms.fill_model import FillModel
from stolgo.oms.order_book import OrderBook
from stolgo.oms.slippage import SlippageModel


class SimBroker:
    def __init__(
        self,
        fill_model: FillModel,
        slippage: SlippageModel,
        commission: CommissionModel,
        *,
        fill_on: Literal["next_open", "next_close", "signal_close", "close"] = "next_open",
        allow_leverage: bool = False,
        qty_step: float | None = None,
    ) -> None:
        self._fill_model = fill_model
        self._slippage = slippage
        self._commission = commission
        self._fill_on = fill_on
        self._allow_leverage = allow_leverage
        self._qty_step = qty_step
        self._pending: list[Order] = []
        self._book = OrderBook()
        self._seq = 0
        self._fill_seq = 0
        self._cancelled_ids: set[str] = set()

    def submit(self, order: Order) -> str:
        if order.order_type == OrderType.STOP_LIMIT:
            raise NotImplementedError("STOP_LIMIT orders are not implemented")
        self._pending.append(order)
        return order.order_id

    def cancel(self, order_id: str) -> None:
        self._cancelled_ids.add(order_id)
        self._pending = [o for o in self._pending if o.order_id != order_id]
        self._book.cancel(order_id)

    def cancel_reduce_only(self, symbol: str) -> None:
        cancelled = [o.order_id for o in self._pending if o.symbol == symbol and o.reduce_only]
        cancelled.extend([o.order_id for o in self._book.resting() if o.symbol == symbol and o.reduce_only])
        self._cancelled_ids.update(cancelled)
        self._pending = [o for o in self._pending if not (o.symbol == symbol and o.reduce_only)]
        self._book.cancel_reduce_only(symbol)

    def cancel_oco(self, oco_group: str) -> None:
        cancelled = [o.order_id for o in self._pending if o.oco_group == oco_group]
        cancelled.extend([o.order_id for o in self._book.resting() if o.oco_group == oco_group])
        self._cancelled_ids.update(cancelled)
        self._pending = [o for o in self._pending if o.oco_group != oco_group]
        self._book.cancel_oco(oco_group)

    def cancel_all(self) -> None:
        """Drop every pending and resting order (used when the run ends)."""
        self._cancelled_ids.update(o.order_id for o in self.open_orders())
        self._pending = []
        self._book = OrderBook()

    def open_orders(self) -> list[Order]:
        return list(self._pending) + self._book.resting()

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
        on_fill: Callable[[FillEvent], None] | None = None,
    ) -> list[FillEvent]:
        """Match waiting orders against ``bar`` and return the resulting fills.

        Market orders fill first (at the price given by the fill model), then
        resting limit/stop orders from the order book. Fills are applied one at
        a time: ``on_fill`` is invoked right after each fill is produced, before
        the next order is checked, so the caller can update the portfolio and
        later orders (cash check, ``size_pct`` sizing, ``reduce_only`` caps, OCO
        cancellation) see the effect of earlier fills in the same bar.
        """
        # Cancels remove orders from _pending and the book immediately; the set only
        # guards the snapshots iterated within a single call, so reset it per call.
        self._cancelled_ids.clear()
        fill_events: list[FillEvent] = []
        still_pending: list[Order] = []
        market_orders: list[Order] = []
        for order in list(self._pending):
            if order.order_id in self._cancelled_ids:
                continue
            if order.order_type != OrderType.MARKET:
                self._book.add(order)
            else:
                market_orders.append(order)
        self._pending = []

        for order in market_orders:
            if order.order_id in self._cancelled_ids:
                continue
            if order.active_from > bar_index or self._fill_on == "signal_close":
                still_pending.append(order)
                continue
            price = self._fill_model.fill_price(order, bar, bar_index=bar_index)
            if price is None:
                still_pending.append(order)
                continue
            fe = self._make_fill(order, bar, price, bar_index, portfolio=portfolio, events=events)
            if fe is not None:
                fill_events.append(fe)
                if on_fill is not None:
                    on_fill(fe)
        self._pending.extend([o for o in still_pending if o.order_id not in self._cancelled_ids])

        for order, price in self._book.match(bar, bar_index=bar_index):
            if order.order_id in self._cancelled_ids:
                continue
            fe = self._make_fill(order, bar, price, bar_index, portfolio=portfolio, events=events)
            if fe is not None:
                fill_events.append(fe)
                if on_fill is not None:
                    on_fill(fe)

        return fill_events

    def match_signal_close(
        self,
        bar: Bar,
        *,
        bar_index: int,
        portfolio: Any = None,
        events: list[Any] | None = None,
        on_fill: Callable[[FillEvent], None] | None = None,
    ) -> list[FillEvent]:
        # Cancels remove orders from _pending and the book immediately; the set only
        # guards the snapshots iterated within a single call, so reset it per call.
        self._cancelled_ids.clear()
        fill_events: list[FillEvent] = []
        still_pending: list[Order] = []
        pending = self._pending
        self._pending = []
        for order in pending:
            if order.order_id in self._cancelled_ids:
                continue
            if order.order_type == OrderType.MARKET:
                if order.active_from > bar_index:
                    still_pending.append(order)
                    continue
                fe = self._make_fill(order, bar, bar.close, bar_index, portfolio=portfolio, events=events)
                if fe is not None:
                    fill_events.append(fe)
                    if on_fill is not None:
                        on_fill(fe)
            else:
                self._book.add(order)
        self._pending.extend(o for o in still_pending if o.order_id not in self._cancelled_ids)
        return fill_events


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
        if order.reduce_only:
            pos_qty = portfolio.position.qty if portfolio is not None else 0.0
            if pos_qty == 0.0:
                self.cancel(order.order_id)
                if order.oco_group is not None:
                    self.cancel_oco(order.oco_group)
                return None
            if (pos_qty > 0 and order.side != Side.SELL) or (pos_qty < 0 and order.side != Side.BUY):
                self.cancel(order.order_id)
                if order.oco_group is not None:
                    self.cancel_oco(order.oco_group)
                return None

        px = self._slippage.adjust(order.side, price, order.qty)

        if order.risk_stop is not None:
            if (order.side == Side.BUY and px <= order.risk_stop) or (order.side == Side.SELL and px >= order.risk_stop):
                if events is not None:
                    from stolgo.core.events import OrderRejectedEvent
                    events.append(OrderRejectedEvent(order_id=order.order_id, reason="gap_through_stop", index=bar_index))
                self.cancel(order.order_id)
                if order.oco_group is not None:
                    self.cancel_oco(order.oco_group)
                return None

        qty = order.qty
        resolved_at_fill = False

        if order.size_risk_pct is not None and order.risk_stop is not None and portfolio is not None:
            risk = abs(px - order.risk_stop)
            if risk > 0:
                equity = portfolio.cash + portfolio.position.qty * px
                qty = (equity * order.size_risk_pct) / risk
            else:
                qty = 0.0
            resolved_at_fill = True

        if order.size_pct is not None and portfolio is not None:
            comm_rate = getattr(self._commission, "_rate", 0.0)
            cost_per_unit = px * (1.0 + comm_rate)
            qty = (portfolio.cash * order.size_pct) / cost_per_unit if cost_per_unit > 0 else 0.0
            resolved_at_fill = True

        # Cap the final resolved size, including percentage-sized exits.
        if order.reduce_only:
            pos_qty = portfolio.position.qty if portfolio is not None else 0.0
            qty = min(qty, abs(pos_qty))
            if qty <= 0:
                self.cancel(order.order_id)
                if order.oco_group is not None:
                    self.cancel_oco(order.oco_group)
                return None

        if resolved_at_fill and self._qty_step is not None and self._qty_step > 0:
            qty = math.floor(qty / self._qty_step + 1e-9) * self._qty_step
            if qty <= 0:
                if events is not None:
                    from stolgo.core.events import OrderRejectedEvent
                    events.append(OrderRejectedEvent(order_id=order.order_id, reason="below_qty_step", index=bar_index))
                self.cancel(order.order_id)
                if order.oco_group is not None:
                    self.cancel_oco(order.oco_group)
                return None

        if qty <= 0:
            if not self._allow_leverage and order.side == Side.BUY and portfolio is not None and portfolio.cash <= 0:
                if events is not None:
                    from stolgo.core.events import OrderRejectedEvent
                    events.append(OrderRejectedEvent(order_id=order.order_id, reason="insufficient_cash", index=bar_index))
            return None

        fee = self._commission.fee(order.side, px, qty)
        if not self._allow_leverage and not order.reduce_only and order.side == Side.BUY and portfolio is not None:
            required_cash = px * qty + fee
            if portfolio.cash - required_cash < -1e-7:
                if events is not None:
                    from stolgo.core.events import OrderRejectedEvent
                    events.append(OrderRejectedEvent(order_id=order.order_id, reason="insufficient_cash", index=bar_index))
                return None

        fill_risk_per_unit = abs(px - order.risk_stop) if order.risk_stop is not None else order.risk_per_unit

        fill = Fill(
            fill_id=self._next_fill_id(),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            qty=float(qty),
            price=px,
            commission=fee,
            ts=bar.ts,
            risk_per_unit=fill_risk_per_unit,
            tag=order.tag,
            client_order_id=order.client_order_id,
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
        reduce_only: bool = False,
        active_from: int = 0,
        size_risk_pct: float | None = None,
        risk_stop: float | None = None,
        client_order_id: str | None = None,
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
            reduce_only=reduce_only,
            active_from=active_from,
            size_risk_pct=size_risk_pct,
            risk_stop=risk_stop,
            client_order_id=client_order_id,
        )
