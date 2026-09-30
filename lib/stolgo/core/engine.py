# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from stolgo.core.clock import SimClock
from stolgo.core.config import RunConfig
from stolgo.core.exceptions import ModeNotSupportedError
from stolgo.core.types import OrderType, Side
from stolgo.data.base import DataSource
from stolgo.data.normalize import bars_from_dataframe, normalize_ohlcv
from stolgo.oms.commission import BpsCommission
from stolgo.oms.fill_model import CloseFill, NextCloseFill, NextOpenFill
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


def _process_intents(
    ctx: Context,
    portfolio: Portfolio,
    broker: SimBroker,
    bar: Bar,
    i: int,
    equity_vals: list[float],
    config: RunConfig,
    all_events: list[Any],
    symbol: str,
) -> None:
    for intent in ctx.consume_intents():
        accepted = apply_risk(intent, portfolio, equity_vals, config, events=all_events, bar_index=i)
        if accepted is None:
            continue
        qty = resolve_qty(accepted, portfolio, bar.close, portfolio.cash)
        if qty <= 0 and accepted.size_pct is None:
            continue
        order = broker.create_order(
            symbol,
            accepted.side,
            qty,
            accepted.order_type,
            limit_price=accepted.limit_price,
            stop_price=accepted.stop_price,
            tag=accepted.tag,
            size_pct=accepted.size_pct,
            oco_group=accepted.oco_group,
            risk_per_unit=accepted.risk_per_unit,
        )
        broker.submit(order)


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

        fill_model = NextCloseFill() if self._config.fill_on in ("close", "next_close") else NextOpenFill()
        broker = SimBroker(
            fill_model,
            BpsSlippage(self._config.slippage_bps),
            BpsCommission(self._config.commission),
            fill_on=self._config.fill_on,
            allow_leverage=self._config.allow_leverage,
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
            _portfolio=portfolio,
            _equity_val=portfolio.cash,
            _cash_val=portfolio.cash,
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
        all_events: list[Any] = []

        for i, bar in SimClock(bars):
            ctx.i = i
            for fe in broker.match(bar, bar_index=i, portfolio=portfolio, events=all_events):
                portfolio.apply_fill(fe.fill)
                ctx.on_fill(fe)
                strategy.on_fill(ctx, fe)
                fill_events.append(fe)
                all_events.append(fe)

            if ctx._intents:
                _process_intents(
                    ctx,
                    portfolio,
                    broker,
                    bar,
                    i,
                    equity_vals,
                    self._config,
                    all_events,
                    symbol,
                )
                for fe in broker.match(bar, bar_index=i, portfolio=portfolio, events=all_events):
                    portfolio.apply_fill(fe.fill)
                    ctx.on_fill(fe)
                    strategy.on_fill(ctx, fe)
                    fill_events.append(fe)
                    all_events.append(fe)

            eq = portfolio.mark_to_market(bar)
            ctx._equity_val = eq
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

            _process_intents(
                ctx,
                portfolio,
                broker,
                bar,
                i,
                equity_vals,
                self._config,
                all_events,
                symbol,
            )

            if self._config.fill_on == "signal_close":
                fills = broker.match_signal_close(
                    bar,
                    bar_index=i,
                    portfolio=portfolio,
                    events=all_events,
                )
                if fills:
                    for fe in fills:
                        portfolio.apply_fill(fe.fill)
                        strategy.on_fill(ctx, fe)
                        fill_events.append(fe)
                        all_events.append(fe)
                    _process_intents(
                        ctx,
                        portfolio,
                        broker,
                        bar,
                        i,
                        equity_vals,
                        self._config,
                        all_events,
                        symbol,
                    )
                    equity_vals[-1] = portfolio.mark_to_market(bar)
                    position_qty_vals[-1] = portfolio.position.qty

        if bars and self._config.close_at_end and not portfolio.position.flat:
            last_bar = bars[-1]
            close_side = Side.SELL if portfolio.position.qty > 0 else Side.BUY
            close_qty = abs(portfolio.position.qty)
            closing_order = broker.create_order(
                symbol,
                close_side,
                close_qty,
                OrderType.MARKET,
                tag="END_OF_DATA",
            )
            fe = broker._make_fill(
                closing_order,
                last_bar,
                last_bar.close,
                len(bars) - 1,
                portfolio=portfolio,
                events=all_events,
            )
            if fe is not None:
                portfolio.apply_fill(fe.fill)
                ctx.on_fill(fe)
                strategy.on_fill(ctx, fe)
                fill_events.append(fe)
                all_events.append(fe)
                eq = portfolio.mark_to_market(last_bar)
                ctx._equity_val = eq
                equity_vals[-1] = eq
                position_qty_vals[-1] = portfolio.position.qty

        strategy.on_end(ctx)

        equity = pd.Series(equity_vals, index=pd.DatetimeIndex(equity_index, tz="UTC"))
        trades = build_trades_from_fills(fill_events)

        if bars and not self._config.close_at_end and not portfolio.position.flat:
            last_bar = bars[-1]
            last_ts = pd.Timestamp(last_bar.ts, unit="ns", tz="UTC")
            qty = abs(portfolio.position.qty)
            side_str = "LONG" if portfolio.position.qty > 0 else "SHORT"
            entry_px = portfolio.position.avg_entry_price
            exit_px = last_bar.close
            gross = (exit_px - entry_px) * qty if side_str == "LONG" else (entry_px - exit_px) * qty
            net = gross
            notional = entry_px * qty
            entry_ts = last_ts
            if fill_events:
                matching_fills = [
                    fe.fill for fe in fill_events
                    if fe.fill.side == (Side.BUY if side_str == "LONG" else Side.SELL)
                ]
                if matching_fills:
                    entry_ts = pd.Timestamp(matching_fills[-1].ts, unit="ns", tz="UTC")
            open_row = {
                "entry_ts": entry_ts,
                "exit_ts": last_ts,
                "side": side_str,
                "entry_price": entry_px,
                "exit_price": exit_px,
                "qty": qty,
                "gross_pnl": gross,
                "net_pnl": net,
                "commission": 0.0,
                "return_on_notional": net / notional if notional > 0 else 0.0,
                "r_multiple": float("nan"),
                "tag": "OPEN",
                "exit_reason": "OPEN",
            }
            if trades.empty:
                trades = pd.DataFrame([open_row])
            else:
                trades = pd.concat([trades, pd.DataFrame([open_row])], ignore_index=True)

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
            events=all_events,
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
