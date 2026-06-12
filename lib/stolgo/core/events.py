# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D
# [ ] no look-ahead: only data[:t+1] in strategy loop
# [ ] no pandas in oms/portfolio hot path
# [ ] no bandl imports outside stolgo.data / stolgo.broker
# [ ] fill default = next_open unless RunConfig.fill_on == "close"
# [ ] pytest tests for this module pass before next build step

"""Event envelopes for the deterministic engine bus (HLD §4.1)."""

from __future__ import annotations

from dataclasses import dataclass

from stolgo.core.types import Bar, Fill, Order, OrderId, Side, Symbol


@dataclass(frozen=True, slots=True)
class BarEvent:
    bar: Bar
    index: int


@dataclass(frozen=True, slots=True)
class OrderEvent:
    order: Order
    index: int


@dataclass(frozen=True, slots=True)
class FillEvent:
    fill: Fill
    order_id: OrderId
    index: int


@dataclass(frozen=True, slots=True)
class SignalEvent:
    symbol: Symbol
    side: Side | None
    index: int
    tag: str | None = None
    rejected: bool = False


@dataclass(frozen=True, slots=True)
class TimerEvent:
    ts: int
    name: str
