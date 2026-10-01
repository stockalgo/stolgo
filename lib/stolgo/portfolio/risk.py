from dataclasses import replace

import numpy as np

from stolgo.core.config import RunConfig
from stolgo.core.events import RiskHaltEvent
from stolgo.core.types import OrderIntent, Side
from stolgo.portfolio.portfolio import Portfolio


def apply_risk(
    intent: OrderIntent | None,
    portfolio: Portfolio,
    equity_curve: list[float] | None = None,
    config: RunConfig | None = None,
    events: list[object] | None = None,
    bar_index: int = 0,
    peak_equity: float | None = None,
    current_equity: float | None = None,
) -> OrderIntent | None:
    if intent is None:
        return None
    if config is None or config.halt_drawdown is None:
        return intent

    if peak_equity is not None and current_equity is not None:
        peak = peak_equity
        current = current_equity
    elif equity_curve is not None and len(equity_curve) >= 2:
        peak = max(equity_curve)
        current = equity_curve[-1]
    else:
        return intent

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
                return replace(intent, qty=pos_qty)
            return intent
        elif pos_qty < 0:
            if intent.side == Side.SELL:
                return None
            if intent.qty is not None and intent.qty > abs(pos_qty):
                return replace(intent, qty=abs(pos_qty))
            return intent
        else:
            return None

    return intent
