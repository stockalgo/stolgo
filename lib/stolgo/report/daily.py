from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

IST = "Asia/Kolkata"


def sessions_from_ohlcv(ohlcv: pd.DataFrame) -> pd.DatetimeIndex:
    """Unique IST dates (tz-naive, normalized) that have at least one bar."""
    if ohlcv.empty:
        return pd.DatetimeIndex([], dtype="datetime64[ns]")

    if isinstance(ohlcv.index, pd.DatetimeIndex):
        idx = ohlcv.index
    elif "timestamp" in ohlcv.columns:
        idx = pd.to_datetime(ohlcv["timestamp"])
    else:
        raise ValueError("ohlcv must have a DatetimeIndex or 'timestamp' column")

    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    ist_idx = idx.tz_convert(IST).tz_localize(None).normalize()
    return pd.DatetimeIndex(sorted(ist_idx.unique()))


def load_calendar(runs_dir: Path, exchange: str) -> pd.DatetimeIndex:
    """Read runs/_calendars/{exchange}.parquet column 'session'. Raise FileNotFoundError if absent."""
    cal_file = Path(runs_dir) / "_calendars" / f"{exchange}.parquet"
    if not cal_file.is_file():
        raise FileNotFoundError(f"Calendar file {cal_file} not found")
    df = pd.read_parquet(cal_file)
    if "session" not in df.columns:
        raise ValueError(f"Calendar file {cal_file} does not contain 'session' column")
    sessions = pd.to_datetime(df["session"]).dt.tz_localize(None).dt.normalize()
    return pd.DatetimeIndex(sorted(sessions.unique()))


def build_calendar_files(runs_dir: Path) -> dict[str, int]:
    """Union of sessions_from_ohlcv over every runs/*/parquet/ohlcv.parquet grouped by exchange
    (NIFTY→NSE, SENSEX→BSE; exchange read from manifest instrument/params.index or run_id prefix).
    Writes runs/_calendars/NSE.parquet and BSE.parquet. Returns {exchange: n_sessions}.
    """
    runs_dir = Path(runs_dir)
    scan_dir = runs_dir / "_backup_v1" if (runs_dir / "_backup_v1").is_dir() else runs_dir
    out_dir = runs_dir / "_calendars"
    out_dir.mkdir(parents=True, exist_ok=True)

    nse_sessions: set[pd.Timestamp] = set()
    bse_sessions: set[pd.Timestamp] = set()

    for p in scan_dir.glob("*/parquet/ohlcv.parquet"):
        run_dir = p.parent.parent
        name = run_dir.name.lower()
        exchange = "NSE"
        manifest_path = run_dir / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text())
                inst = manifest.get("instrument") or {}
                raw_idx = (
                    manifest.get("params", {}).get("index")
                    or inst.get("exchange")
                    or inst.get("market")
                )
                if raw_idx and "sensex" in str(raw_idx).lower():
                    exchange = "BSE"
                elif raw_idx and "nifty" in str(raw_idx).lower():
                    exchange = "NSE"
                elif "sensex" in name:
                    exchange = "BSE"
            except Exception:
                if "sensex" in name:
                    exchange = "BSE"
        elif "sensex" in name:
            exchange = "BSE"

        df = pd.read_parquet(p)
        sessions = sessions_from_ohlcv(df)
        if exchange == "BSE":
            bse_sessions.update(sessions)
        else:
            nse_sessions.update(sessions)

    nse_idx = pd.DatetimeIndex(sorted(nse_sessions))
    bse_idx = pd.DatetimeIndex(sorted(bse_sessions))

    pd.DataFrame({"session": nse_idx}).to_parquet(out_dir / "NSE.parquet", index=False)
    pd.DataFrame({"session": bse_idx}).to_parquet(out_dir / "BSE.parquet", index=False)

    return {"NSE": len(nse_idx), "BSE": len(bse_idx)}


def build_daily(trades: pd.DataFrame, capital: float, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Return the daily.parquet frame (§3.4).
    - window = [IST date of min(entry_ts), IST date of max(exit_ts)]
    - sessions restricted to the window; if an exit date is not in `sessions`, raise ValueError
      naming the date (do NOT silently add it)
    - pnl = groupby(IST exit date).net_pnl.sum(); missing sessions → 0.0
    - if any trade has net_pnl NaN → that session's pnl = NaN
    """
    cols = ["session", "pnl", "equity", "drawdown", "trades_closed"]
    if trades.empty:
        return pd.DataFrame(
            {
                "session": pd.Series([], dtype="string"),
                "pnl": pd.Series([], dtype="float64"),
                "equity": pd.Series([], dtype="float64"),
                "drawdown": pd.Series([], dtype="float64"),
                "trades_closed": pd.Series([], dtype="int64"),
            }
        )

    entry_ts = pd.to_datetime(trades["entry_ts"])
    exit_ts = pd.to_datetime(trades["exit_ts"])

    if entry_ts.dt.tz is None:
        entry_ts = entry_ts.dt.tz_localize("UTC")
    if exit_ts.dt.tz is None:
        exit_ts = exit_ts.dt.tz_localize("UTC")

    entry_ist = entry_ts.dt.tz_convert(IST).dt.tz_localize(None).dt.normalize()
    exit_ist = exit_ts.dt.tz_convert(IST).dt.tz_localize(None).dt.normalize()

    min_date = entry_ist.min()
    max_date = exit_ist.max()

    sessions_normalized = pd.DatetimeIndex(sorted(sessions.unique())).normalize()
    sessions_set = set(sessions_normalized)

    for d in exit_ist:
        if d not in sessions_set:
            raise ValueError(f"Exit date {d.strftime('%Y-%m-%d')} is not in session calendar")

    window_sessions = sessions_normalized[
        (sessions_normalized >= min_date) & (sessions_normalized <= max_date)
    ]

    # Pre-aggregate trades by exit date
    pnl_by_date: dict[pd.Timestamp, float] = {}
    trades_closed_by_date: dict[pd.Timestamp, int] = {}

    work_df = pd.DataFrame({"exit_date": exit_ist, "net_pnl": trades["net_pnl"]})
    for date, group in work_df.groupby("exit_date"):
        trades_closed_by_date[date] = len(group)
        if group["net_pnl"].isna().any():
            pnl_by_date[date] = float("nan")
        else:
            pnl_by_date[date] = float(group["net_pnl"].sum())

    session_strs = []
    pnls = []
    closed_counts = []

    for s in window_sessions:
        session_strs.append(s.strftime("%Y-%m-%d"))
        pnls.append(pnl_by_date.get(s, 0.0))
        closed_counts.append(trades_closed_by_date.get(s, 0))

    pnls_arr = np.array(pnls, dtype=float)
    cumsum_pnl = np.cumsum(pnls_arr)
    equity_arr = capital + cumsum_pnl

    # Drawdown including initial capital
    peak = np.maximum.accumulate(np.insert(equity_arr, 0, capital))[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        drawdown_arr = np.where(peak > 0, equity_arr / peak - 1.0, 0.0)

    return pd.DataFrame(
        {
            "session": session_strs,
            "pnl": pnls_arr,
            "equity": equity_arr,
            "drawdown": drawdown_arr,
            "trades_closed": np.array(closed_counts, dtype=np.int64),
        }
    )
