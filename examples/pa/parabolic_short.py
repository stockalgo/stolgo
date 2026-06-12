"""Parabolic run + first red day short bias."""

from stolgo import Backtest, Context, Strategy, load
from stolgo import trade
import stolgo.pa as pa


class ParabolicShort(Strategy):
    def __init__(self) -> None:
        self._entry = pa.preset.parabolic_short(min_pct=0.5, within_days=10)
        self._bracket = None

    def on_bar(self, ctx: Context) -> None:
        if self._bracket:
            hit = trade.bracket_hit(ctx, self._bracket)
            if hit:
                trade.close(ctx, tag=hit)
                self._bracket = None
            return
        if ctx.position.flat and self._entry(ctx):
            self._bracket = trade.short(ctx, rr=(1, 4), stop="candle_high", qty=1.0)


if __name__ == "__main__":
    df = load("tests/fixtures/trend_up_300bars.csv", symbol="TREND")
    print(Backtest(ParabolicShort(), df, fill_on="close").run().summary())
