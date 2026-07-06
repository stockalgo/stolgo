"""Simple BTCUSDT CoinDCX backtest exported for the Stolgo UI.

Run:
    PYTHONPATH=lib .venv/bin/python examples/btc_usdt_coindcx_backtest.py --output runs/coindcx-btcusdt-sma
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from stolgo import Backtest, Bandl, Context, Strategy
from stolgo.report.exporters import export_all
from stolgo.signals import sma


class BtcUsdtSmaTrend(Strategy):
    fast_period = 12
    slow_period = 36
    vector_entry_size_pct = 0.35

    def on_start(self, ctx: Context) -> None:
        close = ctx.data.close
        self._fast = sma(close, self.fast_period)
        self._slow = sma(close, self.slow_period)

    def on_bar(self, ctx: Context) -> None:
        if ctx.i < self.slow_period:
            return

        fast = self._fast[ctx.i]
        slow = self._slow[ctx.i]
        close = ctx.data.close[-1]

        if ctx.position.flat and fast > slow and close > slow:
            ctx.buy(size_pct=self.vector_entry_size_pct, tag="sma_trend_entry")
        elif not ctx.position.flat and (fast < slow or close < slow):
            ctx.close(tag="sma_trend_exit")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a simple BTCUSDT CoinDCX SMA backtest.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--output", type=Path, default=Path("stolgo_coindcx_btcusdt_output"))
    args = parser.parse_args(argv)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    print(f"Loading {args.symbol} {args.interval} from CoinDCX: {start.date()} -> {end.date()}")
    df = Bandl(provider="crypto", source="coindcx").history(
        args.symbol,
        args.interval,
        start,
        end,
    )
    print(f"Bars: {len(df):,}  {df.index.min()} -> {df.index.max()}")

    result = Backtest(
        BtcUsdtSmaTrend(),
        df,
        symbol=args.symbol,
        interval=args.interval,
        cash=100_000,
        commission=0.001,
        fill_on="close",
    ).run()

    print(result.summary())
    export_all(result, args.output, strategy_name=f"{args.symbol} CoinDCX SMA")
    print(f"Exported to {args.output.resolve()}")


if __name__ == "__main__":
    main()
