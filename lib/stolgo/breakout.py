"""Legacy breakout API — use ``stolgo.pa`` instead."""

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


class Breakout:
    """Deprecated — use :func:`stolgo.pa.consolidation` and :func:`stolgo.pa.breakout_up`."""

    def __init__(self, periods: int = 13, percentage: float = 2) -> None:
        warnings.warn(
            "stolgo.breakout.Breakout is deprecated; use stolgo.pa (see docs/PA.md)",
            DeprecationWarning,
            stacklevel=2,
        )
        self.periods = periods
        self.percentage = percentage

    def is_consolidating(
        self,
        dfs: pd.DataFrame,
        periods: int | None = None,
        percentage: float | None = None,
    ) -> bool:
        periods = periods or self.periods
        percentage = percentage or self.percentage
        if dfs.shape[0] < periods:
            raise BadDataError("Data is not enough for this periods")
        df = _normalize_legacy_df(dfs)
        rule = pa.consolidation(periods, range_pct=percentage / 100.0)
        return bool(rule.series(df).iloc[-1])

    def is_breaking_out(
        self,
        dfs: pd.DataFrame,
        periods: int | None = None,
        percentage: float | None = None,
    ) -> bool:
        periods = periods or self.periods
        percentage = percentage or self.percentage
        df = _normalize_legacy_df(dfs)
        rule = pa.breakout_up(periods, range_pct=percentage / 100.0)
        return bool(rule.series(df).iloc[-1])

    def is_breaking_down(
        self,
        dfs: pd.DataFrame,
        periods: int | None = None,
        percentage: float | None = None,
    ) -> bool:
        periods = periods or self.periods
        percentage = percentage or self.percentage
        df = _normalize_legacy_df(dfs)
        rule = pa.breakout_down(periods, range_pct=percentage / 100.0)
        return bool(rule.series(df).iloc[-1])
