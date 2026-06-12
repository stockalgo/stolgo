# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Parquet disk cache for OHLCV (HLD §4.2)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


class ParquetCache:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path.home() / ".stolgo" / "cache"
        self._root.mkdir(parents=True, exist_ok=True)

    def make_key(
        self,
        provider: str,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> str:
        return f"{provider}_{symbol}_{interval}_{start.isoformat()}_{end.isoformat()}"

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(":", "-")
        return self._root / f"{safe}.parquet"

    def get(self, key: str) -> pd.DataFrame | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return pd.read_parquet(path)
        except Exception:
            return None

    def put(self, key: str, df: pd.DataFrame) -> None:
        df.to_parquet(self._path(key), index=True)
