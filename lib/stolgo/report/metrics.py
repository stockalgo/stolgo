# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Tearsheet metrics (HLD §8.2)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252.0


def compute_metrics(
    equity: pd.Series,
    trades: pd.DataFrame,
    *,
    position_qty: pd.Series | None = None,
) -> dict[str, float]:
    """Compute performance statistics from equity curve and trade log."""
    if equity.empty:
        return _empty_metrics()

    start = float(equity.iloc[0])
    end = float(equity.iloc[-1])
    total_return = (end / start - 1.0) if start else 0.0

    n_bars = len(equity)
    n_years = n_bars / TRADING_DAYS_PER_YEAR if n_bars else 0.0
    cagr = ((end / start) ** (1.0 / n_years) - 1.0) if start > 0 and n_years > 0 else 0.0

    rets = equity.pct_change().dropna()
    vol = float(rets.std() * math.sqrt(TRADING_DAYS_PER_YEAR)) if len(rets) > 1 else 0.0
    sharpe = (
        float(rets.mean() / rets.std() * math.sqrt(TRADING_DAYS_PER_YEAR))
        if len(rets) > 1 and rets.std() > 0
        else 0.0
    )

    downside = rets[rets < 0]
    downside_std = float(downside.std() * math.sqrt(TRADING_DAYS_PER_YEAR)) if len(downside) > 1 else 0.0
    sortino = (
        float(rets.mean() / downside_std * math.sqrt(TRADING_DAYS_PER_YEAR))
        if downside_std > 0
        else 0.0
    )

    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan)
    max_dd = float(dd.min()) if len(dd) else 0.0
    max_dd_duration = _max_drawdown_duration_bars(dd)

    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    mar = calmar

    ulcer = float(np.sqrt((dd.fillna(0) ** 2).mean())) if len(dd) else 0.0

    exposure_pct = 0.0
    if position_qty is not None and len(position_qty) == len(equity):
        exposure_pct = float((position_qty.abs() > 1e-12).mean())

    turnover = 0.0
    if not trades.empty and "qty" in trades.columns:
        traded_notional = float((trades["qty"] * (trades["entry_price"] + trades["exit_price"])).sum())
        avg_equity = float(equity.mean()) if len(equity) else 0.0
        turnover = traded_notional / avg_equity if avg_equity > 0 else 0.0

    num_trades = float(len(trades))
    hit_rate = 0.0
    expectancy = 0.0
    profit_factor = 0.0
    avg_win = 0.0
    avg_loss = 0.0
    payoff = 0.0

    if num_trades > 0 and "net_pnl" in trades.columns:
        pnls = trades["net_pnl"]
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        hit_rate = float((pnls > 0).mean())
        expectancy = float(pnls.mean())
        gross_profit = float(wins.sum()) if len(wins) else 0.0
        gross_loss = float(abs(losses.sum())) if len(losses) else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        avg_win = float(wins.mean()) if len(wins) else 0.0
        avg_loss = float(losses.mean()) if len(losses) else 0.0
        payoff = avg_win / abs(avg_loss) if avg_loss < 0 else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "mar": mar,
        "max_drawdown": max_dd,
        "max_drawdown_duration": float(max_dd_duration),
        "volatility": vol,
        "ulcer_index": ulcer,
        "hit_rate": hit_rate,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "payoff": payoff,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "num_trades": num_trades,
        "exposure_pct": exposure_pct,
        "turnover": turnover,
        "final_equity": end,
    }


def _max_drawdown_duration_bars(dd: pd.Series) -> int:
    in_dd = False
    current = 0
    longest = 0
    for v in dd.fillna(0):
        if v < 0:
            in_dd = True
            current += 1
            longest = max(longest, current)
        else:
            in_dd = False
            current = 0
    return longest


def _empty_metrics() -> dict[str, float]:
    keys = [
        "total_return",
        "cagr",
        "sharpe",
        "sortino",
        "calmar",
        "mar",
        "max_drawdown",
        "max_drawdown_duration",
        "volatility",
        "ulcer_index",
        "hit_rate",
        "expectancy",
        "profit_factor",
        "payoff",
        "avg_win",
        "avg_loss",
        "num_trades",
        "exposure_pct",
        "turnover",
        "final_equity",
    ]
    return dict.fromkeys(keys, 0.0)
