# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""DataSource protocol (HLD §4.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd

from stolgo.core.exceptions import ModeNotSupportedError


class DataSource(Protocol):
    """Implementors: DataFrameSource, BandlDataSource, ParquetSource (future)."""

    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Return normalized OHLCV between start and end (UTC)."""
        ...

    def subscribe(self, symbol: str, interval: str):
        """Live bar stream — not implemented until v0.3."""
        raise ModeNotSupportedError(
            "subscribe() is for live mode (v0.3); use history() for backtest"
        )
