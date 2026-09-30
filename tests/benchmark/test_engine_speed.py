"""Benchmark test for engine performance on 200k bars (§7-f)."""

import time
import numpy as np
import pandas as pd
import pytest

from stolgo import Backtest, Context, Strategy


class FastMom50(Strategy):
    lookback = 50
    entry_thresh = 0.0
    vector_entry_size_pct = 0.25

    def on_start(self, ctx: Context) -> None:
        close = ctx.data.close
        mom = np.full(len(close), np.nan)
        mom[self.lookback :] = close[self.lookback :] / close[: -self.lookback] - 1
        self.entries = mom > self.entry_thresh
        self.exits = mom < 0


@pytest.mark.benchmark
def test_engine_speed_200k_bars():
    np.random.seed(1)
    steps = np.random.randn(200_000)
    px = 1000.0 + np.cumsum(steps)
    idx = pd.date_range("2024-01-01", periods=200_000, freq="min", tz="UTC")
    df = pd.DataFrame(
        {
            "open": px,
            "high": px + 1.0,
            "low": px - 1.0,
            "close": px,
            "volume": 1.0,
        },
        index=idx,
    )

    t0 = time.perf_counter()
    res = Backtest(FastMom50(), df, cash=100_000).run()
    elapsed = time.perf_counter() - t0

    assert len(res.trades) == 6175
    assert elapsed < 3.0, f"Backtest on 200k bars took {elapsed:.2f}s (expected < 3.0s)"
