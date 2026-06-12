# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""OHLCV array helpers for price-action rules."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from stolgo.data.normalize import normalize_ohlcv
from stolgo.strategy.context import BarDataView, Context


@dataclass(frozen=True)
class BarArrays:
    """Contiguous OHLCV arrays aligned to a single timeframe."""

    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    index: pd.DatetimeIndex

    @property
    def n(self) -> int:
        return len(self.close)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, *, symbol: str | None = None) -> BarArrays:
        work = normalize_ohlcv(df, symbol=symbol) if "open" not in df.columns else df
        if not isinstance(work.index, pd.DatetimeIndex):
            raise ValueError("OHLCV DataFrame must have DatetimeIndex")
        return cls(
            open=work["open"].to_numpy(dtype=np.float64),
            high=work["high"].to_numpy(dtype=np.float64),
            low=work["low"].to_numpy(dtype=np.float64),
            close=work["close"].to_numpy(dtype=np.float64),
            volume=work["volume"].to_numpy(dtype=np.float64),
            index=work.index,
        )

    @classmethod
    def from_context(cls, ctx: Context) -> BarArrays:
        data = ctx.data
        n = len(data)
        return cls(
            open=data.open.copy(),
            high=data.high.copy(),
            low=data.low.copy(),
            close=data.close.copy(),
            volume=data.volume.copy(),
            index=pd.DatetimeIndex(np.arange(n), tz="UTC"),  # placeholder; series uses ctx.i
        )

    def slice_to(self, i: int) -> BarArrays:
        """Return arrays truncated to bar index i inclusive (causal window)."""
        end = i + 1
        return BarArrays(
            open=self.open[:end],
            high=self.high[:end],
            low=self.low[:end],
            close=self.close[:end],
            volume=self.volume[:end],
            index=self.index[:end] if len(self.index) >= end else self.index,
        )
