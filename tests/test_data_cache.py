"""Tests for stolgo.data.cache."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from stolgo.data.cache import ParquetCache


def test_put_get_roundtrip(tmp_path, synthetic_100bars_df: pd.DataFrame) -> None:
    cache = ParquetCache(root=tmp_path)
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2020, 5, 1, tzinfo=timezone.utc)
    key = cache.make_key("binance", "BTC", "1d", start, end)
    assert cache.get(key) is None
    cache.put(key, synthetic_100bars_df)
    hit = cache.get(key)
    assert hit is not None
    assert len(hit) == len(synthetic_100bars_df)
