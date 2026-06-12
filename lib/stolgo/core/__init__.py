"""stolgo core — types, events, config, engine."""

from stolgo.core.config import RunConfig
from stolgo.core.engine import Backtest, Engine
from stolgo.core.events import BarEvent, FillEvent, OrderEvent, SignalEvent, TimerEvent
from stolgo.core.exceptions import (
    BrokerNotImplementedError,
    ConfigurationError,
    DataError,
    LookaheadError,
    ModeNotSupportedError,
    OrderRejectedError,
    StolgoError,
)
from stolgo.core.types import (
    Bar,
    Fill,
    Order,
    OrderIntent,
    OrderStatus,
    OrderType,
    Position,
    Side,
)

__all__ = [
    "Backtest",
    "Bar",
    "Engine",
    "BarEvent",
    "BrokerNotImplementedError",
    "ConfigurationError",
    "DataError",
    "Fill",
    "FillEvent",
    "LookaheadError",
    "ModeNotSupportedError",
    "Order",
    "OrderEvent",
    "OrderIntent",
    "OrderRejectedError",
    "OrderStatus",
    "OrderType",
    "Position",
    "RunConfig",
    "Side",
    "SignalEvent",
    "StolgoError",
    "TimerEvent",
]
