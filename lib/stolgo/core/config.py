# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D
# [ ] no look-ahead: only data[:t+1] in strategy loop
# [ ] no pandas in oms/portfolio hot path
# [ ] no bandl imports outside stolgo.data / stolgo.broker
# [ ] fill default = next_open unless RunConfig.fill_on == "close"
# [ ] pytest tests for this module pass before next build step

"""Run configuration (HLD §4.1, §8)."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class RunConfig(BaseModel):
    """Immutable configuration for a single backtest run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["backtest"] = "backtest"
    seed: int = 42
    cash: float = 100_000.0
    commission: float = 0.0
    slippage_bps: float = 0.0
    fill_on: Literal["next_open", "close"] = "next_open"
    fast: bool = False
    symbol: str | None = None
    interval: str | None = None

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
