# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Level
from stolgo.pa._level_util import prep_ohlcv, prior_rolling_max, prior_rolling_min
from stolgo.pa._mtf import level_on_base


def resistance(lookback: int, *, tf: str | None = None) -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        base = ohlcv
        work = prep_ohlcv(ohlcv, tf)
        vals = prior_rolling_max(work["high"], lookback)
        return level_on_base(base, tf, work, vals)

    return Level(name=f"resistance({lookback})", _compute=compute, tf=tf)


def support(lookback: int, *, tf: str | None = None) -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        base = ohlcv
        work = prep_ohlcv(ohlcv, tf)
        vals = prior_rolling_min(work["low"], lookback)
        return level_on_base(base, tf, work, vals)

    return Level(name=f"support({lookback})", _compute=compute, tf=tf)


def donchian_high(period: int, *, tf: str | None = None) -> Level:
    return resistance(period, tf=tf)


def donchian_low(period: int, *, tf: str | None = None) -> Level:
    return support(period, tf=tf)
