# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Shared helpers for Level computation."""

from __future__ import annotations

import pandas as pd

from stolgo.data.normalize import normalize_ohlcv
from stolgo.pa._mtf import apply_tf


def prep_ohlcv(ohlcv: pd.DataFrame, tf: str | None) -> pd.DataFrame:
    if tf is None:
        return ohlcv if "open" in ohlcv.columns else normalize_ohlcv(ohlcv)
    return apply_tf(ohlcv, tf)


def prior_rolling_max(high: pd.Series, lookback: int) -> pd.Series:
    return high.shift(1).rolling(lookback, min_periods=lookback).max()


def prior_rolling_min(low: pd.Series, lookback: int) -> pd.Series:
    return low.shift(1).rolling(lookback, min_periods=lookback).min()
