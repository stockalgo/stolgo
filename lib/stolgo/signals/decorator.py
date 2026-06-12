# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Indicator metadata decorator."""

from __future__ import annotations

from typing import Callable


def indicator(fn: Callable) -> Callable:
    fn._stolgo_indicator = True  # type: ignore[attr-defined]
    fn._stolgo_panel = getattr(fn, "_stolgo_panel", "main")  # type: ignore[attr-defined]
    return fn
