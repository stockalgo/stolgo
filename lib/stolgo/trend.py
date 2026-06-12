"""Legacy trend API — use ``stolgo.pa`` instead."""

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


class Trend:
    """Deprecated — use :func:`stolgo.pa.giant_uptrend` / :func:`stolgo.pa.giant_downtrend`."""

    def __init__(self, periods: int = 13, percentage: float = 2) -> None:
        warnings.warn(
            "stolgo.trend.Trend is deprecated; use stolgo.pa",
            DeprecationWarning,
            stacklevel=2,
        )
        self.periods = periods
        self.percentage = percentage

    def is_giant_uptrend(
        self,
        dfs: pd.DataFrame,
        periods: int | None = None,
        percentage: float | None = None,
    ) -> bool:
        periods = periods or self.periods
        if dfs.shape[0] < periods:
            raise BadDataError("Data is not enough for this periods")
        df = _normalize_legacy_df(dfs)
        return bool(pa.giant_uptrend(periods=periods).series(df).iloc[-1])

    def is_giant_downtrend(
        self,
        dfs: pd.DataFrame,
        periods: int | None = None,
        percentage: float | None = None,
    ) -> bool:
        periods = periods or self.periods
        if dfs.shape[0] < periods:
            raise BadDataError("Data is not enough for this periods")
        df = _normalize_legacy_df(dfs)
        return bool(pa.giant_downtrend(periods=periods).series(df).iloc[-1])
