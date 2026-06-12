"""Smoke tests for pa presets."""

from __future__ import annotations

import stolgo.pa as pa


def test_presets_return_rules(synthetic_100bars_df) -> None:
    assert pa.preset.scalp_green_fade().series(synthetic_100bars_df) is not None
    long_e, short_e = pa.preset.breakout_intraday(days=7)
    assert long_e.series(synthetic_100bars_df) is not None
    assert short_e.series(synthetic_100bars_df) is not None
    assert pa.preset.parabolic_short().series(synthetic_100bars_df) is not None
