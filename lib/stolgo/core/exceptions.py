# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D
# [ ] no look-ahead: only data[:t+1] in strategy loop
# [ ] no pandas in oms/portfolio hot path
# [ ] no bandl imports outside stolgo.data / stolgo.broker
# [ ] fill default = next_open unless RunConfig.fill_on == "close"
# [ ] pytest tests for this module pass before next build step

"""Typed exceptions for stolgo (HLD §4.1, engineering §6)."""

from __future__ import annotations


class StolgoError(Exception):
    """Base exception for all stolgo errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DataError(StolgoError):
    """Invalid or unusable market data (schema, NaN, ordering, range)."""


class LookaheadError(StolgoError):
    """Strategy or engine accessed data beyond the current bar index."""


class ConfigurationError(StolgoError):
    """Invalid RunConfig or engine setup."""


class OrderRejectedError(StolgoError):
    """Order intent rejected by risk middleware or OMS."""


class ModeNotSupportedError(StolgoError):
    """Requested run mode is not implemented (live/paper until v0.3)."""


class BrokerNotImplementedError(StolgoError):
    """Broker adapter method not available in this release."""
