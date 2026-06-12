# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Rule, rule_from_series
from stolgo.pa.patterns.candles import bearish, bullish
from stolgo.pa.patterns.streaks import streak


def run_up(min_pct: float = 2.0, within_days: int = 10) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        c = ohlcv["close"]
        ret = c / c.shift(within_days) - 1.0
        return ret >= min_pct

    return rule_from_series("run_up", fn)


def run_down(min_pct: float = 2.0, within_days: int = 10) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        c = ohlcv["close"]
        ret = 1.0 - c / c.shift(within_days)
        return ret >= min_pct

    return rule_from_series("run_down", fn)


def parabolic_up(lookback: int = 10, min_daily_gain: float = 0.02) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        c = ohlcv["close"]
        daily = c.pct_change()
        strong = daily >= min_daily_gain
        return strong.rolling(lookback, min_periods=lookback).sum() >= lookback - 1

    return rule_from_series("parabolic_up", fn)


def parabolic_down(lookback: int = 10, min_daily_loss: float = 0.02) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        c = ohlcv["close"]
        daily = c.pct_change()
        weak = daily <= -min_daily_loss
        return weak.rolling(lookback, min_periods=lookback).sum() >= lookback - 1

    return rule_from_series("parabolic_down", fn)


def giant_uptrend(periods: int = 13) -> Rule:
    return streak.higher_close(periods) & bullish()


def giant_downtrend(periods: int = 13) -> Rule:
    return streak.lower_close(periods) & bearish()
