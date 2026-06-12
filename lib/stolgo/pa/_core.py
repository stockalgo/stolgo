# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Core Level and Rule types for stolgo.pa."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

import numpy as np
import pandas as pd

from stolgo.pa._bars import BarArrays

if TYPE_CHECKING:
    from stolgo.strategy.context import Context


@dataclass(frozen=True)
class Level:
    """A price level (or zone) series aligned to OHLCV bars."""

    name: str
    _compute: Callable[[pd.DataFrame], pd.Series]
    _band_compute: Callable[[pd.DataFrame], pd.DataFrame] | None = None
    tf: str | None = None

    def values(self, ohlcv: pd.DataFrame) -> pd.Series:
        s = self._compute(ohlcv)
        return s.reindex(ohlcv.index)

    def band(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        if self._band_compute is None:
            v = self.values(ohlcv)
            return pd.DataFrame({"low": v, "high": v}, index=ohlcv.index)
        return self._band_compute(ohlcv).reindex(ohlcv.index)

    def touches(self, ohlcv: pd.DataFrame, tol_pct: float = 0.002) -> pd.DataFrame:
        lv = self.values(ohlcv)
        high = ohlcv["high"]
        low = ohlcv["low"]
        touched = (high >= lv * (1 - tol_pct)) | (low <= lv * (1 + tol_pct))
        return pd.DataFrame({"level": lv, "touched": touched}, index=ohlcv.index)


class Rule(ABC):
    """Boolean price-action condition evaluable per bar."""

    @abstractmethod
    def series(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Vectorized rule; index aligned to ohlcv."""

    def series_at(self, bars: BarArrays) -> np.ndarray:
        """Bool ndarray for BarArrays (used when index is synthetic)."""
        n = bars.n
        if n == 0:
            return np.array([], dtype=bool)
        df = pd.DataFrame(
            {
                "open": bars.open,
                "high": bars.high,
                "low": bars.low,
                "close": bars.close,
                "volume": bars.volume,
            },
            index=pd.DatetimeIndex(range(n), tz="UTC"),
        )
        return self.series(df).to_numpy(dtype=bool)

    def __call__(self, ctx: Context) -> bool:
        data = ctx.data
        n = len(data)
        if n == 0:
            return False
        df = pd.DataFrame(
            {
                "open": data.open,
                "high": data.high,
                "low": data.low,
                "close": data.close,
                "volume": data.volume,
            },
            index=data.index,
        )
        s = self.series(df)
        return bool(s.iloc[-1])

    def __and__(self, other: Rule) -> Rule:
        return AndRule(self, other)

    def __or__(self, other: Rule) -> Rule:
        return OrRule(self, other)

    def __invert__(self) -> Rule:
        return NotRule(self)

    def then(self, other: Rule) -> Rule:
        """True when other is true at t and self was true at t-1."""
        return ThenRule(self, other)


@dataclass(frozen=True)
class _SeriesRule(Rule):
    name: str
    _fn: Callable[[pd.DataFrame], pd.Series]

    def series(self, ohlcv: pd.DataFrame) -> pd.Series:
        return self._fn(ohlcv).reindex(ohlcv.index).fillna(False).astype(bool)


def rule_from_series(name: str, fn: Callable[[pd.DataFrame], pd.Series]) -> Rule:
    return _SeriesRule(name, fn)


@dataclass(frozen=True)
class AndRule(Rule):
    left: Rule
    right: Rule

    def series(self, ohlcv: pd.DataFrame) -> pd.Series:
        return self.left.series(ohlcv) & self.right.series(ohlcv)


@dataclass(frozen=True)
class OrRule(Rule):
    left: Rule
    right: Rule

    def series(self, ohlcv: pd.DataFrame) -> pd.Series:
        return self.left.series(ohlcv) | self.right.series(ohlcv)


@dataclass(frozen=True)
class NotRule(Rule):
    inner: Rule

    def series(self, ohlcv: pd.DataFrame) -> pd.Series:
        return ~self.inner.series(ohlcv)


@dataclass(frozen=True)
class ThenRule(Rule):
    setup: Rule
    trigger: Rule

    def series(self, ohlcv: pd.DataFrame) -> pd.Series:
        a = self.setup.series(ohlcv)
        b = self.trigger.series(ohlcv)
        prev = a.shift(1)
        return b & prev.where(prev.notna(), False).astype(bool)


def all_of(*rules: Rule) -> Rule:
    if not rules:
        raise ValueError("all_of requires at least one rule")
    out = rules[0]
    for r in rules[1:]:
        out = out & r
    return out


def any_of(*rules: Rule) -> Rule:
    if not rules:
        raise ValueError("any_of requires at least one rule")
    out = rules[0]
    for r in rules[1:]:
        out = out | r
    return out
