"""Tests for stolgo.pa relations."""

from __future__ import annotations

import pandas as pd

import stolgo.pa as pa


def _df() -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": [10, 10, 10, 10, 10],
            "high": [11, 11, 12, 11.5, 10.5],
            "low": [9, 9, 9, 9.5, 9],
            "close": [10, 10.5, 11.5, 10, 9.5],
            "volume": [1000.0] * 5,
        },
        index=idx,
    )


def test_crosses_above() -> None:
    df = _df()
    lv = pa.level(11.0)
    s = pa.crosses_above(lv).series(df)
    assert s.iloc[2]


def test_rejected_at() -> None:
    df = _df()
    lv = pa.level(11.0)
    s = pa.rejected_at(lv).series(df)
    assert s.iloc[3]


def test_crosses_below() -> None:
    idx = pd.date_range("2020-01-01", periods=4, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [12, 11, 10, 9],
            "high": [12, 11, 10, 9],
            "low": [11, 10, 9, 8],
            "close": [11.5, 10.5, 9.5, 8.5],
            "volume": [1000.0] * 4,
        },
        index=idx,
    )
    s = pa.crosses_below(pa.level(10.0)).series(df)
    assert s.iloc[2]
