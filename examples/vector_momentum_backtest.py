"""HLD §6.2 vector-style momentum backtest (M5)."""

from pathlib import Path

import numpy as np

from stolgo import Backtest, Context, Strategy, load


class FastMomentum(Strategy):
    lookback = 20
    entry_thresh = 0.02
    vector_entry_size_pct = 0.25

    def on_start(self, ctx: Context) -> None:
        close = ctx.data.close
        mom = np.full(len(close), np.nan)
        mom[self.lookback :] = close[self.lookback :] / close[: -self.lookback] - 1
        self.entries = mom > self.entry_thresh
        self.exits = mom < 0


if __name__ == "__main__":
    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "trend_up_300bars.csv"
    df = load(fixture, symbol="TREND")
    result = Backtest(FastMomentum(), df, cash=100_000, commission=0.0003).run()
    print(result.summary())
    out = Path("vector_momentum_tearsheet.html")
    result.report.to_html(out)
    print(f"Tearsheet: {out.resolve()}")
