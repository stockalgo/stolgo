from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

MARKET_HOURS_UTC: dict[str, tuple[dt.time, dt.time]] = {
    "NSE": (dt.time(3, 30), dt.time(10, 15)),
    "BSE": (dt.time(3, 30), dt.time(10, 15)),
}


class RunValidationError(ValueError):
    """Raised when run frames fail contract validation."""


def assert_utc(series: pd.Series, name: str) -> None:
    """tz must be UTC."""
    if series.empty:
        return
    tz = getattr(series.dt, "tz", None)
    if tz is None or str(tz) != "UTC":
        raise RunValidationError(f"{name} must have UTC timezone, got {tz}")


def looks_like_ist_labelled_utc(ts: pd.Series | pd.DataFrame, exchange: str = "NSE") -> bool:
    """True if >= 50% of timestamps fall outside MARKET_HOURS_UTC but inside the same window shifted by +5:30."""
    if isinstance(ts, pd.DataFrame):
        if "exit_ts" in ts.columns:
            series = ts["exit_ts"]
        elif "entry_ts" in ts.columns:
            series = ts["entry_ts"]
        else:
            series = ts.iloc[:, 0]
    else:
        series = ts

    valid_ts = series.dropna()
    if valid_ts.empty:
        return False

    utc_start, utc_end = MARKET_HOURS_UTC.get(exchange, (dt.time(3, 30), dt.time(10, 15)))

    # Shift window by +5:30
    def shift_time(t: dt.time, delta_m: int) -> dt.time:
        total_m = t.hour * 60 + t.minute + delta_m
        return dt.time((total_m // 60) % 24, total_m % 60)

    shifted_start = shift_time(utc_start, 330)  # 03:30 -> 09:00
    shifted_end = shift_time(utc_end, 330)      # 10:15 -> 15:45

    def in_window(t: dt.time, start: dt.time, end: dt.time) -> bool:
        if start <= end:
            return start <= t <= end
        return t >= start or t <= end

    matched = 0
    total = len(valid_ts)
    for val in valid_ts:
        t = val.time() if hasattr(val, "time") else pd.to_datetime(val).time()
        outside_utc = not in_window(t, utc_start, utc_end)
        inside_shifted = in_window(t, shifted_start, shifted_end)
        if outside_utc and inside_shifted:
            matched += 1

    return (matched / total) >= 0.5


def fix_ist_labelled_utc(ts: pd.Series) -> pd.Series:
    """ts.dt.tz_localize(None).dt.tz_localize('Asia/Kolkata').dt.tz_convert('UTC')"""
    return ts.dt.tz_localize(None).dt.tz_localize("Asia/Kolkata").dt.tz_convert("UTC")


def validate_run_frames(
    trades: pd.DataFrame,
    daily: pd.DataFrame,
    legs: pd.DataFrame | None = None,
    exchange: str = "NSE",
) -> list[str]:
    """Return list of problems. Checks: UTC tz on entry/exit; every entry/exit inside market hours;
    exit_ts >= entry_ts; net_pnl == gross_pnl − fees − slippage (±0.05) where slippage not NaN;
    daily sessions unique+sorted; daily.pnl.sum() == trades.net_pnl.sum() (±0.01).
    """
    problems: list[str] = []
    market_start, market_end = MARKET_HOURS_UTC.get(exchange, (dt.time(3, 30), dt.time(10, 15)))

    # 1. UTC tz on entry/exit
    for col in ("entry_ts", "exit_ts"):
        if col in trades.columns and not trades[col].empty:
            tz = getattr(trades[col].dt, "tz", None)
            if tz is None or str(tz) != "UTC":
                problems.append(f"trades.{col} is not timezone-aware UTC (got {tz})")

    # 2. Every entry/exit inside market hours (if exchange in MARKET_HOURS_UTC and not midnight daily bars)
    if exchange in MARKET_HOURS_UTC:
        market_start, market_end = MARKET_HOURS_UTC[exchange]
        for col in ("entry_ts", "exit_ts"):
            if col in trades.columns and not trades[col].empty:
                valid_ts = trades[col].dropna()
                out_of_bounds = [
                    t for t in valid_ts
                    if t.time() != dt.time(0, 0) and not (market_start <= t.time() <= market_end)
                ]
                if out_of_bounds:
                    problems.append(
                        f"trades.{col} has {len(out_of_bounds)} timestamps outside market hours "
                        f"[{market_start}, {market_end}] UTC (example: {out_of_bounds[0]})"
                    )

    # 3. exit_ts >= entry_ts
    if "entry_ts" in trades.columns and "exit_ts" in trades.columns and not trades.empty:
        invalid_order = (trades["exit_ts"] < trades["entry_ts"]).sum()
        if invalid_order > 0:
            problems.append(f"trades has {invalid_order} rows where exit_ts < entry_ts")

    # 4. net_pnl == gross_pnl − fees − slippage (±0.05) where slippage not NaN
    req_cols = {"gross_pnl", "fees", "net_pnl"}
    if req_cols.issubset(trades.columns) and not trades.empty:
        if "slippage" in trades.columns:
            mask = ~trades["slippage"].isna()
            slip = trades.loc[mask, "slippage"]
        else:
            mask = pd.Series(True, index=trades.index)
            slip = 0.0

        if mask.any():
            expected = trades.loc[mask, "gross_pnl"] - trades.loc[mask, "fees"] - slip
            actual = trades.loc[mask, "net_pnl"]
            diff = (actual - expected).abs()
            violators = (diff > 0.05).sum()
            if violators > 0:
                max_diff = diff.max()
                problems.append(
                    f"trades has {violators} rows where net_pnl != gross_pnl - fees - slippage (+/-0.05). "
                    f"Max diff: {max_diff:.4f}"
                )

    # 5. daily sessions unique+sorted
    if not daily.empty and "session" in daily.columns:
        sessions_series = pd.Series(daily["session"])
        if not sessions_series.is_monotonic_increasing:
            problems.append("daily.session is not monotonically increasing")
        if sessions_series.duplicated().any():
            dups = sessions_series[sessions_series.duplicated()].tolist()
            problems.append(f"daily.session contains duplicate dates: {dups[:5]}")

    # 6. daily.pnl.sum() == trades.net_pnl.sum() (±0.01)
    if "pnl" in daily.columns and "net_pnl" in trades.columns and not daily.empty and not trades.empty:
        daily_sum = float(daily["pnl"].sum())
        trades_sum = float(trades["net_pnl"].sum())
        if not (np.isnan(daily_sum) and np.isnan(trades_sum)):
            if abs(daily_sum - trades_sum) > 0.01:
                problems.append(
                    f"daily.pnl.sum() ({daily_sum:.2f}) does not match trades.net_pnl.sum() "
                    f"({trades_sum:.2f}) within 0.01"
                )

    # 7. Legs checks if provided
    if legs is not None and not legs.empty:
        for col in ("entry_ts", "exit_ts"):
            if col in legs.columns:
                valid_ts = legs[col].dropna()
                if not valid_ts.empty:
                    tz = getattr(valid_ts.dt, "tz", None)
                    if tz is None or str(tz) != "UTC":
                        problems.append(f"legs.{col} is not timezone-aware UTC (got {tz})")

    return problems
