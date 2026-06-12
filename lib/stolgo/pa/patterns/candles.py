# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

import pandas as pd

from stolgo.pa._core import Rule, rule_from_series


def _ohlc(ohlcv: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    return ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]


def bullish() -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        o, _, _, c = _ohlc(ohlcv)
        return c > o

    return rule_from_series("bullish", fn)


def bearish() -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        o, _, _, c = _ohlc(ohlcv)
        return c < o

    return rule_from_series("bearish", fn)


def red() -> Rule:
    return bearish()


def green() -> Rule:
    return bullish()


def doji(body_pct: float = 0.1) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        o, h, l, c = _ohlc(ohlcv)
        rng = (h - l).replace(0, float("nan"))
        body = (c - o).abs()
        return body <= body_pct * rng

    return rule_from_series("doji", fn)


def _wick_parts(o: pd.Series, h: pd.Series, l: pd.Series, c: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    rng = (h - l).replace(0, float("nan"))
    body = (c - o).abs()
    upper = h - pd.concat([c, o], axis=1).max(axis=1)
    lower = pd.concat([c, o], axis=1).min(axis=1) - l
    return rng, body, upper, lower


def hammer(
    lower_wick: float = 0.6,
    body: float = 0.2,
    upper_wick: float = 0.2,
) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        o, h, l, c = _ohlc(ohlcv)
        rng, body_sz, up, low = _wick_parts(o, h, l, c)
        return (body_sz <= body * rng) & (up <= upper_wick * rng) & (low >= lower_wick * rng)

    return rule_from_series("hammer", fn)


def inverted_hammer(
    lower_wick: float = 0.2,
    body: float = 0.2,
    upper_wick: float = 0.6,
) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        o, h, l, c = _ohlc(ohlcv)
        rng, body_sz, up, low = _wick_parts(o, h, l, c)
        return (body_sz <= body * rng) & (low <= lower_wick * rng) & (up >= upper_wick * rng)

    return rule_from_series("inverted_hammer", fn)


def bullish_engulfing() -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        o, _, _, c = _ohlc(ohlcv)
        prev_o = o.shift(1)
        prev_c = c.shift(1)
        prev_bear = prev_c < prev_o
        curr_bull = c > o
        engulf = (c > prev_o) & (o < prev_c)
        return prev_bear & curr_bull & engulf

    return rule_from_series("bullish_engulfing", fn)


def bearish_engulfing() -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        o, _, _, c = _ohlc(ohlcv)
        prev_o = o.shift(1)
        prev_c = c.shift(1)
        prev_bull = prev_c > prev_o
        curr_bear = c < o
        engulf = (c < prev_o) & (o > prev_c)
        return prev_bull & curr_bear & engulf

    return rule_from_series("bearish_engulfing", fn)
