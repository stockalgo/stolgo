# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Level, Rule, rule_from_series
from stolgo.pa.levels.static import level


def _resolve_level(lv: Level | float) -> Level:
    if isinstance(lv, Level):
        return lv
    return level(float(lv))


def above(lv: Level | float) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        return ohlcv["close"] > v

    return rule_from_series("above", fn)


def below(lv: Level | float) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        return ohlcv["close"] < v

    return rule_from_series("below", fn)


def crosses_above(lv: Level | float) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        c = ohlcv["close"]
        return (c > v) & (c.shift(1) <= v.shift(1))

    return rule_from_series("crosses_above", fn)


def crosses_below(lv: Level | float) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        c = ohlcv["close"]
        return (c < v) & (c.shift(1) >= v.shift(1))

    return rule_from_series("crosses_below", fn)


def rejected_at(lv: Level | float) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        return (ohlcv["high"] > v) & (ohlcv["close"] < v)

    return rule_from_series("rejected_at", fn)


def recovered_at(lv: Level | float) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        return (ohlcv["low"] < v) & (ohlcv["close"] > v)

    return rule_from_series("recovered_at", fn)


def near(lv: Level | float, pct: float = 0.005) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        return (ohlcv["close"] - v).abs() / v.replace(0, float("nan")) <= pct

    return rule_from_series("near", fn)


def touched(lv: Level | float, pct: float = 0.002) -> Rule:
    L = _resolve_level(lv)

    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        v = L.values(ohlcv)
        return (ohlcv["high"] >= v * (1 - pct)) | (ohlcv["low"] <= v * (1 + pct))

    return rule_from_series("touched", fn)


# Aliases
breaks_above = crosses_above
breaks_below = crosses_below
failed_breakout_above = rejected_at
failed_breakdown_below = recovered_at
bounced_off = recovered_at
