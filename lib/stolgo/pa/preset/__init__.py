# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Named strategy recipes built from pa atoms."""

from stolgo.pa.preset.intraday import (
    breakout_above_resistance,
    breakout_intraday,
    consolidation_breakout,
    failed_break_intraday,
)
from stolgo.pa.preset.parabolic import parabolic_short
from stolgo.pa.preset.scalp import scalp_green_fade

__all__ = [
    "breakout_above_resistance",
    "breakout_intraday",
    "consolidation_breakout",
    "failed_break_intraday",
    "parabolic_short",
    "scalp_green_fade",
]
