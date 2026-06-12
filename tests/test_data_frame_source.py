"""Tests for stolgo.data.frame_source."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from stolgo.core.exceptions import DataError
from stolgo.data.frame_source import DataFrameSource


def test_slice_range(synthetic_100bars_df: pd.DataFrame) -> None:
    src = DataFrameSource(synthetic_100bars_df, symbol="TEST")
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2020, 2, 1, tzinfo=timezone.utc)
    out = src.history("TEST", "1d", start, end)
    assert not out.empty


def test_invalid_range(synthetic_100bars_df: pd.DataFrame) -> None:
    src = DataFrameSource(synthetic_100bars_df, symbol="TEST")
    t = datetime(2020, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(DataError):
        src.history("TEST", "1d", t, t)
