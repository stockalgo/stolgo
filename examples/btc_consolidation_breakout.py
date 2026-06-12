"""
BTCUSDT consolidation breakout backtest (last 3 years).

Rules
-----
1. Consolidation: prior N daily bars (default 7+) trade inside a tight range.
2. Breakout: today's close clears the consolidation high.
3. Entry: buy at the breakout candle close.
4. Stop loss: low of the breakout candle.
5. Target: 1:4 reward:risk from entry.
6. Size: risk a fixed % of starting capital per trade.

Run:
    .venv/bin/python examples/btc_consolidation_breakout.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from stolgo import Backtest, Bandl, Context, Strategy
from stolgo.report.exporters import export_all


@dataclass
class ConsolidationBreakoutConfig:
    symbol: str = "BTCUSDT"
    interval: str = "1d"
    min_consolidation_days: int = 7
    max_range_pct: float = 0.12  # range width / mid-price; tune for asset
    risk_reward: float = 4.0
    risk_per_trade: float = 0.01  # 1% of capital at risk if stopped
    cash: float = 100_000.0
    commission: float = 0.001  # 10 bps per side (crypto taker-ish)
    years: int = 3


class ConsolidationBreakout(Strategy):
    """Buy when price breaks out above a multi-day consolidation range."""

    def __init__(self, cfg: ConsolidationBreakoutConfig) -> None:
        self.cfg = cfg
        self._stop_loss: float | None = None
        self._take_profit: float | None = None

    def on_bar(self, ctx: Context) -> None:
        i = ctx.i
        close = ctx.data.close
        high = ctx.data.high
        low = ctx.data.low
        n = self.cfg.min_consolidation_days

        # --- manage open trade: SL / target ---
        if not ctx.position.flat:
            bar_low = low[-1]
            bar_high = high[-1]
            if self._stop_loss is not None and bar_low <= self._stop_loss:
                ctx.close(tag="stop_loss")
                self._clear_bracket()
                return
            if self._take_profit is not None and bar_high >= self._take_profit:
                ctx.close(tag="take_profit_1_4")
                self._clear_bracket()
                return
            return

        if i < n:
            return

        # Prior consolidation window (excludes current bar)
        win_high = float(np.max(high[-(n + 1) : -1]))
        win_low = float(np.min(low[-(n + 1) : -1]))
        win_mid = float(np.mean(close[-(n + 1) : -1]))
        if win_mid <= 0:
            return

        range_pct = (win_high - win_low) / win_mid
        consolidating = range_pct <= self.cfg.max_range_pct
        breakout = close[-1] > win_high

        if not (consolidating and breakout):
            return

        entry = float(close[-1])
        stop = float(low[-1])
        risk = entry - stop
        if risk <= 0:
            return

        dollar_risk = self.cfg.cash * self.cfg.risk_per_trade
        qty = dollar_risk / risk
        if qty <= 0:
            return

        self._stop_loss = stop
        self._take_profit = entry + self.cfg.risk_reward * risk
        ctx.buy(qty=qty, tag="breakout")

    def _clear_bracket(self) -> None:
        self._stop_loss = None
        self._take_profit = None


def load_btc_daily(cfg: ConsolidationBreakoutConfig) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.years * 365)
    source = Bandl()
    df = source.history(cfg.symbol, cfg.interval, start, end)
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def print_trade_log(trades: pd.DataFrame) -> None:
    if trades.empty:
        print("\nNo completed trades in this window.")
        return
    print("\n--- Trades ---")
    cols = ["entry_ts", "exit_ts", "entry_price", "exit_price", "qty", "net_pnl", "tag"]
    show = [c for c in cols if c in trades.columns]
    print(trades[show].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))


def main() -> None:
    cfg = ConsolidationBreakoutConfig()
    print(f"Loading {cfg.symbol} {cfg.interval} ({cfg.years}y) …")
    df = load_btc_daily(cfg)
    print(f"Bars: {len(df)}  |  {df.index.min().date()} → {df.index.max().date()}")

    strategy = ConsolidationBreakout(cfg)
    result = Backtest(
        strategy,
        df,
        symbol=cfg.symbol,
        cash=cfg.cash,
        commission=cfg.commission,
        fill_on="close",  # enter at breakout candle close
    ).run()

    print("\n--- Strategy parameters ---")
    print(f"  consolidation ≥ {cfg.min_consolidation_days} days")
    print(f"  max range width     ≤ {cfg.max_range_pct:.0%} of mid-price")
    print(f"  risk / trade        {cfg.risk_per_trade:.0%} of ${cfg.cash:,.0f}")
    print(f"  reward:risk         1:{cfg.risk_reward:g}")
    print(f"  commission          {cfg.commission:.2%} per side")

    print("\n--- Performance ---")
    print(result.summary())
    final_eq = float(result.equity.iloc[-1])
    print(f"final_equity        ${final_eq:,.2f}")

    if not result.trades.empty:
        wins = result.trades[result.trades["net_pnl"] > 0]
        losses = result.trades[result.trades["net_pnl"] <= 0]
        print(f"wins / losses       {len(wins)} / {len(losses)}")
        if len(wins):
            print(f"avg win             ${wins['net_pnl'].mean():,.2f}")
        if len(losses):
            print(f"avg loss            ${losses['net_pnl'].mean():,.2f}")

    print_trade_log(result.trades)

    out_dir = Path("stolgo_btc_breakout_output")
    export_all(result, out_dir)
    print(f"\nArtifacts: {out_dir.resolve()}/")
    print(f"  tearsheet.html  equity curve + drawdown + markers")
    print(f"  trades.csv      trade log")
    print(f"  summary.json    metrics")


if __name__ == "__main__":
    main()
