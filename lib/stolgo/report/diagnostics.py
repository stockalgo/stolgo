from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


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


def build_diagnostics(
    trades_v2: pd.DataFrame,
    daily: pd.DataFrame,
    capital: float,
    source_manifest: dict[str, Any] | None = None,
    *,
    has_audit_file: bool = False,
) -> dict[str, Any]:
    """Build the diagnostics dict (§3.1) from v2 trades, daily, capital, and source manifest."""
    source_manifest = source_manifest or {}
    source_params = source_manifest.get("params") or {}
    source_metrics = source_manifest.get("metrics") or {}

    # 1. exit_reasons: value_counts() ordered by count desc
    if not trades_v2.empty and "exit_reason" in trades_v2.columns:
        exit_counts = trades_v2["exit_reason"].value_counts().to_dict()
    else:
        exit_counts = {}

    # 2. data_quality
    trades_total = len(trades_v2)
    missing_mask = (trades_v2["data_flag"] != "") if not trades_v2.empty and "data_flag" in trades_v2.columns else pd.Series([], dtype=bool)
    trades_with_missing_data = int(missing_mask.sum())

    missing_reasons = {}
    if trades_with_missing_data > 0:
        missing_reasons = trades_v2.loc[missing_mask, "data_flag"].value_counts().to_dict()

    unresolved_sessions = source_metrics.get("unresolved", source_params.get("unresolved_sessions", 0))
    skipped_sessions = source_metrics.get("skipped", source_params.get("skipped_sessions", 0))
    eligible_sessions = source_metrics.get("eligible", source_params.get("eligible_sessions", None))

    data_quality = {
        "trades_total": trades_total,
        "trades_with_missing_data": trades_with_missing_data,
        "missing_reasons": missing_reasons,
        "unresolved_sessions": int(unresolved_sessions) if unresolved_sessions is not None else 0,
        "skipped_sessions": int(skipped_sessions) if skipped_sessions is not None else 0,
        "eligible_sessions": int(eligible_sessions) if eligible_sessions is not None else None,
    }

    # 3. stability: split trades by trade_id into first ceil(n/2) and rest
    if trades_total > 0:
        n_early = math.ceil(trades_total / 2)
        early_trades = trades_v2.iloc[:n_early]
        recent_trades = trades_v2.iloc[n_early:]

        def _half_stats(half: pd.DataFrame) -> dict[str, Any]:
            if half.empty:
                return {"trades": 0, "net_pnl": 0.0, "hit_rate": 0.0, "start": None, "end": None}
            t_count = len(half)
            net_pnl = float(half["net_pnl"].sum())
            hit_rate = float((half["net_pnl"] > 0).mean())
            start = str(half["session_date"].iloc[0])
            end = str(half["session_date"].iloc[-1])
            return {
                "trades": t_count,
                "net_pnl": round(net_pnl, 2),
                "hit_rate": round(hit_rate, 6),
                "start": start,
                "end": end,
            }

        stability = {
            "split": "half_by_trade_count",
            "early": _half_stats(early_trades),
            "recent": _half_stats(recent_trades),
        }
    else:
        stability = {
            "split": "half_by_trade_count",
            "early": {"trades": 0, "net_pnl": 0.0, "hit_rate": 0.0, "start": None, "end": None},
            "recent": {"trades": 0, "net_pnl": 0.0, "hit_rate": 0.0, "start": None, "end": None},
        }

    # 4. monthly: from daily, group by session[:7]
    if not daily.empty and "session" in daily.columns and "pnl" in daily.columns:
        months_series = daily["session"].str.slice(0, 7)
        monthly_groups = daily.groupby(months_series)["pnl"].sum()
        n_months = len(monthly_groups)
        prof_months = int((monthly_groups > 0).sum())
        monthly_pcts = (monthly_groups / capital).values if capital > 0 else np.array([0.0])
        mean_monthly_pct = float(np.mean(monthly_pcts)) if len(monthly_pcts) else 0.0
        median_monthly_pct = float(np.median(monthly_pcts)) if len(monthly_pcts) else 0.0

        monthly = {
            "months": n_months,
            "profitable_months": prof_months,
            "mean_monthly_pct": round(mean_monthly_pct, 6),
            "median_monthly_pct": round(median_monthly_pct, 6),
        }
    else:
        monthly = {
            "months": 0,
            "profitable_months": 0,
            "mean_monthly_pct": 0.0,
            "median_monthly_pct": 0.0,
        }

    # 5. extremes: best_trade, worst_trade, worst_mtm, max_stop_overshoot
    best_trade = float(trades_v2["net_pnl"].max()) if not trades_v2.empty else None
    worst_trade = float(trades_v2["net_pnl"].min()) if not trades_v2.empty else None
    worst_mtm = source_metrics.get("worst_mtm", source_params.get("worst_mtm", None))
    max_stop_overshoot = source_metrics.get(
        "max_stop_overshoot", source_params.get("max_stop_overshoot", None)
    )

    extremes = {
        "best_trade": _clean_val(best_trade),
        "worst_trade": _clean_val(worst_trade),
        "worst_mtm": _clean_val(worst_mtm),
        "max_stop_overshoot": _clean_val(max_stop_overshoot),
    }

    # 6. decision_counts
    decision_counts = source_params.get("decision_counts", None)

    # 7. validation
    val_status = source_params.get("validation_status", None)
    audit_summary = source_params.get("audit_summary", None)
    model_limitations = source_params.get("model_limitations", [])
    if isinstance(model_limitations, str):
        model_limitations = [model_limitations]

    caveats: list[str] = []
    if "caveat" in source_params and source_params["caveat"]:
        caveats.append(str(source_params["caveat"]))
    elif "caveats" in source_params:
        raw_c = source_params["caveats"]
        if isinstance(raw_c, list):
            caveats.extend(str(x) for x in raw_c)
        elif raw_c:
            caveats.append(str(raw_c))

    ledger_audit = source_params.get("ledger_audit", None)
    report_avail = bool(
        source_params.get("report_available") or source_manifest.get("has", {}).get("audit") or has_audit_file
    )

    validation = {
        "status": val_status,
        "summary": audit_summary,
        "limitations": model_limitations,
        "caveats": caveats,
        "ledger_audit": ledger_audit,
        "report_available": report_avail,
    }

    return {
        "exit_reasons": exit_counts,
        "data_quality": data_quality,
        "stability": stability,
        "monthly": monthly,
        "extremes": extremes,
        "decision_counts": decision_counts,
        "validation": validation,
    }
