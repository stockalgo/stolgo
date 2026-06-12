# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from stolgo.pa._core import Rule
from stolgo.pa.patterns.candles import bearish_engulfing, red
from stolgo.pa.patterns.streaks import streak


def scalp_green_fade(min_green: int = 3) -> Rule:
    """Short after ``min_green`` green bars then red or bearish engulfing."""
    return streak.green(min_green).then(red() | bearish_engulfing())
