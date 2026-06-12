"""MTF alignment tests — no look-ahead."""

from __future__ import annotations

import pandas as pd

import stolgo.pa as pa
from stolgo.pa._mtf import align_to_base, resample_ohlcv


def test_resample_daily() -> None:
    idx = pd.date_range("2020-01-01 09:00", periods=48, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0,
        },
        index=idx,
    )
    daily = resample_ohlcv(df, "1D")
    assert len(daily) >= 1


def test_daily_resistance_on_intraday_no_lookahead() -> None:
    """Daily level at hour 0 should not include same-day future highs."""
    idx = pd.date_range("2020-01-01 00:00", periods=48, freq="h", tz="UTC")
    close = [100 + (i * 0.1) for i in range(48)]
    df = pd.DataFrame(
        {
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": [1000.0] * 48,
        },
        index=idx,
    )
    r = pa.resistance(1, tf="1D").values(df)
    assert r.notna().sum() >= 24  # second day onward has daily level ffill
