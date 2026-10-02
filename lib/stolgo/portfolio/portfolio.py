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
        old_qty = self._position.qty
        fill_signed = fill.qty if fill.side == Side.BUY else -fill.qty
        new_qty = old_qty + fill_signed

        if fill.side == Side.BUY:
            self._cash -= notional + fill.commission
        else:
            self._cash += notional - fill.commission

        if abs(new_qty) < 1e-12:
            self._position.qty = 0.0
            self._position.avg_entry_price = 0.0
        elif old_qty == 0.0:
            self._position.qty = new_qty
            self._position.avg_entry_price = fill.price
        elif (old_qty > 0 and fill_signed > 0) or (old_qty < 0 and fill_signed < 0):
            self._position.avg_entry_price = (
                self._position.avg_entry_price * abs(old_qty) + notional
            ) / abs(new_qty)
            self._position.qty = new_qty
        elif (old_qty > 0 and new_qty > 0) or (old_qty < 0 and new_qty < 0):
            self._position.qty = new_qty
        else:
            self._position.qty = new_qty
            self._position.avg_entry_price = fill.price

        if abs(self._cash) < 1e-9:
            self._cash = 0.0

    def mark_to_market(self, bar: Bar) -> float:
        return self._cash + self._position.qty * bar.close
