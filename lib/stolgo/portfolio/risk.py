# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import numpy as np

from stolgo.core.config import RunConfig
from stolgo.core.events import RiskHaltEvent
from stolgo.core.types import OrderIntent, Side
from stolgo.portfolio.portfolio import Portfolio


def apply_risk(
    intent: OrderIntent | None,
    portfolio: Portfolio,
    equity_curve: list[float],
    config: RunConfig,
    events: list[object] | None = None,
    bar_index: int = 0,
) -> OrderIntent | None:
    if intent is None:
        return None
    if config.halt_drawdown is None:
        return intent
    if len(equity_curve) < 2:
        return intent

    peak = max(equity_curve)
    current = equity_curve[-1]
    if peak <= 0:
        return intent

    drawdown = (peak - current) / peak
    if drawdown >= config.halt_drawdown:
        if events is not None and not any(isinstance(e, RiskHaltEvent) for e in events):
            events.append(RiskHaltEvent(index=bar_index, drawdown=drawdown))

        pos_qty = portfolio.position.qty
        if pos_qty > 0:
            if intent.side == Side.BUY:
                return None
            if intent.qty is not None and intent.qty > pos_qty:
                return OrderIntent(
                    symbol=intent.symbol,
                    side=intent.side,
                    order_type=intent.order_type,
                    qty=pos_qty,
                    size_pct=intent.size_pct,
                    limit_price=intent.limit_price,
                    stop_price=intent.stop_price,
                    tag=intent.tag,
                )
            return intent
        elif pos_qty < 0:
            if intent.side == Side.SELL:
                return None
            if intent.qty is not None and intent.qty > abs(pos_qty):
                return OrderIntent(
                    symbol=intent.symbol,
                    side=intent.side,
                    order_type=intent.order_type,
                    qty=abs(pos_qty),
                    size_pct=intent.size_pct,
                    limit_price=intent.limit_price,
                    stop_price=intent.stop_price,
                    tag=intent.tag,
                )
            return intent
        else:
            return None

    return intent
