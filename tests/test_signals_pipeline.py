"""Tests for cross-sectional Pipeline (v0.2)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stolgo.signals.pipeline import Pipeline, momentum


def _make_symbol_frame(seed: int, n: int = 60, drift: float = 0.001) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    close = 100 * np.cumprod(1 + drift + rng.normal(0, 0.01, n))
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1000.0,
        }
    )


def test_pipeline_weekly_rebalance_top2_deterministic():
    frames = {
        "AAA": _make_symbol_frame(1, drift=0.002),
        "BBB": _make_symbol_frame(2, drift=0.0005),
        "CCC": _make_symbol_frame(3, drift=-0.001),
    }
    pipe = (
        Pipeline(["AAA", "BBB", "CCC"])
        .add(momentum(5), name="mom")
        .rank("mom", top=2)
        .rebalance("W-FRI")
    )
    weights = pipe.run_frames(frames)
    assert list(weights.columns) == ["AAA", "BBB", "CCC"]
    assert len(weights) == 60
    active = weights.sum(axis=1)
    assert (active[active > 0] - 1.0).abs().max() < 1e-9
    # AAA has strongest drift — should appear in most rebalance windows
    assert weights["AAA"].sum() > 0
