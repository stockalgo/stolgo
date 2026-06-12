"""Tests for stolgo.data.normalize."""

from __future__ import annotations

import pandas as pd
import pytest

from stolgo.core.exceptions import DataError
from stolgo.data.normalize import bars_from_dataframe, normalize_ohlcv


def test_happy_path(synthetic_100bars_df: pd.DataFrame) -> None:
    df = normalize_ohlcv(synthetic_100bars_df.reset_index(), symbol="TEST")
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.tz is not None
    bars = bars_from_dataframe(df, symbol="TEST")
    assert len(bars) == len(df)


def test_empty_raises() -> None:
    with pytest.raises(DataError, match="empty"):
        normalize_ohlcv(pd.DataFrame())


def test_duplicate_timestamps_raises() -> None:
    df = pd.DataFrame(
        {
            "timestamp": ["2020-01-01", "2020-01-01"],
            "open": [1, 1],
            "high": [2, 2],
            "low": [0.5, 0.5],
            "close": [1.5, 1.5],
            "volume": [100, 100],
        }
    )
    with pytest.raises(DataError, match="duplicate"):
        normalize_ohlcv(df)


def test_nan_raises() -> None:
    df = pd.DataFrame(
        {
            "timestamp": ["2020-01-01"],
            "open": [1.0],
            "high": [2.0],
            "low": [0.5],
            "close": [float("nan")],
            "volume": [100.0],
        }
    )
    with pytest.raises(DataError, match="NaN"):
        normalize_ohlcv(df)
