"""Tests for stolgo.report.trades."""

import pytest

from stolgo.core.events import FillEvent
from stolgo.core.types import Fill, Side
from stolgo.report.trades import build_trades_from_fills


def test_round_trip_trade():
    buy = FillEvent(
        fill=Fill("f1", "o1", "X", Side.BUY, 10.0, 100.0, 0.1, 1),
        order_id="o1",
        index=0,
    )
    sell = FillEvent(
        fill=Fill("f2", "o2", "X", Side.SELL, 10.0, 110.0, 0.1, 2),
        order_id="o2",
        index=1,
    )
    trades = build_trades_from_fills([buy, sell])
    assert len(trades) == 1
    assert trades.iloc[0]["gross_pnl"] == 100.0
    assert trades.iloc[0]["net_pnl"] == pytest.approx(99.8, rel=1e-3)
