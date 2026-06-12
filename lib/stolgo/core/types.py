# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D
# [ ] no look-ahead: only data[:t+1] in strategy loop
# [ ] no pandas in oms/portfolio hot path
# [ ] no bandl imports outside stolgo.data / stolgo.broker
# [ ] fill default = next_open unless RunConfig.fill_on == "close"
# [ ] pytest tests for this module pass before next build step

"""Canonical domain types (HLD §4.1). Notional amounts are unitless floats (USD/INR)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

OrderId = str
Symbol = str
Price = float
Qty = float


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Bar:
    """Single OHLCV bar; ``ts`` is UTC nanoseconds since epoch."""

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str


@dataclass(frozen=True, slots=True)
class Order:
    order_id: OrderId
    symbol: Symbol
    side: Side
    order_type: OrderType
    qty: Qty
    limit_price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    client_order_id: str | None = None
    tag: str | None = None


@dataclass(frozen=True, slots=True)
class Fill:
    fill_id: str
    order_id: OrderId
    symbol: Symbol
    side: Side
    qty: Qty
    price: Price
    commission: float
    ts: int


@dataclass
class Position:
    symbol: Symbol
    qty: float = 0.0
    avg_entry_price: float = 0.0

    @property
    def flat(self) -> bool:
        return self.qty == 0.0


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Strategy order request before sizing and OMS submission."""

    symbol: Symbol
    side: Side
    order_type: OrderType
    qty: Qty | None = None
    size_pct: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
    tag: str | None = None

    def __post_init__(self) -> None:
        if self.qty is not None and self.qty <= 0:
            raise ValueError("OrderIntent.qty must be positive when set")
        if self.size_pct is not None and self.size_pct <= 0:
            raise ValueError("OrderIntent.size_pct must be positive when set")
