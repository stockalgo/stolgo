"""Parameter sweep tests (v0.2 / M6)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from stolgo import Backtest, Strategy
from stolgo.core.sweep import parameter_sweep
from stolgo.signals import sma
from stolgo.strategy.context import Context


class SmaCrossSweep(Strategy):
    def __init__(self, period: int) -> None:
        self.period = period
        self._sma = None

    def on_start(self, ctx: Context) -> None:
        self._sma = sma(ctx.data.close, self.period)

    def on_bar(self, ctx: Context) -> None:
        if ctx.i < self.period or self._sma is None:
            return
        if ctx.position.flat and ctx.data.close[-1] > self._sma[ctx.i]:
            ctx.buy(size_pct=0.5)
        elif not ctx.position.flat and ctx.data.close[-1] < self._sma[ctx.i]:
            ctx.close()


@pytest.fixture
def trend_up_df() -> pd.DataFrame:
    path = Path(__file__).parent / "fixtures" / "trend_up_300bars.csv"
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.set_index("timestamp")


def test_parameter_sweep_100_combos(trend_up_df: pd.DataFrame) -> None:
    def factory(params: dict) -> Strategy:
        return SmaCrossSweep(period=params["period"])

    summary = parameter_sweep(
        factory,
        {"period": range(10, 20), "x": range(10)},
        trend_up_df,
        cash=100_000,
    )
    assert len(summary) == 100
    assert "total_return" in summary.columns
    assert summary["total_return"].notna().all()


@pytest.mark.benchmark
def test_parameter_sweep_benchmark_optional(trend_up_df: pd.DataFrame) -> None:
    pytest.importorskip("numba")
    import time

    grid = {"period": range(5, 15)}
    t0 = time.perf_counter()
    parameter_sweep(
        lambda p: SmaCrossSweep(period=p["period"]),
        {**{k: v for k, v in [("period", range(5, 15))]}, "x": range(10)},
        trend_up_df,
        fast=True,
    )
    elapsed = time.perf_counter() - t0
    assert elapsed < 30.0
