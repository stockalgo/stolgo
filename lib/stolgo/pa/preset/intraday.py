# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from stolgo.pa._core import Rule
from stolgo.pa.levels.rolling import resistance, support
from stolgo.pa.levels.range import range_high
from stolgo.pa.patterns.structure import consolidation
from stolgo.pa.relations.price_level import crosses_above, crosses_below, recovered_at, rejected_at


def breakout_intraday(
    days: int = 7,
    range_pct: float = 0.12,
    *,
    tf_daily: str = "1d",
) -> tuple[Rule, Rule]:
    """Daily consolidation + intraday break of daily range."""
    cons = consolidation(days, range_pct, tf=tf_daily)
    r = resistance(days, tf=tf_daily)
    s = support(days, tf=tf_daily)
    long_e = cons & crosses_above(r)
    short_e = cons & crosses_below(s)
    return long_e, short_e


def failed_break_intraday(
    days: int = 7,
    range_pct: float = 0.12,
    *,
    tf_daily: str = "1d",
) -> tuple[Rule, Rule]:
    """Failed breakout/breakdown at daily range."""
    cons = consolidation(days, range_pct, tf=tf_daily)
    r = resistance(days, tf=tf_daily)
    s = support(days, tf=tf_daily)
    short_e = cons & rejected_at(r)
    long_e = cons & recovered_at(s)
    return long_e, short_e


def consolidation_breakout(days: int = 7, range_pct: float = 0.12) -> Rule:
    """Consolidation then close above range high (daily)."""
    return consolidation(days, range_pct) & crosses_above(range_high(days))


def breakout_above_resistance(days: int = 7, res_lookback: int = 20, range_pct: float = 0.12) -> Rule:
    return consolidation(days, range_pct) & crosses_above(resistance(res_lookback))
