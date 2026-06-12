# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Strategy ABC (HLD §4.4)."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from stolgo.core.events import FillEvent
    from stolgo.strategy.context import Context


class Strategy(ABC):
    entries: np.ndarray | None = None
    exits: np.ndarray | None = None

    def on_start(self, ctx: Context) -> None:
        pass

    def on_bar(self, ctx: Context) -> None:
        pass

    def on_fill(self, ctx: Context, fill: FillEvent) -> None:
        pass

    def on_end(self, ctx: Context) -> None:
        pass
