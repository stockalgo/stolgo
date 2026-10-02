from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from stolgo.core.clock import SimClock
from stolgo.core.config import RunConfig
from stolgo.core.exceptions import ModeNotSupportedError
from stolgo.core.types import Bar, OrderType, Side
from stolgo.data.base import DataSource
from stolgo.data.normalize import bars_from_dataframe, normalize_ohlcv
from stolgo.oms.commission import BpsCommission
from stolgo.oms.fill_model import NextCloseFill, NextOpenFill
from stolgo.oms.sim_broker import SimBroker
from stolgo.oms.slippage import BpsSlippage
from stolgo.portfolio.portfolio import Portfolio
from stolgo.portfolio.risk import apply_risk
from stolgo.portfolio.sizing import resolve_qty
from stolgo.core.lookahead import probe
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
    peak_equity: float | None = None,
    current_equity: float | None = None,
    active_from: int = 0,
) -> None:
    for intent in ctx.consume_intents():
        accepted = apply_risk(
            intent,
            portfolio,
            equity_vals,
            config,
            events=all_events,
            bar_index=i,
            peak_equity=peak_equity,
            current_equity=current_equity,
        )
        if accepted is None:
            continue
        qty = resolve_qty(accepted, portfolio, bar.close, portfolio.cash)
        if qty <= 0 and accepted.size_pct is None and accepted.size_risk_pct is None:
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
            reduce_only=accepted.reduce_only,
            active_from=active_from,
            size_risk_pct=accepted.size_risk_pct,
            risk_stop=accepted.risk_stop,
            client_order_id=accepted.client_order_id,
        )
        broker.submit(order)


def _clean_unresolved_brackets(ctx: Context, broker: SimBroker) -> None:
    if not ctx._active_brackets:
        return
    open_cids = {o.client_order_id for o in broker.open_orders() if o.client_order_id is not None}
    pending_intent_cids = {intent.client_order_id for intent in ctx._intents if intent.client_order_id is not None}
    valid_cids = open_cids | pending_intent_cids
    ctx._active_brackets = [
        b for b in ctx._active_brackets
        if (b.entry_cid in valid_cids if b.entry_cid is not None else not b.filled)
    ]


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

        if self._config.lookahead_check:
            probe(strategy, df)

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
            qty_step=self._config.qty_step,
        )
        portfolio = Portfolio(self._config.cash, symbol=symbol)

        n = len(bars) - 1
        bar_index = pd.DatetimeIndex(df.index, tz="UTC")
        data_view = BarDataView(
            _open=arrays["open"],
            _high=arrays["high"],
            _low=arrays["low"],
            _close=arrays["close"],
            _volume=arrays["volume"],
            _limit=n,
            _index=bar_index,
        )
        ctx = Context(
            i=0,
            data=data_view,
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
        equity_ts: list[int] = []
        position_qty_vals: list[float] = []
        fill_events: list[Any] = []
        all_events: list[Any] = []

        def _apply_fill(fe: Any) -> None:
            portfolio.apply_fill(fe.fill)
            if portfolio.position.flat:
                broker.cancel_reduce_only(fe.fill.symbol)
            ctx.on_fill(fe)
            strategy.on_fill(ctx, fe)
            fill_events.append(fe)
            all_events.append(fe)

        running_peak: float | None = None
        for i, bar in SimClock(bars):
            ctx.i = i
            broker.match(bar, bar_index=i, portfolio=portfolio, events=all_events, on_fill=_apply_fill)
            _clean_unresolved_brackets(ctx, broker)

            if ctx._intents:
                active_from = i + 1 if self._config.fill_on in ("close", "next_close") else i
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
                    peak_equity=running_peak if len(equity_vals) >= 2 else None,
                    current_equity=equity_vals[-1] if len(equity_vals) >= 2 else None,
                    active_from=active_from,
                )
                broker.match(bar, bar_index=i, portfolio=portfolio, events=all_events, on_fill=_apply_fill)
                _clean_unresolved_brackets(ctx, broker)

            eq = portfolio.mark_to_market(bar)
            ctx._equity_val = eq
            equity_vals.append(eq)
            equity_ts.append(bar.ts)
            position_qty_vals.append(portfolio.position.qty)
            running_peak = eq if running_peak is None else max(running_peak, eq)

            ctx.i = i
            data_view._limit = i
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
                peak_equity=running_peak if len(equity_vals) >= 2 else None,
                current_equity=equity_vals[-1] if len(equity_vals) >= 2 else None,
                active_from=i + 1,
            )
            _clean_unresolved_brackets(ctx, broker)

            if self._config.fill_on == "signal_close":
                fills = broker.match_signal_close(
                    bar,
                    bar_index=i,
                    portfolio=portfolio,
                    events=all_events,
                    on_fill=_apply_fill,
                )
                if fills:
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
                        peak_equity=running_peak if len(equity_vals) >= 2 else None,
                        current_equity=equity_vals[-1] if len(equity_vals) >= 2 else None,
                        active_from=i + 1,
                    )
                    eq_close = portfolio.mark_to_market(bar)
                    equity_vals[-1] = eq_close
                    position_qty_vals[-1] = portfolio.position.qty
                    running_peak = eq_close if running_peak is None else max(running_peak, eq_close)
                _clean_unresolved_brackets(ctx, broker)

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
                active_from=len(bars),
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
                _apply_fill(fe)
                eq = portfolio.mark_to_market(last_bar)
                ctx._equity_val = eq
                equity_vals[-1] = eq
                position_qty_vals[-1] = portfolio.position.qty

        # Nothing can fill after the last bar: drop unfilled brackets and any
        # orders still pending or resting so on_end sees a settled state.
        broker.cancel_all()
        ctx._active_brackets = [b for b in ctx._active_brackets if b.filled]
        strategy.on_end(ctx)

        equity = pd.Series(equity_vals, index=pd.to_datetime(equity_ts, unit="ns", utc=True))
        mark = None
        if bars and not self._config.close_at_end and not portfolio.position.flat:
            last_bar = bars[-1]
            mark = (last_bar.ts, last_bar.close)
        trades = build_trades_from_fills(fill_events, mark=mark)

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
