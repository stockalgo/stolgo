"""stolgo core — types, events, config, engine."""

from stolgo.core.config import RunConfig
from stolgo.core.engine import Backtest, Engine
from stolgo.core.events import (
    BarEvent,
    FillEvent,
    OrderEvent,
    OrderRejectedEvent,
    RiskHaltEvent,
    SignalEvent,
    TimerEvent,
)
from stolgo.core.lookahead import probe
from stolgo.core.exceptions import (
    AccountingError,
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
    "AccountingError",
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
    "OrderRejectedEvent",
    "OrderStatus",
    "OrderType",
    "Position",
    "probe",
    "RiskHaltEvent",
    "RunConfig",
    "Side",
    "SignalEvent",
    "StolgoError",
    "TimerEvent",
]
