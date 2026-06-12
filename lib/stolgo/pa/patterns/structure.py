# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Rule, rule_from_series
from stolgo.pa._level_util import prep_ohlcv
from stolgo.pa._mtf import level_on_base
from stolgo.pa.levels.range import range_high, range_low


def consolidation(days: int, range_pct: float = 0.12, *, tf: str | None = None) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        base = ohlcv
        work = prep_ohlcv(ohlcv, tf)
        h = work["high"].shift(1).rolling(days, min_periods=days).max()
        l = work["low"].shift(1).rolling(days, min_periods=days).min()
        mid = work["close"].shift(1).rolling(days, min_periods=days).mean()
        width = (h - l) / mid.replace(0, float("nan"))
        cons = width <= range_pct
        return level_on_base(base, tf, work, cons).fillna(False).astype(bool)

    return rule_from_series("consolidation", fn)


def breakout_up(days: int, range_pct: float = 0.12, *, tf: str | None = None) -> Rule:
    rh = range_high(days, tf=tf)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        cons = consolidation(days, range_pct, tf=tf).series(ohlcv)
        top = rh.values(ohlcv)
        return cons & (ohlcv["close"] > top)

    return rule_from_series("breakout_up", fn)


def breakout_down(days: int, range_pct: float = 0.12, *, tf: str | None = None) -> Rule:
    rl = range_low(days, tf=tf)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        cons = consolidation(days, range_pct, tf=tf).series(ohlcv)
        bot = rl.values(ohlcv)
        return cons & (ohlcv["close"] < bot)

    return rule_from_series("breakout_down", fn)


def range_bound(days: int, range_pct: float = 0.12, *, tf: str | None = None) -> Rule:
    return consolidation(days, range_pct, tf=tf)
