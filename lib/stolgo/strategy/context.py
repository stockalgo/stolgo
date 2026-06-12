# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Strategy context (HLD §4.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from stolgo.core.exceptions import LookaheadError
from stolgo.core.types import OrderIntent, OrderType, Position, Side


@dataclass
class BarDataView:
    _open: np.ndarray
    _high: np.ndarray
    _low: np.ndarray
    _close: np.ndarray
    _volume: np.ndarray
    _limit: int
    _index: pd.DatetimeIndex | None = None

    @property
    def open(self) -> np.ndarray:
        return self._open[: self._limit + 1]

    @property
    def high(self) -> np.ndarray:
        return self._high[: self._limit + 1]

    @property
    def low(self) -> np.ndarray:
        return self._low[: self._limit + 1]

    @property
    def close(self) -> np.ndarray:
        return self._close[: self._limit + 1]

    @property
    def volume(self) -> np.ndarray:
        return self._volume[: self._limit + 1]

    def _check(self, idx: int) -> None:
        if idx > self._limit:
            raise LookaheadError(f"cannot access index {idx} at bar {self._limit}")

    def __len__(self) -> int:
        return self._limit + 1

    @property
    def index(self) -> pd.DatetimeIndex:
        if self._index is not None:
            return self._index[: self._limit + 1]
        return pd.DatetimeIndex(range(self._limit + 1), tz="UTC")


@dataclass
class Context:
    i: int
    data: BarDataView
    position: Position
    entries: np.ndarray | None = None
    exits: np.ndarray | None = None
    _intents: list[OrderIntent] = field(default_factory=list)

    def buy(self, *, qty: float | None = None, size_pct: float | None = None, tag: str | None = None) -> OrderIntent:
        intent = OrderIntent(
            symbol=self.position.symbol,
            side=Side.BUY,
            order_type=OrderType.MARKET,
            qty=qty,
            size_pct=size_pct,
            tag=tag,
        )
        self._intents.append(intent)
        return intent

    def sell(self, *, qty: float | None = None, size_pct: float | None = None, tag: str | None = None) -> OrderIntent:
        intent = OrderIntent(
            symbol=self.position.symbol,
            side=Side.SELL,
            order_type=OrderType.MARKET,
            qty=qty,
            size_pct=size_pct,
            tag=tag,
        )
        self._intents.append(intent)
        return intent

    def close(self, *, tag: str | None = None) -> OrderIntent | None:
        if self.position.flat:
            return None
        qty = abs(self.position.qty)
        if self.position.qty > 0:
            return self.sell(qty=qty, tag=tag)
        return self.buy(qty=qty, tag=tag)

    def consume_intents(self) -> list[OrderIntent]:
        out = list(self._intents)
        self._intents.clear()
        return out
