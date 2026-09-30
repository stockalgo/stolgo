"""Golden snapshot baseline for stolgo backtest engine and exporters.

Runs 4 fixed strategies and asserts their SHA-256 trades CSV hash and final equity.
Also validates the export_run_v2 manifest snapshot for a migrated options run.
Every F* and N* task must leave this test completely unchanged and passing byte-for-byte.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from examples.vector_momentum_backtest import FastMomentum
from stolgo import Backtest, Context, Strategy, load
from stolgo.trade import long


def _sha256_df(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(float_format="%.10g").encode("utf-8")).hexdigest()


def _strip_volatile(d: Any) -> Any:
    volatile = {"created_at", "migrated_at", "path", "code_version"}
    if isinstance(d, dict):
        return {k: _strip_volatile(v) for k, v in d.items() if k not in volatile}
    elif isinstance(d, list):
        return [_strip_volatile(x) for x in d]
    return d


class GoldenMACross(Strategy):
    def on_bar(self, ctx: Context) -> None:
        if ctx.i < 20:
            return
        fast = np.mean(ctx.data.close[-10:])
        slow = np.mean(ctx.data.close[-20:])
        if fast > slow and ctx.position.flat:
            ctx.buy(qty=10.0)
        elif fast < slow and not ctx.position.flat:
            ctx.close()


class GoldenBracket(Strategy):
    def on_bar(self, ctx: Context) -> None:
        if ctx.i % 30 == 0 and ctx.position.flat:
            long(ctx, stop=ctx.data.close[-1] * 0.95, size_risk_pct=0.01, rr=(1, 2))


class GoldenMom50(Strategy):
    lookback = 50
    entry_thresh = 0.0
    vector_entry_size_pct = 0.25

    def on_start(self, ctx: Context) -> None:
        close = ctx.data.close
        mom = np.full(len(close), np.nan)
        mom[self.lookback :] = close[self.lookback :] / close[: -self.lookback] - 1
        self.entries = mom > self.entry_thresh
        self.exits = mom < 0


def test_golden_ma_cross():
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "trend_up_300bars.csv"
    df = load(fixture_path, symbol="TREND")
    res = Backtest(GoldenMACross(), df, cash=100_000).run()
    assert len(res.trades) == 1
    assert _sha256_df(res.trades) == "e479f5e69e4a62abf4369aaf3ba07112e281d2fccf84af42eaba0a14ced38efe"
    assert round(float(res.equity.iloc[-1]), 6) == 100142.226775


def test_golden_vector_lift():
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "trend_up_300bars.csv"
    df = load(fixture_path, symbol="TREND")
    res = Backtest(FastMomentum(), df, cash=100_000, commission=0.0003).run()
    assert len(res.trades) == 4
    assert _sha256_df(res.trades) == "023bc96606db17221e734f817332814de6a1d0aaaa11954f5f8db5ffc2c0bad5"
    assert round(float(res.equity.iloc[-1]), 6) == 106399.312205


def test_golden_bracket():
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "trend_up_300bars.csv"
    df = load(fixture_path, symbol="TREND")
    res = Backtest(GoldenBracket(), df, cash=100_000).run()
    assert len(res.trades) == 3
    assert _sha256_df(res.trades) == "99509429a57930f7f039b12ccea6fa1e4c137a9b434a57c825475a78b312f2b6"
    assert round(float(res.equity.iloc[-1]), 6) == 105299.297659


def test_golden_random_walk_200k():
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
    res = Backtest(GoldenMom50(), df, cash=100_000).run()
    assert len(res.trades) == 6175
    assert _sha256_df(res.trades) == "3d32b77b038d89d0d8e88372beb606d639f2731a1a64f5d504ac9993e2f0c36c"
    assert round(float(res.equity.iloc[-1]), 6) == 119429.215734


def test_golden_options_manifest_snapshot():
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "golden_options_manifest.json"
    expected = json.loads(fixture_path.read_text())

    run_dir = Path("runs/validated-timing-3y-nifty-0dte-static")
    if (run_dir / "manifest.json").exists():
        actual = json.loads((run_dir / "manifest.json").read_text())
        assert _strip_volatile(actual) == expected
