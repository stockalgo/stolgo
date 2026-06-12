# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from stolgo.core.types import OrderIntent
from stolgo.portfolio.portfolio import Portfolio


def resolve_qty(intent: OrderIntent, portfolio: Portfolio, price: float, cash: float) -> float:
    if intent.qty is not None:
        return intent.qty
    if intent.size_pct is not None:
        return (cash * intent.size_pct) / price
    return 0.0
