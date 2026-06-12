# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""bandl market data adapter (HLD §4.2, §G).

Import as ``from stolgo import Bandl`` — wraps the `bandl` package for OHLCV
history (crypto, equity). For CSV/Parquet files use :func:`stolgo.load`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

import pandas as pd

from stolgo.core.exceptions import DataError
from stolgo.data.cache import ParquetCache
from stolgo.data.normalize import normalize_ohlcv


class BandlDataSource:
    """Historical OHLCV via `bandl` with normalization and optional parquet cache.

    Public alias: :class:`Bandl` (preferred in user code).
    """
    def __init__(
        self,
        client=None,
        *,
        provider: Literal["crypto", "equity"] = "crypto",
        source: str | None = None,
        cache: ParquetCache | None = None,
    ) -> None:
        if client is None:
            from bandl import Bandl

            client = Bandl()
        self._client = client
        self._provider = provider
        self._source = source
        self._cache = cache or ParquetCache()

    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        if start >= end:
            raise DataError("start must be before end")

        provider_key = self._source or self._provider
        key = self._cache.make_key(provider_key, symbol, interval, start, end)
        hit = self._cache.get(key)
        if hit is not None:
            return hit

        kwargs: dict = {}
        if self._source:
            kwargs["source"] = self._source

        if self._provider == "crypto":
            raw = self._client.crypto.get_ohlcv_dataframe(
                symbol, interval, start, end, **kwargs
            )
        else:
            raw = self._client.equity.get_ohlcv_dataframe(
                symbol, interval, start, end, **kwargs
            )

        df = normalize_ohlcv(raw, symbol=symbol)
        self._cache.put(key, df)
        return df


# Preferred public name (``from stolgo import Bandl``).
Bandl = BandlDataSource
