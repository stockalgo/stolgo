"""Consolidation breakout using stolgo.pa + trade (replaces manual brackets)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stolgo.pa as pa
from stolgo import Backtest, Bandl, Context, Strategy
from stolgo import trade
from stolgo.report.exporters import export_all


@dataclass
class Cfg:
    symbol: str = "BTCUSDT"
    days: int = 7
    range_pct: float = 0.12
    risk_reward: tuple[int, int] = (1, 4)
    cash: float = 100_000.0
    commission: float = 0.001
    years: int = 3


class ConsolidationBreakoutPA(Strategy):
    def __init__(self, cfg: Cfg) -> None:
        self.cfg = cfg
        self._entry = None
        self._bracket = None

    def on_start(self, ctx: Context) -> None:
        self._entry = pa.preset.consolidation_breakout(self.cfg.days, self.cfg.range_pct)

    def on_bar(self, ctx: Context) -> None:
        if self._bracket is not None:
            hit = trade.bracket_hit(ctx, self._bracket)
            if hit:
                trade.close(ctx, tag=hit)
                self._bracket = None
            return
        if ctx.position.flat and self._entry(ctx):
            self._bracket = trade.long(
                ctx,
                rr=self.cfg.risk_reward,
                stop="candle_low",
                size_risk_pct=0.01,
                cash=self.cfg.cash,
            )


def main() -> None:
    cfg = Cfg()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.years * 365)
    df = Bandl().history(cfg.symbol, "1d", start, end)
    result = Backtest(
        ConsolidationBreakoutPA(cfg),
        df,
        symbol=cfg.symbol,
        cash=cfg.cash,
        commission=cfg.commission,
        fill_on="close",
    ).run()
    print(result.summary())
    export_all(result, Path("stolgo_btc_breakout_output"))


if __name__ == "__main__":
    main()
