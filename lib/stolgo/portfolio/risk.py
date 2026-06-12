# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import numpy as np

from stolgo.core.config import RunConfig
from stolgo.core.types import OrderIntent
from stolgo.portfolio.portfolio import Portfolio


def apply_risk(
    intent: OrderIntent | None,
    portfolio: Portfolio,
    equity_curve: list[float],
    config: RunConfig,
) -> OrderIntent | None:
    if intent is None:
        return None
    if len(equity_curve) < 2:
        return intent
    peak = max(equity_curve)
    current = equity_curve[-1]
    if peak > 0 and (peak - current) / peak > 0.5:
        return None
    return intent
