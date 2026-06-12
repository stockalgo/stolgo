# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Level
from stolgo.pa._level_util import prep_ohlcv
from stolgo.pa._mtf import level_on_base


def _range_window(high: pd.Series, low: pd.Series, days: int) -> tuple[pd.Series, pd.Series]:
    h = high.shift(1).rolling(days, min_periods=days).max()
    l = low.shift(1).rolling(days, min_periods=days).min()
    return h, l


def range_high(days: int, *, tf: str | None = None) -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        base = ohlcv
        work = prep_ohlcv(ohlcv, tf)
        h, _ = _range_window(work["high"], work["low"], days)
        return level_on_base(base, tf, work, h)

    return Level(name=f"range_high({days})", _compute=compute, tf=tf)


def range_low(days: int, *, tf: str | None = None) -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        base = ohlcv
        work = prep_ohlcv(ohlcv, tf)
        _, l = _range_window(work["high"], work["low"], days)
        return level_on_base(base, tf, work, l)

    return Level(name=f"range_low({days})", _compute=compute, tf=tf)
