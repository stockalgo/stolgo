# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""In-memory DataFrame data source."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from stolgo.core.exceptions import DataError
from stolgo.data.normalize import normalize_ohlcv


class DataFrameSource:
    def __init__(self, df: pd.DataFrame, *, symbol: str = "UNKNOWN") -> None:
        self._df = normalize_ohlcv(df, symbol=symbol)
        self._symbol = symbol

    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        if start >= end:
            raise DataError("start must be before end")
        if symbol != self._symbol and self._symbol != "UNKNOWN":
            raise DataError(f"symbol mismatch: expected {self._symbol}, got {symbol}")
        start_ts = pd.Timestamp(start).tz_convert("UTC")
        end_ts = pd.Timestamp(end).tz_convert("UTC")
        out = self._df.loc[start_ts:end_ts]
        if out.empty:
            raise DataError(f"no rows in range {start} .. {end}")
        return out
