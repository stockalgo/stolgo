"""Run configuration (HLD §4.1, §8)."""

from __future__ import annotations

import hashlib
import json
from typing import Literal
import warnings

from pydantic import BaseModel, ConfigDict, field_validator


class RunConfig(BaseModel):
    """Immutable configuration for a single backtest run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["backtest"] = "backtest"
    seed: int = 42
    cash: float = 100_000.0
    commission: float = 0.0
    slippage_bps: float = 0.0
    fill_on: Literal["next_open", "next_close", "signal_close", "close"] = "next_open"
    fast: bool = False
    symbol: str | None = None
    interval: str | None = None
    halt_drawdown: float | None = None
    allow_leverage: bool = False
    close_at_end: bool = True
    lookahead_check: bool = False

    @field_validator("fill_on")
    @classmethod
    def _validate_fill_on(cls, v: str) -> str:
        if v == "close":
            warnings.warn(
                "fill_on='close' is deprecated, use fill_on='next_close'",
                DeprecationWarning,
                stacklevel=2,
            )
        return v

    @field_validator("cash")
    @classmethod
    def _cash_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("cash must be positive")
        return v

    def params_hash(self) -> str:
        """Stable hash of config for reproducibility keys."""
        payload = self.model_dump(mode="json")
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
