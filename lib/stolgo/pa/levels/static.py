# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Level
from stolgo.pa.levels.rolling import resistance, support


def level(price: float) -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        return pd.Series(float(price), index=ohlcv.index)

    return Level(name=f"level({price})", _compute=compute)


def level_from_series(s: pd.Series) -> Level:
    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        return s.reindex(ohlcv.index).ffill()

    return Level(name="level_from_series", _compute=compute)


def cluster(*levels: Level, tol_pct: float = 0.005) -> Level:
    if not levels:
        raise ValueError("cluster requires at least one Level")

    def compute(ohlcv: pd.DataFrame) -> pd.Series:
        mats = [lv.values(ohlcv) for lv in levels]
        stacked = pd.concat(mats, axis=1)
        mid = stacked.mean(axis=1)
        return mid

    def band_compute(ohlcv: pd.DataFrame) -> pd.DataFrame:
        mats = [lv.values(ohlcv) for lv in levels]
        stacked = pd.concat(mats, axis=1)
        low = stacked.min(axis=1)
        high = stacked.max(axis=1)
        spread = (high - low) / low.replace(0, float("nan"))
        mid = (high + low) / 2
        use_mid = spread <= tol_pct
        out_low = low.where(~use_mid, mid * (1 - tol_pct / 2))
        out_high = high.where(~use_mid, mid * (1 + tol_pct / 2))
        return pd.DataFrame({"low": out_low, "high": out_high}, index=ohlcv.index)

    return Level(name="cluster", _compute=compute, _band_compute=band_compute)
