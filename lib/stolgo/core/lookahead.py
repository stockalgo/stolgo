"""Look-ahead probe for vector strategies and masks (Plan 04 §C9)."""

from __future__ import annotations

import copy
from typing import Any, Callable

import numpy as np
import pandas as pd

from stolgo.core.exceptions import LookaheadError
from stolgo.core.types import Position
from stolgo.core.vector_lift import resolve_vector_masks
from stolgo.data.normalize import normalize_ohlcv
from stolgo.strategy.base import Strategy
from stolgo.strategy.context import BarDataView, Context


def _make_ctx(df: pd.DataFrame) -> tuple[Context, int]:
    df_norm = normalize_ohlcv(df)
    n = len(df_norm)
    bar_index = pd.DatetimeIndex(df_norm.index, tz="UTC")
    arrays = {
        "open": df_norm["open"].to_numpy(dtype=np.float64),
        "high": df_norm["high"].to_numpy(dtype=np.float64),
        "low": df_norm["low"].to_numpy(dtype=np.float64),
        "close": df_norm["close"].to_numpy(dtype=np.float64),
        "volume": df_norm["volume"].to_numpy(dtype=np.float64),
    }
    data_view = BarDataView(
        _open=arrays["open"],
        _high=arrays["high"],
        _low=arrays["low"],
        _close=arrays["close"],
        _volume=arrays["volume"],
        _limit=n - 1,
        _index=bar_index,
    )
    pos = Position(str(df_norm.attrs.get("symbol", "UNKNOWN")), 0.0, 0.0)
    ctx = Context(i=0, data=data_view, position=pos)
    return ctx, n


def probe(
    strategy_factory: Callable[[], Strategy] | Strategy,
    df: pd.DataFrame,
    cuts: tuple[float, ...] = (0.25, 0.5, 0.75),
) -> None:
    """Probe a vector strategy for look-ahead bias across sub-slices of df.

    For each cut fraction k in cuts, builds the strategy on df.iloc[:k] and asserts
    that entries[:k] and exits[:k] equal the full-run masks' prefixes.
    Raises LookaheadError if there is any mismatch.
    """
    if callable(strategy_factory) and not isinstance(strategy_factory, Strategy):
        get_strat: Callable[[], Strategy] = strategy_factory
    else:
        get_strat = lambda: copy.deepcopy(strategy_factory)

    strat_full = get_strat()
    ctx_full, n_full = _make_ctx(df)
    strat_full.on_start(ctx_full)
    entries_full, exits_full, use_vector = resolve_vector_masks(
        strat_full.entries,
        strat_full.exits,
        ctx_full.entries,
        ctx_full.exits,
        n_full,
    )

    if not use_vector:
        return

    for c in cuts:
        k = int(n_full * c)
        if k <= 0:
            continue
        df_cut = df.iloc[:k]
        strat_cut = get_strat()
        ctx_cut, n_cut = _make_ctx(df_cut)
        strat_cut.on_start(ctx_cut)
        entries_cut, exits_cut, _ = resolve_vector_masks(
            strat_cut.entries,
            strat_cut.exits,
            ctx_cut.entries,
            ctx_cut.exits,
            n_cut,
        )

        if entries_full is not None and entries_cut is not None:
            if not np.array_equal(entries_cut, entries_full[:k]):
                mismatch_idx = np.where(entries_cut != entries_full[:k])[0]
                raise LookaheadError(
                    f"Look-ahead detected in entries at cut {c} (k={k}): first mismatch at bar {mismatch_idx[0]}"
                )
        if exits_full is not None and exits_cut is not None:
            if not np.array_equal(exits_cut, exits_full[:k]):
                mismatch_idx = np.where(exits_cut != exits_full[:k])[0]
                raise LookaheadError(
                    f"Look-ahead detected in exits at cut {c} (k={k}): first mismatch at bar {mismatch_idx[0]}"
                )
