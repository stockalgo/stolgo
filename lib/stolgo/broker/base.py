# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from abc import ABC, abstractmethod

from stolgo.core.exceptions import BrokerNotImplementedError
from stolgo.core.types import OrderIntent, Position


class BrokerAdapter(ABC):
    """Implementors: BandlBroker (v0.3), custom brokers via entry point (v1.0)."""

    @abstractmethod
    def place_order(self, intent: OrderIntent) -> str:
        raise BrokerNotImplementedError("place_order — v0.3")

    @abstractmethod
    def modify_order(self, order_id: str, **kwargs) -> None:
        raise BrokerNotImplementedError("modify_order — v0.3")

    @abstractmethod
    def cancel_order(self, order_id: str) -> None:
        raise BrokerNotImplementedError("cancel_order — v0.3")

    @abstractmethod
    def positions(self) -> dict[str, Position]:
        raise BrokerNotImplementedError("positions — v0.3")

    @abstractmethod
    def balance(self) -> float:
        raise BrokerNotImplementedError("balance — v0.3")

    @abstractmethod
    def subscribe_bars(self, symbol: str, interval: str):
        raise BrokerNotImplementedError("subscribe_bars — v0.3")

    @abstractmethod
    def subscribe_fills(self):
        raise BrokerNotImplementedError("subscribe_fills — v0.3")
