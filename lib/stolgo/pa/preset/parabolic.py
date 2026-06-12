# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from stolgo.pa._core import Rule
from stolgo.pa.patterns.momentum import run_up
from stolgo.pa.patterns.streaks import first_red_day


def parabolic_short(min_pct: float = 2.0, within_days: int = 10) -> Rule:
    """Large run up then first red day (short bias)."""
    return run_up(min_pct=min_pct, within_days=within_days) & first_red_day()
