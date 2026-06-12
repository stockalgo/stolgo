# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from stolgo.broker.base import BrokerAdapter
from stolgo.core.exceptions import BrokerNotImplementedError


class PaperBroker(BrokerAdapter):
    """Stub — use SimBroker inside Engine for backtests (v0.1)."""

    def place_order(self, intent):
        raise BrokerNotImplementedError(
            "PaperBroker is not available in v0.1. Run Backtest(...).run() with SimBroker."
        )

    def modify_order(self, order_id: str, **kwargs) -> None:
        raise BrokerNotImplementedError("PaperBroker is not available in v0.1.")

    def cancel_order(self, order_id: str) -> None:
        raise BrokerNotImplementedError("PaperBroker is not available in v0.1.")

    def positions(self):
        raise BrokerNotImplementedError("PaperBroker is not available in v0.1.")

    def balance(self) -> float:
        raise BrokerNotImplementedError("PaperBroker is not available in v0.1.")

    def subscribe_bars(self, symbol: str, interval: str):
        raise BrokerNotImplementedError("PaperBroker is not available in v0.1.")

    def subscribe_fills(self):
        raise BrokerNotImplementedError("PaperBroker is not available in v0.1.")
