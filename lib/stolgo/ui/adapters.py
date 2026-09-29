"""Pure adapters from stolgo artifacts to frontend JSON contracts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from stolgo.report.metric_registry import metric_defs


def _clean(obj: Any) -> Any:
    """Recursively converts NaN/inf to None and normalizes numpy types."""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return None if (np.isnan(obj) or np.isinf(obj)) else float(obj)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return int(obj.timestamp())
    if pd.isna(obj):
        return None
    return obj


def _to_secs(ts: Any) -> int | None:
    if ts is None or pd.isna(ts):
        return None
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return int(t.timestamp())


def run_summary_v2(manifest: dict) -> dict:
    """Format manifest as §4.1 RunSummary JSON object."""
    run_id = str(manifest.get("run_id", ""))
    inst = manifest.get("instrument") or {}
    group = manifest.get("group") or {}
    config = manifest.get("config") or {}
    window = manifest.get("window") or config.get("window") or {}
    metrics = manifest.get("metrics") or {}
    rob = manifest.get("robustness") or {}
    diag = manifest.get("diagnostics") or {}
    dq = diag.get("data_quality") or {}
    has_flags = manifest.get("has") or {}

    summary_metrics = {
        "net_pnl": metrics.get("net_pnl"),
        "total_return": metrics.get("total_return"),
        "cagr": metrics.get("cagr"),
        "sharpe": metrics.get("sharpe"),
        "max_drawdown": metrics.get("max_drawdown"),
        "profit_factor": metrics.get("profit_factor"),
        "hit_rate": metrics.get("hit_rate"),
        "num_trades": metrics.get("num_trades"),
        "expectancy": metrics.get("expectancy"),
        "annualised_from_short_window": metrics.get("annualised_from_short_window", False),
    }

    raw = {
        "id": run_id,
        "name": manifest.get("name") or run_id,
        "status": manifest.get("status", "ok"),
        "status_reasons": manifest.get("status_reasons", []),
        "markets": inst.get("markets", []),
        "structure": inst.get("structure", ""),
        "dte": inst.get("dte", []),
        "group": {
            "id": group.get("id"),
            "label": group.get("label"),
            "axes": group.get("axes", {}),
        },
        "window": {
            "start": window.get("start"),
            "end": window.get("end"),
            "sessions": window.get("sessions", 0),
        },
        "capital": float(config.get("capital", 0.0)) if config.get("capital") is not None else 0.0,
        "metrics": summary_metrics,
        "robustness": {
            "p_net_positive": rob.get("p_net_positive"),
            "net_without_top5": rob.get("net_without_top5"),
        },
        "data_quality": {
            "trades_with_missing_data": dq.get("trades_with_missing_data", 0),
            "trades_total": dq.get("trades_total", metrics.get("num_trades", 0)),
        },
        "has": {
            "ohlcv": bool(has_flags.get("ohlcv", False)),
            "legs": bool(has_flags.get("legs", False)),
            "intraday_equity": bool(has_flags.get("intraday_equity", False)),
            "audit": bool(has_flags.get("audit", False)),
        },
        "created_at": manifest.get("created_at"),
        "migrated_at": manifest.get("migrated_at"),
        "migrated_changed_basis": manifest.get("migrated_changed_basis", False),
    }
    return _clean(raw)


def run_detail_v2(manifest: dict) -> dict:
    """Format manifest as §4.2 RunDetail JSON object."""
    summary = run_summary_v2(manifest)
    detail = dict(summary)
    detail["instrument"] = manifest.get("instrument", {})
    detail["config"] = manifest.get("config", {})
    detail["metrics"] = manifest.get("metrics", {})
    detail["robustness"] = manifest.get("robustness", {})
    detail["diagnostics"] = manifest.get("diagnostics", {})
    detail["metric_defs"] = metric_defs()
    return _clean(detail)


def trades_v2_rows(df: pd.DataFrame) -> dict:
    """Format trades dataframe as §4.5 TradeV2[] response."""
    if df.empty:
        return {"rows": [], "columns": list(df.columns)}
    work = df.copy()
    for col in ("entry_ts", "exit_ts"):
        if col in work.columns:
            work[col] = work[col].apply(_to_secs)
    return {
        "rows": _clean(work.to_dict(orient="records")),
        "columns": list(df.columns),
    }


def daily_rows(daily_df: pd.DataFrame) -> dict:
    """Format daily dataframe as §4.3 response."""
    if daily_df.empty:
        return {"rows": []}
    work = daily_df.copy()
    if "session" in work.columns:
        work["session"] = work["session"].astype(str).str.slice(0, 10)
    records = work.to_dict(orient="records")
    return {"rows": _clean(records)}


def monthly_rows(daily_df: pd.DataFrame, capital: float) -> dict:
    """Format monthly aggregation from daily dataframe as §4.4 response."""
    if daily_df.empty:
        return {"rows": []}
    work = daily_df.copy()
    work["month"] = work["session"].astype(str).str.slice(0, 7)
    grouped = work.groupby("month", sort=True)
    rows = []
    cap = float(capital) if capital and capital > 0 else 0.0
    for month, group in grouped:
        pnl = float(group["pnl"].sum())
        ret_pct = pnl / cap if cap > 0 else None
        trades = int(group["trades_closed"].sum()) if "trades_closed" in group.columns else 0
        rows.append(
            {
                "month": str(month),
                "pnl": pnl,
                "return_pct": ret_pct,
                "trades": trades,
            }
        )
    return {"rows": _clean(rows)}


def candles(
    ohlcv: pd.DataFrame,
    tf: str = "1D",
    frm: str | None = None,
    to: str | None = None,
) -> dict:
    """Format and resample ohlcv as §4.7 Candle[] response."""
    if ohlcv is None or ohlcv.empty:
        return {"rows": [], "tf": tf}

    work = ohlcv.copy()
    if not isinstance(work.index, pd.DatetimeIndex):
        if "timestamp" in work.columns:
            work = work.set_index(pd.to_datetime(work["timestamp"], utc=True))
        else:
            raise ValueError("ohlcv must have a DatetimeIndex or timestamp column")

    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
    else:
        work.index = work.index.tz_convert("Asia/Kolkata")

    work["session_date"] = work.index.strftime("%Y-%m-%d")

    unique_sessions = sorted(work["session_date"].unique())
    if frm is not None or to is not None:
        if frm is not None:
            work = work[work["session_date"] >= frm]
        if to is not None:
            work = work[work["session_date"] <= to]
    else:
        limit = 180 if tf == "1D" else (20 if tf == "1H" else 5)
        selected_sessions = set(unique_sessions[-limit:])
        work = work[work["session_date"].isin(selected_sessions)]

    if work.empty:
        return {"rows": [], "tf": tf}

    has_vol = "volume" in work.columns

    if tf == "1D":
        records = []
        for s_date, grp in work.groupby("session_date", sort=True):
            t_s = int(grp.index[0].tz_convert("UTC").timestamp())
            rec = {
                "time": t_s,
                "open": float(grp["open"].iloc[0]),
                "high": float(grp["high"].max()),
                "low": float(grp["low"].min()),
                "close": float(grp["close"].iloc[-1]),
            }
            if has_vol:
                rec["volume"] = float(grp["volume"].sum())
            records.append(rec)
        return {"rows": _clean(records), "tf": tf}

    elif tf == "1H":
        records = []
        for s_date, s_grp in work.groupby("session_date", sort=True):
            hourly_matched = False
            for start_hour, end_hour in [
                ("09:15:00", "10:15:00"),
                ("10:15:00", "11:15:00"),
                ("11:15:00", "12:15:00"),
                ("12:15:00", "13:15:00"),
                ("13:15:00", "14:15:00"),
                ("14:15:00", "15:15:00"),
                ("15:15:00", "15:30:00"),
            ]:
                bar_grp = s_grp.between_time(
                    start_hour, end_hour, inclusive="left" if end_hour != "15:30:00" else "both"
                )
                if not bar_grp.empty:
                    hourly_matched = True
                    rec = {
                        "time": int(bar_grp.index[0].tz_convert("UTC").timestamp()),
                        "open": float(bar_grp["open"].iloc[0]),
                        "high": float(bar_grp["high"].max()),
                        "low": float(bar_grp["low"].min()),
                        "close": float(bar_grp["close"].iloc[-1]),
                    }
                    if has_vol:
                        rec["volume"] = float(bar_grp["volume"].sum())
                    records.append(rec)
            if not hourly_matched:
                rec = {
                    "time": int(s_grp.index[0].tz_convert("UTC").timestamp()),
                    "open": float(s_grp["open"].iloc[0]),
                    "high": float(s_grp["high"].max()),
                    "low": float(s_grp["low"].min()),
                    "close": float(s_grp["close"].iloc[-1]),
                }
                if has_vol:
                    rec["volume"] = float(s_grp["volume"].sum())
                records.append(rec)
        return {"rows": _clean(records), "tf": tf}

    else:  # 15m or raw
        records = []
        for ts, row in work.iterrows():
            rec = {
                "time": int(ts.tz_convert("UTC").timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
            if has_vol:
                rec["volume"] = float(row["volume"])
            records.append(rec)
        return {"rows": _clean(records), "tf": tf}


def trade_detail(
    trades_df: pd.DataFrame,
    legs_df: pd.DataFrame | None,
    ohlcv: pd.DataFrame | None,
    trade_id: int,
    ohlcv_market: str | None = None,
) -> dict:
    """Format single trade detail with optional legs and session bars as §4.6 response."""
    match = trades_df[trades_df["trade_id"] == trade_id]
    if match.empty:
        raise KeyError(f"trade {trade_id} not found")

    trade_row = match.iloc[0].to_dict()
    for col in ("entry_ts", "exit_ts"):
        trade_row[col] = _to_secs(trade_row.get(col))

    legs_rows: list[dict] = []
    if legs_df is not None and not legs_df.empty and "trade_id" in legs_df.columns:
        leg_matches = legs_df[legs_df["trade_id"] == trade_id]
        if not leg_matches.empty:
            work_legs = leg_matches.copy()
            for col in ("entry_ts", "exit_ts"):
                if col in work_legs.columns:
                    work_legs[col] = work_legs[col].apply(_to_secs)
            legs_rows = work_legs.to_dict(orient="records")

    bars: list[dict] = []
    trade_market = trade_row.get("market")
    market_matches = True
    if ohlcv_market is not None and trade_market is not None and str(trade_market).strip() != "":
        market_matches = (str(trade_market).strip().upper() == str(ohlcv_market).strip().upper())

    session_date = str(trade_row.get("session_date", ""))
    if market_matches and ohlcv is not None and not ohlcv.empty and session_date:
        work_ohlcv = ohlcv.copy()
        if not isinstance(work_ohlcv.index, pd.DatetimeIndex):
            if "timestamp" in work_ohlcv.columns:
                work_ohlcv = work_ohlcv.set_index(pd.to_datetime(work_ohlcv["timestamp"], utc=True))
        if work_ohlcv.index.tz is None:
            work_ohlcv.index = work_ohlcv.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
        else:
            work_ohlcv.index = work_ohlcv.index.tz_convert("Asia/Kolkata")

        work_ohlcv["date"] = work_ohlcv.index.strftime("%Y-%m-%d")
        session_bars = work_ohlcv[work_ohlcv["date"] == session_date]
        if not session_bars.empty:
            intraday = session_bars.between_time("09:15", "15:30")
            bars_to_use = intraday if not intraday.empty else session_bars
            has_vol = "volume" in bars_to_use.columns
            for ts, row in bars_to_use.iterrows():
                b = {
                    "time": int(ts.tz_convert("UTC").timestamp()),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
                if has_vol:
                    b["volume"] = float(row["volume"])
                bars.append(b)

    return _clean(
        {
            "trade": trade_row,
            "legs": legs_rows,
            "bars": bars,
        }
    )


# Backward compatibility helpers
def run_summary(manifest: dict) -> dict:
    if manifest.get("schema_version") == 2:
        return run_summary_v2(manifest)
    m = manifest.get("metrics", {})
    p = manifest.get("params", {})
    market = p.get("symbol") or p.get("index") or "-"
    dte_val = p.get("dte")
    timeframe = p.get("interval") or (f"{dte_val}DTE" if dte_val is not None else "-")
    return {
        "id": manifest["run_id"],
        "strategy": manifest.get("strategy") or manifest.get("name", "Unknown"),
        "market": market,
        "timeframe": timeframe,
        "return": m.get("total_return", 0.0),
        "sharpe": m.get("sharpe", 0.0),
        "drawdown": m.get("max_drawdown", 0.0),
        "trades": int(m.get("num_trades", 0)),
        "created_at": manifest.get("created_at"),
    }


def metric_cards(metrics: dict) -> list[dict]:
    order = [
        ("total_return", "Net return", "pct"),
        ("cagr", "CAGR", "pct"),
        ("sharpe", "Sharpe", "num"),
        ("max_drawdown", "Max drawdown", "pct"),
        ("profit_factor", "Profit factor", "num"),
        ("hit_rate", "Win rate", "pct"),
        ("expectancy", "Expectancy", "r"),
        ("num_trades", "Trades", "int"),
    ]
    return [
        {"key": key, "label": label, "value": metrics.get(key, 0.0), "fmt": fmt}
        for key, label, fmt in order
    ]


def series(ohlcv_df: pd.DataFrame, equity_s: pd.Series, drawdown_s: pd.Series) -> dict:
    candles_list = [
        {
            "time": _to_secs(index),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
        }
        for index, row in ohlcv_df.iterrows()
    ]
    volume = (
        [
            {
                "time": _to_secs(index),
                "value": float(row.volume),
                "color": "rgba(20,154,90,0.18)"
                if row.close >= row.open
                else "rgba(200,63,58,0.16)",
            }
            for index, row in ohlcv_df.iterrows()
        ]
        if "volume" in ohlcv_df.columns
        else []
    )
    equity = [{"time": _to_secs(index), "value": float(value)} for index, value in equity_s.items()]
    drawdown = [
        {"time": _to_secs(index), "value": float(value)} for index, value in drawdown_s.items()
    ]
    return _clean({"candles": candles_list, "volume": volume, "equity": equity, "drawdown": drawdown})
