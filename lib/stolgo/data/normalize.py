"""OHLCV normalization (HLD §4.2, §G)."""

from __future__ import annotations

import pandas as pd

from stolgo.core.exceptions import DataError
from stolgo.core.types import Bar

CANONICAL_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close", "volume")

_COLUMN_MAP = {
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}


def normalize_ohlcv(
    df: pd.DataFrame,
    *,
    symbol: str | None = None,
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """Validate and normalize OHLCV to UTC-indexed lowercase columns."""
    if df.empty:
        raise DataError("OHLCV DataFrame is empty")

    work = df.copy()
    if timestamp_col in work.columns:
        work[timestamp_col] = pd.to_datetime(work[timestamp_col], utc=True)
        work = work.set_index(timestamp_col)
    elif not isinstance(work.index, pd.DatetimeIndex):
        raise DataError(f"expected DatetimeIndex or column {timestamp_col!r}")

    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC")
    else:
        work.index = work.index.tz_convert("UTC")

    rename = {c: _COLUMN_MAP[c] for c in work.columns if c in _COLUMN_MAP}
    work = work.rename(columns=rename)
    missing = [c for c in CANONICAL_COLUMNS if c not in work.columns]
    if missing:
        raise DataError(f"missing OHLCV columns: {missing}")

    cols = list(CANONICAL_COLUMNS)
    work = work[cols].astype("float64")
    if work[cols].isna().any().any():
        raise DataError("NaN values in OHLCV columns are not allowed")

    if not work.index.is_monotonic_increasing:
        work = work.sort_index()

    if work.index.has_duplicates:
        dupes = work.index[work.index.duplicated()].unique()[:5].tolist()
        raise DataError(f"duplicate timestamps: {dupes}")

    for col in ("open", "high", "low", "close"):
        if (work[col] <= 0).any():
            raise DataError(f"non-positive prices in column {col}")

    if symbol is not None:
        work.attrs["symbol"] = symbol

    return work


def bars_from_dataframe(df: pd.DataFrame, *, symbol: str = "UNKNOWN") -> tuple[Bar, ...]:
    """Convert normalized DataFrame to Bar tuple (cold path at engine start)."""
    if df.empty:
        return ()
    sym = str(df.attrs.get("symbol", symbol))
    ts = df.index.asi8.tolist()
    cols = [df[c].to_numpy("float64").tolist() for c in ("open", "high", "low", "close", "volume")]
    return tuple(Bar(t, o, h, l, c, v, sym) for t, o, h, l, c, v in zip(ts, *cols))
