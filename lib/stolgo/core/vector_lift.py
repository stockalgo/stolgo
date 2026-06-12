# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Vector-style entry/exit masks lifted to order intents (HLD §6.2, §7.1)."""

from __future__ import annotations

import numpy as np

from stolgo.strategy.context import Context


def apply_vector_signals(
    ctx: Context,
    i: int,
    entries: np.ndarray | None,
    exits: np.ndarray | None,
    *,
    entry_qty: float | None = None,
    entry_size_pct: float | None = None,
) -> None:
    """Emit buy/close intents from precomputed boolean masks at bar ``i``."""
    if entries is not None and bool(entries[i]) and ctx.position.flat:
        if entry_qty is not None:
            ctx.buy(qty=entry_qty)
        else:
            ctx.buy(size_pct=entry_size_pct if entry_size_pct is not None else 1.0)
    if exits is not None and bool(exits[i]) and not ctx.position.flat:
        ctx.close()


def _as_bool_mask(mask: np.ndarray, n_bars: int, name: str) -> np.ndarray:
    if len(mask) != n_bars:
        raise ValueError(f"{name} length {len(mask)} != bar count {n_bars}")
    return mask.astype(bool) if mask.dtype != bool else mask


def resolve_vector_masks(
    strategy_entries: np.ndarray | None,
    strategy_exits: np.ndarray | None,
    ctx_entries: np.ndarray | None,
    ctx_exits: np.ndarray | None,
    n_bars: int,
) -> tuple[np.ndarray | None, np.ndarray | None, bool]:
    entries = strategy_entries if strategy_entries is not None else ctx_entries
    exits = strategy_exits if strategy_exits is not None else ctx_exits
    if entries is None and exits is None:
        return None, None, False
    if entries is not None:
        entries = _as_bool_mask(np.asarray(entries), n_bars, "entries")
    if exits is not None:
        exits = _as_bool_mask(np.asarray(exits), n_bars, "exits")
    return entries, exits, True
