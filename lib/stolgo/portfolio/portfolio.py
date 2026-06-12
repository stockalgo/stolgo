# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from stolgo.core.types import Bar, Fill, Position, Side


class Portfolio:
    def __init__(self, cash: float, symbol: str) -> None:
        self._cash = cash
        self._position = Position(symbol=symbol)

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def position(self) -> Position:
        return self._position

    def apply_fill(self, fill: Fill) -> None:
        notional = fill.price * fill.qty
        if fill.side == Side.BUY:
            self._cash -= notional + fill.commission
            new_qty = self._position.qty + fill.qty
            if new_qty > 0:
                self._position.avg_entry_price = (
                    self._position.avg_entry_price * self._position.qty + notional
                ) / new_qty
            self._position.qty = new_qty
        else:
            self._cash += notional - fill.commission
            self._position.qty -= fill.qty
            if abs(self._position.qty) < 1e-12:
                self._position.qty = 0.0
                self._position.avg_entry_price = 0.0

    def mark_to_market(self, bar: Bar) -> float:
        return self._cash + self._position.qty * bar.close
