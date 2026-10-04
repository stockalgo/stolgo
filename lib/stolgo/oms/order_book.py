from __future__ import annotations

from stolgo.core.types import Bar, Order, OrderType, Side


class OrderBook:
    def __init__(self) -> None:
        self._resting: list[Order] = []

    def add(self, order: Order) -> None:
        if order.order_type == OrderType.STOP_LIMIT:
            raise NotImplementedError("STOP_LIMIT orders are not implemented")
        if order.order_type in (OrderType.LIMIT, OrderType.STOP):
            self._resting.append(order)

    def cancel(self, order_id: str) -> None:
        self._resting = [o for o in self._resting if o.order_id != order_id]

    def cancel_reduce_only(self, symbol: str) -> None:
        self._resting = [o for o in self._resting if not (o.symbol == symbol and o.reduce_only)]

    def cancel_oco(self, oco_group: str) -> None:
        self._resting = [o for o in self._resting if o.oco_group != oco_group]

    def resting(self) -> list[Order]:
        return list(self._resting)

    def match(self, bar: Bar, bar_index: int = 0) -> list[tuple[Order, float]]:
        """Return ``(order, fill_price)`` for every resting order triggered by ``bar``.

        Orders with ``active_from > bar_index`` are skipped. Limits fill on a
        touch at ``min(open, limit)`` (buy) or ``max(open, limit)`` (sell); stops
        fill at ``max(open, stop)`` (buy) or ``min(open, stop)`` (sell), so a gap
        fills at the open.

        When several legs of one ``oco_group`` trigger in the same bar, exactly
        one fills and its siblings are cancelled. OHLC data does not say which
        was hit first, so the open decides: a leg whose trigger the open has
        already crossed wins (a gap through a target fills the target at the
        open); if the open crossed neither leg, or both, the STOP wins
        (adverse-first).
        """
        candidates: list[tuple[Order, float]] = []
        untriggered: list[Order] = []

        for order in self._resting:
            if order.active_from > bar_index:
                untriggered.append(order)
                continue
            price = None
            if order.order_type == OrderType.LIMIT and order.limit_price is not None:
                if order.side == Side.BUY and bar.low <= order.limit_price:
                    price = min(bar.open, order.limit_price)
                elif order.side == Side.SELL and bar.high >= order.limit_price:
                    price = max(bar.open, order.limit_price)
            elif order.order_type == OrderType.STOP and order.stop_price is not None:
                if order.side == Side.BUY and bar.high >= order.stop_price:
                    price = max(bar.open, order.stop_price)
                elif order.side == Side.SELL and bar.low <= order.stop_price:
                    price = min(bar.open, order.stop_price)

            if price is not None:
                candidates.append((order, price))
            else:
                untriggered.append(order)

        filled: list[tuple[Order, float]] = []
        filled_oco_groups: set[str] = set()

        # Group triggered orders by oco_group
        oco_map: dict[str, list[tuple[Order, float]]] = {}
        for order, price in candidates:
            if order.oco_group is not None:
                oco_map.setdefault(order.oco_group, []).append((order, price))
            else:
                filled.append((order, price))

        for grp, orders in oco_map.items():
            # If the open alone satisfies one triggered leg, that leg wins at the open price.
            open_satisfied = [
                item for item in orders
                if (
                    (item[0].order_type == OrderType.LIMIT and item[0].limit_price is not None and (
                        (item[0].side == Side.SELL and bar.open >= item[0].limit_price) or
                        (item[0].side == Side.BUY and bar.open <= item[0].limit_price)
                    )) or
                    (item[0].order_type == OrderType.STOP and item[0].stop_price is not None and (
                        (item[0].side == Side.SELL and bar.open <= item[0].stop_price) or
                        (item[0].side == Side.BUY and bar.open >= item[0].stop_price)
                    ))
                )
            ]
            if len(open_satisfied) == 1:
                winner = open_satisfied[0]
            elif len(open_satisfied) > 1:
                stop_candidates = [item for item in open_satisfied if item[0].order_type == OrderType.STOP]
                winner = stop_candidates[0] if stop_candidates else open_satisfied[0]
            else:
                # Open is between the legs: adverse-first: fill STOP
                stop_candidates = [item for item in orders if item[0].order_type == OrderType.STOP]
                winner = stop_candidates[0] if stop_candidates else orders[0]
            filled.append(winner)
            filled_oco_groups.add(grp)

        # Cancel any sibling orders in the same oco_group that was filled
        self._resting = [o for o in untriggered if o.oco_group is None or o.oco_group not in filled_oco_groups]
        return filled
