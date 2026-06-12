"""Failed breakout at daily S/R — preset.failed_break_intraday."""

from stolgo import Backtest, Context, Strategy, load
from stolgo import trade
import stolgo.pa as pa


class FailedBreak(Strategy):
    def __init__(self) -> None:
        self._long, self._short = pa.preset.failed_break_intraday(days=7)
        self._bracket = None

    def on_bar(self, ctx: Context) -> None:
        if self._bracket:
            hit = trade.bracket_hit(ctx, self._bracket)
            if hit:
                trade.close(ctx, tag=hit)
                self._bracket = None
            return
        if ctx.position.flat and self._short(ctx):
            self._bracket = trade.short(ctx, rr=(1, 2), stop="candle_high", qty=1.0)
        elif ctx.position.flat and self._long(ctx):
            self._bracket = trade.long(ctx, rr=(1, 2), stop="candle_low", qty=1.0)


if __name__ == "__main__":
    df = load("tests/fixtures/synthetic_100bars.csv", symbol="SYN")
    print(Backtest(FailedBreak(), df, fill_on="close").run().summary())
