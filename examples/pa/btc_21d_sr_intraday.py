"""BTC intraday breakout vs 21-day daily support/resistance (3-year backtest).

Long: intraday close crosses above 21-day daily resistance.
Short: intraday close crosses below 21-day daily support (optional).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import stolgo.pa as pa
from stolgo import Backtest, Bandl, Context, Strategy
from stolgo import trade
from stolgo.report.exporters import export_all


@dataclass
class Cfg:
    symbol: str = "BTCUSDT"
    sr_lookback: int = 21
    interval: str = "1h"
    years: int = 3
    risk_reward: tuple[int, int] = (1, 2)
    cash: float = 100_000.0
    commission: float = 0.001
    qty: float = 0.05
    allow_short: bool = True
    # Prefer long entries when both fire same bar (resistance break vs support break)
    prefer_long: bool = True


class Btc21dSrIntraday(Strategy):
    def __init__(self, cfg: Cfg, ohlcv: pd.DataFrame) -> None:
        self.cfg = cfg
        daily = "1d"
        lb = cfg.sr_lookback
        r = pa.resistance(lb, tf=daily)
        s = pa.support(lb, tf=daily)
        self._long_sig = pa.crosses_above(r).series(ohlcv).to_numpy(dtype=bool)
        self._short_sig = pa.crosses_below(s).series(ohlcv).to_numpy(dtype=bool)
        self._bracket: trade.Bracket | None = None

    def on_bar(self, ctx: Context) -> None:
        # Fills apply at the next bar open — only manage bracket once positioned.
        if not ctx.position.flat:
            if self._bracket is not None:
                hit = trade.bracket_hit(ctx, self._bracket)
                if hit:
                    trade.close(ctx, tag=hit)
                    self._bracket = None
            return

        if self._bracket is not None:
            self._bracket = None  # pending entry never filled or already flat

        i = ctx.i
        long_bar = bool(self._long_sig[i])
        short_bar = self.cfg.allow_short and bool(self._short_sig[i])
        if long_bar and (not short_bar or self.cfg.prefer_long):
            self._bracket = trade.long(
                ctx,
                rr=self.cfg.risk_reward,
                stop="candle_low",
                qty=self.cfg.qty,
                cash=self.cfg.cash,
            )
        elif short_bar:
            self._bracket = trade.short(
                ctx,
                rr=self.cfg.risk_reward,
                stop="candle_high",
                qty=self.cfg.qty,
                cash=self.cfg.cash,
            )


def main() -> None:
    cfg = Cfg()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.years * 365)

    print(f"Loading {cfg.symbol} {cfg.interval} from {start.date()} to {end.date()}...")
    df = Bandl().history(cfg.symbol, cfg.interval, start, end)
    print(f"Bars: {len(df):,}  ({df.index[0]} → {df.index[-1]})")

    long_n = int(pa.crosses_above(pa.resistance(cfg.sr_lookback, tf="1d")).series(df).sum())
    short_n = int(pa.crosses_below(pa.support(cfg.sr_lookback, tf="1d")).series(df).sum())
    print(f"Signal bars (3y): long crosses={long_n}, short crosses={short_n}")

    result = Backtest(
        Btc21dSrIntraday(cfg, df),
        df,
        symbol=cfg.symbol,
        cash=cfg.cash,
        commission=cfg.commission,
        fill_on="close",
    ).run()

    print("\n--- Summary ---")
    print(result.summary())
    if len(result.trades):
        print(result.trades[["entry_ts", "exit_ts", "net_pnl", "tag"]].tail(8).to_string(index=False))

    out = Path("stolgo_btc_21d_sr_intraday_output")
    export_all(result, out)
    print(f"\nExported to {out.resolve()}")


if __name__ == "__main__":
    main()
