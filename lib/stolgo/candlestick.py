"""Legacy candlestick API — use ``stolgo.pa`` instead."""

from __future__ import annotations

import warnings

import pandas as pd

import stolgo.pa as pa
from stolgo.exception import BadDataError


def _normalize_legacy_df(dfs: pd.DataFrame) -> pd.DataFrame:
    out = dfs.copy()
    mapping = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    for old, new in mapping.items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]
    return out


class CandleStick:
    """Deprecated — use :mod:`stolgo.pa` candle rules."""

    def __init__(self) -> None:
        warnings.warn(
            "stolgo.candlestick.CandleStick is deprecated; use stolgo.pa",
            DeprecationWarning,
            stacklevel=2,
        )

    def is_bearish_candle(self, candle: pd.Series) -> bool:
        o = candle.get("Open", candle.get("open"))
        c = candle.get("Close", candle.get("close"))
        return bool(c < o)

    def is_bullish_candle(self, candle: pd.Series) -> bool:
        o = candle.get("Open", candle.get("open"))
        c = candle.get("Close", candle.get("close"))
        return bool(c > o)

    def is_bullish_engulfing(self, candles: pd.DataFrame, pos: int = -1) -> bool:
        if candles.shape[0] < 2:
            raise BadDataError("Minimun two candles require")
        df = _normalize_legacy_df(candles)
        return bool(pa.bullish_engulfing().series(df).iloc[pos])

    def is_hammer_candle(
        self,
        candle: pd.DataFrame,
        pos: int = -1,
        lower_wick: float = 0.6,
        body: float = 0.2,
        upper_wick: float = 0.2,
    ) -> bool:
        if candle.shape[0] < 1:
            raise BadDataError("Minimun one candles require")
        df = _normalize_legacy_df(candle)
        return bool(pa.hammer().series(df).iloc[pos])

    def is_inverse_hammer_candle(
        self,
        candle: pd.DataFrame,
        pos: int = -1,
        lower_wick: float = 0.2,
        body: float = 0.2,
        upper_wick: float = 0.6,
    ) -> bool:
        df = _normalize_legacy_df(candle)
        return bool(pa.inverted_hammer().series(df).iloc[pos])

    def is_doji_candle(
        self,
        candle: pd.DataFrame,
        pos: int = -1,
        lower_wick: float = 0.4,
        body: float = 0.02,
        upper_wick: float = 0.4,
    ) -> bool:
        df = _normalize_legacy_df(candle)
        return bool(pa.doji().series(df).iloc[pos])
