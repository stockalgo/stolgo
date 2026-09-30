# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

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

    def match(self, bar: Bar) -> list[tuple[Order, float]]:
        candidates: list[tuple[Order, float]] = []
        untriggered: list[Order] = []

        for order in self._resting:
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
            # If both stop and limit hit in same bar, adverse-first: fill STOP
            stop_candidates = [item for item in orders if item[0].order_type == OrderType.STOP]
            winner = stop_candidates[0] if stop_candidates else orders[0]
            filled.append(winner)
            filled_oco_groups.add(grp)

        # Cancel any sibling orders in the same oco_group that was filled
        self._resting = [o for o in untriggered if o.oco_group is None or o.oco_group not in filled_oco_groups]
        return filled
