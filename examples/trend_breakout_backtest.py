"""HLD §6.1 trend breakout example (M2)."""

from pathlib import Path

from stolgo import Backtest, Context, Strategy, load
from stolgo.signals import atr, sma


class TrendBreakout(Strategy):
    def on_start(self, ctx: Context) -> None:
        period = min(50, len(ctx.data.close))
        self._sma = sma(ctx.data.close, period)
        self._atr = atr(ctx.data.high, ctx.data.low, ctx.data.close, 14)

    def on_bar(self, ctx: Context) -> None:
        if ctx.i < 14:
            return
        if ctx.position.flat and ctx.data.close[-1] > self._sma[ctx.i]:
            ctx.buy(size_pct=0.1, tag="entry")
        elif not ctx.position.flat and ctx.data.close[-1] < self._sma[ctx.i]:
            ctx.close(tag="exit")


if __name__ == "__main__":
    df = load("tests/fixtures/synthetic_100bars.csv", symbol="SYN")
    result = Backtest(TrendBreakout(), df, cash=100_000, commission=0.0003).run()
    print(result.summary())
    out = Path("stolgo_tearsheet.html")
    result.report.to_html(out)
    print(f"Tearsheet: {out.resolve()}")
