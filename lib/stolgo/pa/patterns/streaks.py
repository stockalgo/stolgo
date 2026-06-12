# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Streak helpers exposed as ``pa.streak.green`` etc."""

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Rule, rule_from_series
from stolgo.pa.patterns.candles import bearish, bullish


def _streak(rule: Rule, min_n: int, name: str) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        b = rule.series(ohlcv).astype(int)
        return b.rolling(min_n, min_periods=min_n).sum() >= min_n

    return rule_from_series(name, fn)


class _StreakNS:
    def green(self, min_n: int) -> Rule:
        return _streak(bullish(), min_n, f"streak.green({min_n})")

    def red(self, min_n: int) -> Rule:
        return _streak(bearish(), min_n, f"streak.red({min_n})")

    def higher_close(self, min_n: int) -> Rule:
        def fn(ohlcv: pd.DataFrame) -> pd.Series:
            c = ohlcv["close"]
            up = c > c.shift(1)
            return up.rolling(min_n, min_periods=min_n).sum() >= min_n

        return rule_from_series(f"streak.higher_close({min_n})", fn)

    def lower_close(self, min_n: int) -> Rule:
        def fn(ohlcv: pd.DataFrame) -> pd.Series:
            c = ohlcv["close"]
            down = c < c.shift(1)
            return down.rolling(min_n, min_periods=min_n).sum() >= min_n

        return rule_from_series(f"streak.lower_close({min_n})", fn)


streak = _StreakNS()


def first_red_day(min_prior_green: int = 3) -> Rule:
    return streak.green(min_prior_green).then(bearish())


def first_green_day(min_prior_red: int = 3) -> Rule:
    return streak.red(min_prior_red).then(bullish())
