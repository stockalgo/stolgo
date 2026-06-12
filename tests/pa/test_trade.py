"""Tests for stolgo.trade brackets."""

from __future__ import annotations

import pandas as pd

from stolgo.core.types import Position
from stolgo.strategy.context import BarDataView, Context
from stolgo.core.types import Side
from stolgo.trade import Bracket, bracket_hit, close, long, short


def _ctx(i: int, ohlc: tuple[float, float, float, float]) -> Context:
    o, h, l, c = ohlc
    n = i + 1
    arrays = {
        "open": [o] * n,
        "high": [h] * n,
        "low": [l] * n,
        "close": [c] * n,
        "volume": [1000.0] * n,
    }
    import numpy as np

    return Context(
        i=i,
        data=BarDataView(
            _open=np.array(arrays["open"], dtype=np.float64),
            _high=np.array(arrays["high"], dtype=np.float64),
            _low=np.array(arrays["low"], dtype=np.float64),
            _close=np.array(arrays["close"], dtype=np.float64),
            _volume=np.array(arrays["volume"], dtype=np.float64),
            _limit=i,
        ),
        position=Position("X", 0, 0),
    )


def test_long_bracket_stop_hit() -> None:
    ctx = _ctx(0, (100, 101, 99, 100))
    b = long(ctx, rr=(1, 2), stop="candle_low", qty=1.0)
    assert b is not None
    ctx2 = _ctx(1, (100, 101, 98, 99))
    assert bracket_hit(ctx2, b) == "stop"


def test_short_bracket_target() -> None:
    ctx = _ctx(0, (100, 102, 99, 100))
    b = short(ctx, rr=(1, 2), stop="candle_high", qty=1.0)
    assert b is not None
    assert b.target_price < b.entry_price


def test_close_short_issues_buy() -> None:
    ctx = _ctx(0, (100, 100, 100, 100))
    ctx.position = Position("X", -1.0, 100.0)
    intent = ctx.close(tag="cover")
    assert intent is not None
    assert intent.side == Side.BUY
