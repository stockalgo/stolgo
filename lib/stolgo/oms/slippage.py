# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from typing import Protocol

from stolgo.core.types import Side


class SlippageModel(Protocol):
    def adjust(self, side: Side, price: float, qty: float) -> float: ...


class NoSlippage:
    def adjust(self, side: Side, price: float, qty: float) -> float:
        return price


class BpsSlippage:
    def __init__(self, bps: float) -> None:
        self._bps = bps

    def adjust(self, side: Side, price: float, qty: float) -> float:
        slip = price * (self._bps / 10_000)
        return price + slip if side == Side.BUY else price - slip
