"""Integration: pa rules + Backtest."""

from __future__ import annotations

import stolgo.pa as pa
from stolgo import Backtest, Context, Strategy
from stolgo.trade import bracket_hit, close, long


class PaBreakout(Strategy):
    def __init__(self) -> None:
        self._entry = None
        self._bracket = None

    def on_start(self, ctx: Context) -> None:
        self._entry = pa.consolidation(7, range_pct=0.5) & pa.crosses_above(pa.range_high(7))

    def on_bar(self, ctx: Context) -> None:
        if self._bracket is not None:
            hit = bracket_hit(ctx, self._bracket)
            if hit:
                close(ctx, tag=hit)
                self._bracket = None
            return
        if ctx.position.flat and self._entry(ctx):
            self._bracket = long(ctx, rr=(1, 2), stop="candle_low", qty=1.0, cash=100_000)


def test_pa_backtest_runs(synthetic_100bars_df) -> None:
    result = Backtest(PaBreakout(), synthetic_100bars_df, cash=100_000).run()
    assert len(result.equity) == 100
