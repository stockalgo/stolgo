"""Scalp: green streak then fade short — pa.preset.scalp_green_fade."""

from stolgo import Backtest, Context, Strategy, load
from stolgo import trade
import stolgo.pa as pa


class ScalpFade(Strategy):
    def __init__(self) -> None:
        self._trigger = pa.preset.scalp_green_fade(min_green=3)
        self._bracket = None

    def on_bar(self, ctx: Context) -> None:
        if self._bracket:
            hit = trade.bracket_hit(ctx, self._bracket)
            if hit:
                trade.close(ctx, tag=hit)
                self._bracket = None
            return
        if ctx.position.flat and self._trigger(ctx):
            self._bracket = trade.short(ctx, rr=(1, 2), stop="candle_high", qty=1.0)


if __name__ == "__main__":
    df = load("tests/fixtures/synthetic_100bars.csv", symbol="SYN")
    print(Backtest(ScalpFade(), df, fill_on="close").run().summary())
