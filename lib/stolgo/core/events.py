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


@dataclass(frozen=True, slots=True)
class RiskHaltEvent:
    index: int
    drawdown: float = 0.0
    type: str = "RISK_HALT"


@dataclass(frozen=True, slots=True)
class OrderRejectedEvent:
    order_id: str
    reason: str
    index: int
    type: str = "ORDER_REJECTED"
