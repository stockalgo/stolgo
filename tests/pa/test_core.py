"""Tests for stolgo.pa core Rule combinators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stolgo.pa._bars import BarArrays
from stolgo.pa._core import Rule, _SeriesRule, rule_from_series
from stolgo.strategy.context import BarDataView, Context
from stolgo.core.types import Position


def _const_rule(name: str, flags: list[bool]) -> Rule:
    def fn(ohlcv: pd.DataFrame) -> pd.Series:
        n = len(ohlcv)
        return pd.Series(flags[:n], index=ohlcv.index, dtype=bool)

    return rule_from_series(name, fn)


def test_and_or_not(synthetic_100bars_df: pd.DataFrame) -> None:
    a = _const_rule("a", [True, False, True, False] + [False] * 96)
    b = _const_rule("b", [True, True, False, True] + [False] * 96)
    s = (a & b).series(synthetic_100bars_df)
    assert s.iloc[0]
    assert not s.iloc[1]
    assert (~a).series(synthetic_100bars_df).iloc[0] is np.bool_(False)


def test_then_rule() -> None:
    setup = [False, True, True, True, False]
    trigger = [False, False, True, False, False]
    r = _const_rule("s", setup).then(_const_rule("t", trigger))
    df = pd.DataFrame(
        {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
        index=pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC"),
    )
    s = r.series(df)
    assert not s.iloc[0]
    assert not s.iloc[1]
    assert s.iloc[2]  # trigger at 2, setup at 1


def test_rule_call_matches_series(synthetic_100bars_df: pd.DataFrame) -> None:
    flags = [i % 3 == 0 for i in range(100)]
    r = _const_rule("f", flags)
    s = r.series(synthetic_100bars_df)
    arrays = BarArrays.from_dataframe(synthetic_100bars_df)
    for i in (0, 10, 50, 99):
        ctx = Context(
            i=i,
            data=BarDataView(
                _open=arrays.open,
                _high=arrays.high,
                _low=arrays.low,
                _close=arrays.close,
                _volume=arrays.volume,
                _limit=i,
                _index=synthetic_100bars_df.index,
            ),
            position=Position("X", 0, 0),
        )
        assert r(ctx) == bool(s.iloc[i])


def test_all_of_any_of() -> None:
    df = pd.DataFrame(
        {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
        index=pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC"),
    )
    from stolgo.pa._core import all_of, any_of

    a = _const_rule("a", [True, False, True])
    b = _const_rule("b", [False, False, True])
    assert all_of(a, b).series(df).iloc[2]
    assert any_of(a, b).series(df).iloc[0]


import numpy as np
