"""Performance metrics for R-multiple, trade-log based strategies (HLD §8.2 ext).

Unlike :func:`stolgo.report.metrics.compute_metrics` (which expects a
per-bar equity curve from the single-symbol event engine), this module
summarizes a flat trade log — the natural output of a multi-symbol screener
such as :mod:`stolgo.strategy.builtins.parabolic_short` — using each trade's
realized R-multiple. Overlapping trades are supported: the equity curve used
for drawdown is built by sorting trades on ``exit_date`` and cumulatively
summing R (i.e. assumes a fixed, equal risk-per-trade sizing model, which is
the standard convention for R-multiple system evaluation).
"""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ("r_multiple", "outcome", "holding_period_days", "exit_date")


def compute_rmultiple_metrics(
    trades: pd.DataFrame,
    *,
    regime: pd.Series | None = None,
) -> dict:
    """Summarize a trade log of realized R-multiples.

    Parameters
    ----------
    trades:
        DataFrame as produced by
        :func:`stolgo.strategy.builtins.parabolic_short.trades_to_dataframe`.
        Only closed trades (``outcome != "open"``) count toward win rate,
        expectancy, profit factor, and R-based drawdown; open trades are
        reported separately.
    regime:
        Optional Series aligned to ``trades.index`` (or matching on
        ``exit_date``) labeling each trade's market regime (e.g. "bull",
        "bear", "sideways"). When provided, metrics are also broken out per
        regime under the ``"by_regime"`` key.

    Returns
    -------
    dict
        Flat metrics dict plus ``"by_regime"`` (only present when ``regime``
        is supplied) and ``"equity_curve_r"`` (cumulative R by exit date, for
        charting).
    """
    if trades.empty:
        return _empty_metrics()

    missing = [c for c in REQUIRED_COLUMNS if c not in trades.columns]
    if missing:
        raise ValueError(f"trades missing required columns: {missing}")

    closed = trades[trades["outcome"] != "open"].copy()
    open_trades = trades[trades["outcome"] == "open"]

    metrics = _metrics_for_subset(closed)
    metrics["total_trades"] = int(len(trades))
    metrics["open_trades"] = int(len(open_trades))
    metrics["best_trade_r"] = float(closed["r_multiple"].max()) if len(closed) else 0.0
    metrics["worst_trade_r"] = float(closed["r_multiple"].min()) if len(closed) else 0.0
    if len(closed):
        best_row = closed.loc[closed["r_multiple"].idxmax()]
        worst_row = closed.loc[closed["r_multiple"].idxmin()]
        metrics["best_trade_symbol"] = str(best_row.get("symbol", ""))
        metrics["worst_trade_symbol"] = str(worst_row.get("symbol", ""))
    else:
        metrics["best_trade_symbol"] = ""
        metrics["worst_trade_symbol"] = ""

    equity_curve = _r_equity_curve(closed)
    metrics["equity_curve_r"] = equity_curve
    metrics["max_drawdown_r"] = _max_drawdown(equity_curve)

    if regime is not None and len(closed):
        by_regime: dict[str, dict] = {}
        aligned = closed.copy()
        if len(regime) == len(trades):
            aligned["_regime"] = regime.reindex(trades.index).loc[aligned.index]
        else:
            aligned["_regime"] = aligned["exit_date"].map(regime)
        for label, sub in aligned.groupby("_regime"):
            sub_metrics = _metrics_for_subset(sub)
            sub_metrics["total_trades"] = int(len(sub))
            by_regime[str(label)] = sub_metrics
        metrics["by_regime"] = by_regime

    return metrics


def _metrics_for_subset(closed: pd.DataFrame) -> dict:
    n = len(closed)
    if n == 0:
        m = _empty_metrics()
        m.pop("equity_curve_r", None)
        return m

    r = closed["r_multiple"]
    wins = r[r > 0]
    losses = r[r < 0]

    win_rate = float((r > 0).mean())
    avg_r = float(r.mean())
    gross_profit_r = float(wins.sum()) if len(wins) else 0.0
    gross_loss_r = float(abs(losses.sum())) if len(losses) else 0.0
    profit_factor = gross_profit_r / gross_loss_r if gross_loss_r > 0 else float("inf") if gross_profit_r > 0 else 0.0
    avg_win_r = float(wins.mean()) if len(wins) else 0.0
    avg_loss_r = float(losses.mean()) if len(losses) else 0.0
    # expectancy per trade, in R, standard formula (equivalent to avg_r but
    # kept explicit for the win-rate / avg-win / avg-loss breakdown)
    expectancy_r = win_rate * avg_win_r + (1 - win_rate) * avg_loss_r
    avg_holding_period = float(closed["holding_period_days"].mean())

    return {
        "closed_trades": int(n),
        "win_rate": win_rate,
        "avg_r_multiple": avg_r,
        "expectancy_r": expectancy_r,
        "profit_factor": profit_factor,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "avg_holding_period_days": avg_holding_period,
    }


def _r_equity_curve(closed: pd.DataFrame) -> pd.Series:
    if closed.empty:
        return pd.Series(dtype=float)
    ordered = closed.sort_values("exit_date")
    return pd.Series(
        ordered["r_multiple"].cumsum().to_numpy(),
        index=pd.Index(ordered["exit_date"].to_numpy(), name="exit_date"),
        name="cumulative_r",
    )


def _max_drawdown(equity_curve_r: pd.Series) -> float:
    if equity_curve_r.empty:
        return 0.0
    # R-equity can start at/near zero and dip negative before any wins land,
    # so drawdown here is measured as the largest peak-to-trough *drop* in R
    # (not a percentage), which is well-defined even when equity crosses zero.
    running_peak = equity_curve_r.cummax()
    drawdown = equity_curve_r - running_peak
    return float(drawdown.min())


def _empty_metrics() -> dict:
    return {
        "total_trades": 0,
        "open_trades": 0,
        "closed_trades": 0,
        "win_rate": 0.0,
        "avg_r_multiple": 0.0,
        "expectancy_r": 0.0,
        "profit_factor": 0.0,
        "avg_win_r": 0.0,
        "avg_loss_r": 0.0,
        "avg_holding_period_days": 0.0,
        "best_trade_r": 0.0,
        "worst_trade_r": 0.0,
        "best_trade_symbol": "",
        "worst_trade_symbol": "",
        "max_drawdown_r": 0.0,
        "equity_curve_r": pd.Series(dtype=float),
    }
