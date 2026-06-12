"""Tests for stolgo.pa levels."""

from __future__ import annotations

import pandas as pd

import stolgo.pa as pa


def _df(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=len(rows), freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": [r[0] for r in rows],
            "high": [r[1] for r in rows],
            "low": [r[2] for r in rows],
            "close": [r[3] for r in rows],
            "volume": [1000.0] * len(rows),
        },
        index=idx,
    )


def test_resistance_rolling_max_excludes_current_bar() -> None:
    df = _df([(10, 12, 9, 11), (11, 15, 10, 14), (14, 20, 13, 18)])
    r = pa.resistance(2).values(df)
    assert pd.isna(r.iloc[0])
    assert pd.isna(r.iloc[1])
    assert r.iloc[2] == 15.0


def test_support_and_level_constant() -> None:
    df = _df([(10, 12, 8, 11), (11, 13, 9, 10)])
    s = pa.support(1).values(df)
    assert s.iloc[1] == 8.0
    flat = pa.level(100.0).values(df)
    assert (flat == 100.0).all()


def test_range_high_low() -> None:
    df = _df([(1, 2, 0.5, 1), (1, 3, 0.5, 2), (2, 4, 1, 3), (3, 5, 2, 4)])
    rh = pa.range_high(2).values(df)
    assert rh.iloc[3] == 4.0  # max high of prior 2 bars: 3 and 4
