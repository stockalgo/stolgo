# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from stolgo.core.clock import SimClock
from stolgo.core.config import RunConfig
from stolgo.core.exceptions import ModeNotSupportedError
from stolgo.data.base import DataSource
from stolgo.data.normalize import bars_from_dataframe, normalize_ohlcv
from stolgo.oms.commission import BpsCommission
from stolgo.oms.fill_model import CloseFill, NextOpenFill
from stolgo.oms.sim_broker import SimBroker
from stolgo.oms.slippage import BpsSlippage, NoSlippage
from stolgo.portfolio.portfolio import Portfolio
from stolgo.portfolio.risk import apply_risk
from stolgo.portfolio.sizing import resolve_qty
from stolgo.core.vector_lift import apply_vector_signals, resolve_vector_masks
from stolgo.report.result import RunResult
from stolgo.report.trades import build_trades_from_fills
from stolgo.strategy.base import Strategy
from stolgo.strategy.context import BarDataView, Context


class Engine:
    def __init__(self, config: RunConfig) -> None:
        if config.mode != "backtest":
            raise ModeNotSupportedError(
                "live/paper mode not implemented until v0.3; see docs/HLD.md §12"
            )
        self._config = config

    def run(self, strategy: Strategy, data: pd.DataFrame | DataSource) -> RunResult:
        if isinstance(data, pd.DataFrame):
            df = normalize_ohlcv(data, symbol=self._config.symbol or "UNKNOWN")
        else:
            raise NotImplementedError("DataSource history slice requires symbol/interval in config")

        symbol = str(df.attrs.get("symbol", self._config.symbol or "UNKNOWN"))
        bars = bars_from_dataframe(df, symbol=symbol)
        arrays = {
            "open": df["open"].to_numpy(dtype=np.float64),
            "high": df["high"].to_numpy(dtype=np.float64),
            "low": df["low"].to_numpy(dtype=np.float64),
            "close": df["close"].to_numpy(dtype=np.float64),
            "volume": df["volume"].to_numpy(dtype=np.float64),
        }

        fill_model = CloseFill() if self._config.fill_on == "close" else NextOpenFill()
        broker = SimBroker(
            fill_model,
            BpsSlippage(self._config.slippage_bps),
            BpsCommission(self._config.commission),
            fill_on=self._config.fill_on,
        )
        portfolio = Portfolio(self._config.cash, symbol=symbol)

        n = len(bars) - 1
        bar_index = pd.DatetimeIndex(df.index, tz="UTC")
        ctx = Context(
            i=0,
            data=BarDataView(
                _open=arrays["open"],
                _high=arrays["high"],
                _low=arrays["low"],
                _close=arrays["close"],
                _volume=arrays["volume"],
                _limit=n,
                _index=bar_index,
            ),
            position=portfolio.position,
        )
        strategy.on_start(ctx)
        n_bars = len(bars)
        entries, exits, use_vector = resolve_vector_masks(
            strategy.entries,
            strategy.exits,
            ctx.entries,
            ctx.exits,
            n_bars,
        )
        vector_entry_qty = getattr(strategy, "vector_entry_qty", None)
        vector_entry_size_pct = getattr(strategy, "vector_entry_size_pct", None)

        equity_vals: list[float] = []
        equity_index: list[pd.Timestamp] = []
        position_qty_vals: list[float] = []
        fill_events: list[Any] = []

        for i, bar in SimClock(bars):
            for fe in broker.match(bar, bar_index=i):
                portfolio.apply_fill(fe.fill)
                strategy.on_fill(ctx, fe)
                fill_events.append(fe)

            eq = portfolio.mark_to_market(bar)
            equity_vals.append(eq)
            equity_index.append(pd.Timestamp(bar.ts, unit="ns", tz="UTC"))
            position_qty_vals.append(portfolio.position.qty)

            ctx.i = i
            ctx.data = BarDataView(
                _open=arrays["open"],
                _high=arrays["high"],
                _low=arrays["low"],
                _close=arrays["close"],
                _volume=arrays["volume"],
                _limit=i,
                _index=bar_index,
            )
            ctx.position = portfolio.position
            strategy.on_bar(ctx)
            if use_vector:
                apply_vector_signals(
                    ctx,
                    i,
                    entries,
                    exits,
                    entry_qty=vector_entry_qty,
                    entry_size_pct=vector_entry_size_pct,
                )

            for intent in ctx.consume_intents():
                accepted = apply_risk(intent, portfolio, equity_vals, self._config)
                if accepted is None:
                    continue
                qty = resolve_qty(accepted, portfolio, bar.close, portfolio.cash)
                if qty <= 0:
                    continue
                order = broker.create_order(symbol, accepted.side, qty, accepted.order_type)
                broker.submit(order)

        strategy.on_end(ctx)

        equity = pd.Series(equity_vals, index=pd.DatetimeIndex(equity_index, tz="UTC"))
        trades = build_trades_from_fills(fill_events)
        positions = pd.DataFrame(
            {"qty": position_qty_vals, "equity": equity_vals},
            index=equity.index,
        )
        signals = pd.DataFrame()

        return RunResult(
            params=self._config.model_dump(),
            trades=trades,
            equity=equity,
            positions=positions,
            signals=signals,
            events=fill_events,
            ohlcv=df,
        )


class Backtest:
    def __init__(self, strategy: Strategy, data: pd.DataFrame | DataSource, **kwargs: Any) -> None:
        self._strategy = strategy
        self._data = data
        self._kwargs = kwargs

    def run(self) -> RunResult:
        cfg = RunConfig(**self._kwargs)
        return Engine(cfg).run(self._strategy, self._data)
