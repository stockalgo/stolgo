from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from stolgo.core.exceptions import AccountingError
from stolgo.report.calendar_metrics import calendar_metrics

IST = "Asia/Kolkata"


def _clean_val(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (float, np.floating)):
        if np.isnan(v) or np.isinf(v):
            return None
        return float(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    return v


def compute_run_metrics(
    trades: pd.DataFrame,
    capital: float,
    daily: pd.DataFrame,
    *,
    intraday_equity: pd.Series | None = None,
    equity_basis: str = "mark_to_market",
    tz: str = "UTC",
    session_close: str = "24:00",
) -> dict[str, Any]:
    """Return the manifest v2 `metrics` dict (§3.1), all keys present, NaN→None applied last."""
    if daily.empty or capital <= 0:
        raise ValueError("Non-empty daily and positive capital are required to compute run metrics")

    # Localize daily_pnl to session_close in tz then convert to UTC
    if session_close == "24:00":
        close_offset = pd.Timedelta(hours=23, minutes=59, seconds=59)
    else:
        h, m = map(int, session_close.split(":"))
        close_offset = pd.Timedelta(hours=h, minutes=m)

    daily_pnl = pd.Series(
        daily["pnl"].values,
        index=pd.DatetimeIndex(daily["session"]).tz_localize(tz) + close_offset,
    ).tz_convert("UTC")

    # Prepare trades_for_legacy and call calendar_metrics
    trades_for_legacy = trades.copy()
    if "fees" in trades_for_legacy.columns and "commission" not in trades_for_legacy.columns:
        trades_for_legacy = trades_for_legacy.rename(columns={"fees": "commission"})

    if "premium_entry" in trades_for_legacy.columns:
        trades_for_legacy["entry_price"] = trades_for_legacy["premium_entry"]
        if "premium_exit" in trades_for_legacy.columns:
            trades_for_legacy["exit_price"] = trades_for_legacy["premium_exit"]
    else:
        trades_for_legacy = trades_for_legacy.drop(
            columns=["entry_price", "exit_price"], errors="ignore"
        )

    m, _ = calendar_metrics(daily_pnl, capital, trades_for_legacy, intraday_equity=intraday_equity)

    # Total return verification and assignment
    net_pnl_sum = float(trades["net_pnl"].sum()) if not trades.empty and "net_pnl" in trades.columns else 0.0
    calc_total_return = net_pnl_sum / capital
    if not math.isclose(calc_total_return, m["total_return"], abs_tol=1e-9):
        raise AccountingError(
            f"Total return mismatch: {calc_total_return} vs {m['total_return']}"
        )
    m["total_return"] = calc_total_return

    # Summary metrics
    m["basis"] = "calendar_daily"
    m["equity_basis"] = equity_basis
    m["net_pnl"] = net_pnl_sum

    if "gross_pnl" in trades.columns and not trades["gross_pnl"].isna().all():
        m["gross_pnl"] = float(trades["gross_pnl"].sum())
    else:
        m["gross_pnl"] = None

    if "fees" in trades.columns and not trades["fees"].isna().all():
        m["fees"] = float(trades["fees"].sum())
    elif "commission" in trades.columns and not trades["commission"].isna().all():
        m["fees"] = float(trades["commission"].sum())
    else:
        m["fees"] = None

    if "slippage" in trades.columns and not trades["slippage"].isna().all():
        m["slippage"] = float(trades["slippage"].sum())
    else:
        m["slippage"] = None

    if "r_multiple" in trades.columns and not trades["r_multiple"].isna().all():
        m["avg_r"] = float(trades["r_multiple"].dropna().mean())
    else:
        m["avg_r"] = None

    m["annualised_from_short_window"] = len(daily) < 252

    # Remove unsupported legacy keys
    m.pop("mar", None)
    m.pop("exposure_pct", None)
    m.pop("turnover", None)

    # Convert counts to int where appropriate
    if "max_drawdown_duration" in m and not (np.isnan(m["max_drawdown_duration"]) if isinstance(m["max_drawdown_duration"], float) else False):
        m["max_drawdown_duration"] = int(round(m["max_drawdown_duration"]))
    m["num_trades"] = int(len(trades))

    if "intraday_max_drawdown" not in m:
        m["intraday_max_drawdown"] = None

    # Replace every NaN/±inf with None
    res = {}
    for k, v in m.items():
        res[k] = _clean_val(v)

    # Ensure all target keys from §3.1 are present
    target_keys = [
        "basis",
        "net_pnl",
        "gross_pnl",
        "fees",
        "slippage",
        "total_return",
        "cagr",
        "sharpe",
        "sortino",
        "calmar",
        "max_drawdown",
        "max_drawdown_duration",
        "intraday_max_drawdown",
        "volatility",
        "ulcer_index",
        "worst_day",
        "expected_shortfall_95",
        "num_trades",
        "hit_rate",
        "profit_factor",
        "payoff",
        "avg_win",
        "avg_loss",
        "expectancy",
        "avg_r",
        "final_equity",
        "annualised_from_short_window",
    ]
    for k in target_keys:
        if k not in res:
            res[k] = None

    return res
