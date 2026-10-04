from __future__ import annotations

from typing import Any

MIN_TRADES_OK: int = 100
MIN_SESSIONS_OK: int = 252
DATA_ISSUE_THRESHOLD: float = 0.05


def run_status(
    name: str,
    metrics: dict[str, Any],
    diagnostics: dict[str, Any],
    sessions: int,
    *,
    raw_params: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Determine run status and list of reasons per §3.1 precedence.

    Precedence (first match wins for status):
    empty (0 trades) > superseded (name starts with "INVALID" or raw_params.superseded == true)
    > data_issues (trades_with_missing_data / trades_total > 0.05 or unresolved_sessions > 0)
    > low_sample (< 100 trades) > short_window (< 252 sessions) > ok.

    status_reasons holds one short human string for every condition that matched.
    """
    raw_params = raw_params or {}
    dq = diagnostics.get("data_quality") or {}
    trades_total = dq.get("trades_total", metrics.get("num_trades", 0))
    trades_with_missing_data = dq.get("trades_with_missing_data", 0)
    unresolved_sessions = dq.get("unresolved_sessions", 0)
    pnl_reconciles = dq.get("pnl_reconciles", True)
    pnl_unreconciled_inr = dq.get("pnl_unreconciled_inr", 0.0)

    is_empty = (trades_total == 0)
    is_superseded = name.startswith("INVALID") or (raw_params.get("superseded") is True)
    has_missing_data = (
        trades_total > 0
        and (trades_with_missing_data / trades_total) > DATA_ISSUE_THRESHOLD
    )
    has_unresolved = (unresolved_sessions > 0)
    has_unreconciled_pnl = (pnl_reconciles is False)
    is_data_issues = has_missing_data or has_unresolved or has_unreconciled_pnl
    is_low_sample = (trades_total < MIN_TRADES_OK)
    is_short_window = (sessions < MIN_SESSIONS_OK)

    reasons: list[str] = []
    if is_empty:
        reasons.append("0 trades")
    if is_superseded:
        reasons.append("marked superseded")
    if has_missing_data:
        reasons.append(
            f"{trades_with_missing_data} of {trades_total} trades exited on missing data"
        )
    if has_unresolved:
        reasons.append(f"{unresolved_sessions} unresolved sessions")
    if has_unreconciled_pnl:
        abs_diff = abs(pnl_unreconciled_inr)
        reasons.append(f"net P&L differs from gross − fees by ₹{abs_diff:,.0f}")
    if is_low_sample and not is_empty:
        reasons.append(f"{trades_total} trades < 100")
    if is_short_window:
        reasons.append(f"{sessions} sessions < 252")

    if is_empty:
        status = "empty"
    elif is_superseded:
        status = "superseded"
    elif is_data_issues:
        status = "data_issues"
    elif is_low_sample:
        status = "low_sample"
    elif is_short_window:
        status = "short_window"
    else:
        status = "ok"

    return status, reasons
