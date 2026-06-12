"""Tests for stolgo.pa patterns."""

from __future__ import annotations

import pandas as pd

import stolgo.pa as pa
from stolgo.data.normalize import normalize_ohlcv


def test_bullish_engulfing_two_bars() -> None:
    idx = pd.date_range("2020-01-01", periods=2, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [10, 9],
            "high": [10.5, 11],
            "low": [9.5, 8.5],
            "close": [9.5, 10.5],
            "volume": [1000.0, 1000.0],
        },
        index=idx,
    )
    assert pa.bullish_engulfing().series(df).iloc[1]


def test_consolidation_and_breakout(synthetic_100bars_df: pd.DataFrame) -> None:
    s = pa.consolidation(7, range_pct=0.5).series(synthetic_100bars_df)
    assert s.dtype == bool


def test_streak_green_then_engulfing() -> None:
    idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [10, 10.2, 10.4, 10.6, 10.5],
            "high": [10.5, 10.7, 10.9, 11, 10.6],
            "low": [9.8, 10, 10.2, 10.4, 10],
            "close": [10.3, 10.5, 10.7, 10.9, 10.1],
            "volume": [1000.0] * 5,
        },
        index=idx,
    )
    r = pa.streak.green(3).then(pa.bearish())
    assert r.series(df).iloc[4]


def test_legacy_breakout_parity_shape() -> None:
    """Normalized OHLCV breakout_up should be computable on fixture."""
    path = __import__("pathlib").Path(__file__).parent.parent / "fixtures" / "synthetic_100bars.csv"
    raw = pd.read_csv(path)
    df = normalize_ohlcv(raw, symbol="SYN")
    s = pa.breakout_up(7, range_pct=0.12).series(df)
    assert len(s) == len(df)
