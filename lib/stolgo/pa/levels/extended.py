# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""v1.1 levels: swing, pivots, vwap, session — optional extended API."""

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Level
from stolgo.pa._level_util import prep_ohlcv
from stolgo.pa._mtf import level_on_base


def swing_high(lookback: int = 5, *, tf: str | None = None) -> Level:
    half = max(1, lookback // 2)

    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        base = ohlcv
        work = prep_ohlcv(ohlcv, tf)
        h = work["high"]
        out = pd.Series(float("nan"), index=work.index)
        for i in range(half, len(work) - half):
            window = h.iloc[i - half : i + half + 1]
            if h.iloc[i] == window.max():
                out.iloc[i] = h.iloc[i]
        return level_on_base(base, tf, work, out.ffill())

    return Level(name=f"swing_high({lookback})", _compute=compute, tf=tf)


def swing_low(lookback: int = 5, *, tf: str | None = None) -> Level:
    half = max(1, lookback // 2)

    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        base = ohlcv
        work = prep_ohlcv(ohlcv, tf)
        l = work["low"]
        out = pd.Series(float("nan"), index=work.index)
        for i in range(half, len(work) - half):
            window = l.iloc[i - half : i + half + 1]
            if l.iloc[i] == window.min():
                out.iloc[i] = l.iloc[i]
        return level_on_base(base, tf, work, out.ffill())

    return Level(name=f"swing_low({lookback})", _compute=compute, tf=tf)


def prev_day_high(*, tf: str = "1d") -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        daily = prep_ohlcv(ohlcv, "1D")
        pdh = daily["high"].shift(1)
        return level_on_base(ohlcv, "1D", daily, pdh)

    return Level(name="prev_day_high", _compute=compute, tf=tf)


def prev_day_low(*, tf: str = "1d") -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        daily = prep_ohlcv(ohlcv, "1D")
        pdl = daily["low"].shift(1)
        return level_on_base(ohlcv, "1D", daily, pdl)

    return Level(name="prev_day_low", _compute=compute, tf=tf)


def vwap() -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        tp = (ohlcv["high"] + ohlcv["low"] + ohlcv["close"]) / 3.0
        vol = ohlcv["volume"].replace(0, float("nan"))
        return (tp * vol).cumsum() / vol.cumsum()

    return Level(name="vwap", _compute=compute)


def pivot_point() -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        daily = prep_ohlcv(ohlcv, "1D")
        pp = (daily["high"].shift(1) + daily["low"].shift(1) + daily["close"].shift(1)) / 3.0
        return level_on_base(ohlcv, "1D", daily, pp)

    return Level(name="pivot_point", _compute=compute)
