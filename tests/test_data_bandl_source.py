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


def test_asset_type_passthrough_for_futures(mock_bandl_client, tmp_path) -> None:
    """BandlDataSource must forward asset_type so callers can request crypto
    futures/perp OHLCV (e.g. Binance USDT-M) instead of the provider default
    (crypto_spot)."""
    captured: dict = {}

    class CapturingFacet:
        def get_ohlcv_dataframe(self, symbol, interval, start, end, **kwargs):
            captured.update(kwargs)
            return mock_bandl_client.crypto.get_ohlcv_dataframe(symbol, interval, start, end)

    class CapturingClient:
        crypto = CapturingFacet()
        equity = CapturingFacet()

    cache = ParquetCache(root=tmp_path)
    src = BandlDataSource(CapturingClient(), cache=cache, asset_type="crypto_perp")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    src.history("BTCUSDT", "1d", start, end)
    assert captured.get("asset_type") == "crypto_perp"


def test_asset_type_call_override(mock_bandl_client, tmp_path) -> None:
    captured: dict = {}

    class CapturingFacet:
        def get_ohlcv_dataframe(self, symbol, interval, start, end, **kwargs):
            captured.update(kwargs)
            return mock_bandl_client.crypto.get_ohlcv_dataframe(symbol, interval, start, end)

    class CapturingClient:
        crypto = CapturingFacet()
        equity = CapturingFacet()

    cache = ParquetCache(root=tmp_path)
    src = BandlDataSource(CapturingClient(), cache=cache)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    src.history("BTCUSDT", "1d", start, end, asset_type="crypto_perp")
    assert captured.get("asset_type") == "crypto_perp"
