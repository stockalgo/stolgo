"""stolgo — quant-grade backtesting (greenfield API)."""

from stolgo.core.config import RunConfig
from stolgo.core.engine import Backtest, Engine
from stolgo.core.exceptions import StolgoError
from stolgo.core.sweep import parameter_sweep
from stolgo.core.types import Bar, Fill, Order, OrderIntent, OrderType, Position, Side
from stolgo.data import Bandl, BandlDataSource, load
from stolgo.report.result import RunResult
from stolgo.signals.pipeline import Pipeline
from stolgo.strategy import Context, Strategy
from stolgo import trade as trade

__all__ = [
    "Backtest",
    "Bandl",
    "BandlDataSource",
    "Bar",
    "Context",
    "Engine",
    "Fill",
    "Order",
    "OrderIntent",
    "OrderType",
    "Pipeline",
    "Position",
    "RunConfig",
    "RunResult",
    "Side",
    "StolgoError",
    "Strategy",
    "load",
    "parameter_sweep",
    "trade",
]
