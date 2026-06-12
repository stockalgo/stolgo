# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from typing import Protocol

from stolgo.core.types import Side


class CommissionModel(Protocol):
    def fee(self, side: Side, price: float, qty: float) -> float: ...


class BpsCommission:
    def __init__(self, rate: float) -> None:
        self._rate = rate

    def fee(self, side: Side, price: float, qty: float) -> float:
        return price * qty * self._rate


class FlatCommission:
    def __init__(self, amount: float) -> None:
        self._amount = amount

    def fee(self, side: Side, price: float, qty: float) -> float:
        return self._amount
