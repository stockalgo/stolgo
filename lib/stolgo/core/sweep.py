# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Parameter sweep helpers (HLD §7.3) — v0.2."""

from __future__ import annotations

from itertools import product
from typing import Any, Callable, Iterable

import pandas as pd

from stolgo.core.config import RunConfig
from stolgo.core.engine import Backtest
from stolgo.strategy.base import Strategy
from stolgo.report.result import RunResult


def parameter_sweep(
    strategy_factory: Callable[[dict[str, Any]], Strategy],
    param_grid: dict[str, Iterable[Any]],
    data: pd.DataFrame,
    *,
    config: RunConfig | None = None,
    **run_kwargs: Any,
) -> pd.DataFrame:
    """Run backtest for each combination in ``param_grid``; return summary rows."""
    keys = list(param_grid.keys())
    values = [list(param_grid[k]) for k in keys]
    rows: list[dict[str, Any]] = []
    base_cfg = config or RunConfig()

    cfg_keys = set(RunConfig.model_fields.keys())
    base = {**base_cfg.model_dump(), **run_kwargs}
    run_kwargs_clean = {k: v for k, v in base.items() if k in cfg_keys}

    for combo in product(*values):
        params = dict(zip(keys, combo))
        strategy = strategy_factory(params)
        result: RunResult = Backtest(strategy, data, **run_kwargs_clean).run()
        row = {**params, **result.metrics}
        rows.append(row)

    return pd.DataFrame(rows)
