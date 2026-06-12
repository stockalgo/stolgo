"""Tests for stolgo.data.bandl_source."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from stolgo.core.exceptions import DataError
from stolgo.data.bandl_source import BandlDataSource
from stolgo.data.cache import ParquetCache


def test_mock_client_no_network(mock_bandl_client, tmp_path) -> None:
    cache = ParquetCache(root=tmp_path)
    src = BandlDataSource(mock_bandl_client, cache=cache)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    df = src.history("BTCUSDT", "1h", start, end)
    assert len(df) == 48
    assert "close" in df.columns


def test_cache_hit_skips_second_fetch(mock_bandl_client, tmp_path) -> None:
    class CountingFacet:
        calls = 0

        def get_ohlcv_dataframe(self, *args, **kwargs):
            CountingFacet.calls += 1
            return mock_bandl_client.crypto.get_ohlcv_dataframe(*args, **kwargs)

    class CountingClient:
        crypto = CountingFacet()
        equity = CountingFacet()

    cache = ParquetCache(root=tmp_path)
    src = BandlDataSource(CountingClient(), cache=cache)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    src.history("BTCUSDT", "1h", start, end)
    src.history("BTCUSDT", "1h", start, end)
    assert CountingFacet.calls == 1


def test_start_after_end_raises(mock_bandl_client) -> None:
    src = BandlDataSource(mock_bandl_client)
    t = datetime(2020, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(DataError):
        src.history("BTC", "1d", t, t)
