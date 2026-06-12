"""HLD §7.3 parameter sweep example (M6)."""

from pathlib import Path

from stolgo import Context, Strategy, load, parameter_sweep
from stolgo.signals import sma


class SmaTrend(Strategy):
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


if __name__ == "__main__":
    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "trend_up_300bars.csv"
    df = load(fixture, symbol="TREND")

    summary = parameter_sweep(
        lambda p: SmaTrend(period=p["period"]),
        {"period": range(10, 20), "x": range(10)},
        df,
        cash=100_000,
        commission=0.0003,
    )
    best = summary.sort_values("sharpe", ascending=False).iloc[0]
    print(f"Ran {len(summary)} combinations")
    print(f"Best period={int(best['period'])} sharpe={best['sharpe']:.4f} total_return={best['total_return']:.4f}")
