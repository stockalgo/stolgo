# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Load normalized OHLCV from local files (CSV, Parquet)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from stolgo.core.exceptions import DataError
from stolgo.data.normalize import normalize_ohlcv


def load(
    path: str | Path,
    *,
    symbol: str | None = None,
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """Load OHLCV from a CSV or Parquet file and return a normalized DataFrame.

    Columns are lowercased to ``open``, ``high``, ``low``, ``close``, ``volume``
    with a UTC ``DatetimeIndex``. Use :class:`~stolgo.data.bandl_source.Bandl`
    for live/historical market data via `bandl`.

    Args:
        path: File path ending in ``.csv``, ``.parquet``, or ``.pq``.
        symbol: Optional symbol stored on the frame (defaults to file stem).
        timestamp_col: Name of the timestamp column when not using the index.

    Returns:
        Normalized OHLCV DataFrame ready for :class:`stolgo.Backtest`.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        raw = pd.read_csv(file_path)
    elif suffix in (".parquet", ".pq"):
        raw = pd.read_parquet(file_path)
    else:
        raise DataError(f"unsupported file type {suffix!r}; use .csv or .parquet")

    sym = symbol or file_path.stem.upper()
    return normalize_ohlcv(raw, symbol=sym, timestamp_col=timestamp_col)
