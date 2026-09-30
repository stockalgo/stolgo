"""Export RunResult artifacts (HLD §8.4) and Run v2 schema."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import numpy as np
import pandas as pd

from stolgo.report.daily import build_daily, sessions_from_ohlcv
from stolgo.report.diagnostics import build_diagnostics
from stolgo.report.quality import run_status
from stolgo.report.result import RunResult
from stolgo.report.robustness import robustness
from stolgo.report.run_metrics import compute_run_metrics
from stolgo.report.trade_schema import SourceMapping, normalize_trades
from stolgo.report.validate import RunValidationError, validate_run_frames


def export_csv(result: RunResult, trades_path: Path) -> None:
    """Write trades only (accounting export)."""
    result.trades.to_csv(trades_path, index=False)


def _persist_series_enabled() -> bool:
    val = os.environ.get("STOLGO_PERSIST_SERIES", "1").strip().lower()
    return val not in {"0", "false", "no", "off"}


def export_parquet(result: RunResult, directory: Path) -> None:
    """Write trades, equity, and events to Parquet files."""
    directory.mkdir(parents=True, exist_ok=True)
    result.trades.to_parquet(directory / "trades.parquet", index=False)
    result.equity.to_frame("equity").to_parquet(directory / "equity.parquet")
    if not result.positions.empty:
        result.positions.to_parquet(directory / "positions.parquet")

    if _persist_series_enabled():
        if result.ohlcv is not None and not result.ohlcv.empty:
            result.ohlcv.to_parquet(directory / "ohlcv.parquet")


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _get_git_commit_short() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return None


def _replace_directory(tmp: Path, directory: Path) -> None:
    if directory.exists():
        shutil.rmtree(directory)
    os.replace(tmp, directory)


def _upsert_manifest(manifest: dict[str, Any], directory: Path) -> None:
    try:
        from stolgo.ui.index import upsert_run
    except ImportError:
        return

    upsert_run(manifest, index_path=directory.parent / "_index.duckdb")


def export_json(result: RunResult, path: Path) -> None:
    result.to_json(path)


def export_run_v2(
    directory: Path | str,
    *,
    run_id: str,
    name: str,
    trades_v2: pd.DataFrame,
    legs_v2: pd.DataFrame | None,
    daily: pd.DataFrame,
    instrument: dict[str, Any],
    group: dict[str, Any],
    config: dict[str, Any],
    metrics: dict[str, Any],
    robustness: dict[str, Any],
    diagnostics: dict[str, Any],
    ohlcv: pd.DataFrame | None = None,
    ohlcv_market: str | None = None,
    intraday_equity: pd.Series | pd.DataFrame | None = None,
    extra_files: dict[str, Path] | None = None,
    created_at: str | None = None,
    migrated_at: str | None = None,
    migrated_changed_basis: bool | None = None,
) -> dict[str, Any]:
    """Write run directory layout according to v2 specification (§2).

    Atomic write using tmp directory + _replace_directory.
    Validates run frames first via validate_run_frames.
    Fails loudly if NaN/Inf slips into manifest.json.
    """
    directory = Path(directory)

    # Validate frames
    if not trades_v2.empty:
        exchange = instrument.get("exchange", "NSE")
        problems = validate_run_frames(trades_v2, daily, legs=legs_v2, exchange=exchange)
        if problems:
            raise RunValidationError(f"Validation failed for run {run_id}: " + "; ".join(problems))

    tmp = directory.with_name(directory.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    parquet_dir = tmp / "parquet"
    parquet_dir.mkdir(parents=True, exist_ok=True)

    # Write trades
    trades_v2.to_csv(tmp / "trades.csv", index=False)
    trades_v2.to_parquet(parquet_dir / "trades.parquet", index=False)

    # Write daily
    daily.to_parquet(parquet_dir / "daily.parquet", index=False)

    # Write legs if present
    if legs_v2 is not None and not legs_v2.empty:
        legs_v2.to_parquet(parquet_dir / "legs.parquet", index=False)

    # Write ohlcv if present
    if ohlcv is not None and not ohlcv.empty:
        ohlcv.to_parquet(parquet_dir / "ohlcv.parquet")

    # Write intraday equity if present
    if intraday_equity is not None and not intraday_equity.empty:
        if isinstance(intraday_equity, pd.Series):
            intraday_equity.to_frame("equity").to_parquet(parquet_dir / "equity.parquet")
        else:
            intraday_equity.to_parquet(parquet_dir / "equity.parquet")

    # Copy extra files
    if extra_files:
        for rel_name, src_path in extra_files.items():
            if Path(src_path).is_file():
                dest = tmp / rel_name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest)

    # Status determination
    window_sessions = config.get("window", {}).get("sessions", len(daily))
    status, status_reasons = run_status(
        name,
        metrics,
        diagnostics,
        window_sessions,
        raw_params=config.get("raw_params"),
    )

    has_ohlcv = (ohlcv is not None and not ohlcv.empty) or (parquet_dir / "ohlcv.parquet").is_file()
    has_block = {
        "ohlcv": has_ohlcv,
        "legs": (legs_v2 is not None and not legs_v2.empty)
        or (parquet_dir / "legs.parquet").is_file(),
        "intraday_equity": (intraday_equity is not None and not intraday_equity.empty)
        or (parquet_dir / "equity.parquet").is_file(),
        "audit": (tmp / "audit.html").is_file(),
    }
    if has_ohlcv:
        mkt = ohlcv_market
        if not mkt:
            mkts = instrument.get("markets", [])
            if len(mkts) == 1:
                mkt = mkts[0]
        if mkt:
            has_block["ohlcv_market"] = mkt

    manifest = {
        "schema_version": 2,
        "run_id": run_id,
        "kind": "run",
        "name": name,
        "status": status,
        "status_reasons": status_reasons,
        "created_at": created_at or _now_iso(),
        "path": str(directory),
        "equity_basis": metrics.get("equity_basis", "mark_to_market"),
        "instrument": instrument,
        "group": group,
        "config": config,
        "metrics": metrics,
        "robustness": robustness,
        "diagnostics": diagnostics,
        "has": has_block,
    }
    if migrated_at:
        manifest["migrated_at"] = migrated_at
    if migrated_changed_basis is not None:
        manifest["migrated_changed_basis"] = bool(migrated_changed_basis)

    # Writing manifest with allow_nan=False raises ValueError on any NaN/Inf
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str, allow_nan=False))

    _replace_directory(tmp, directory)
    _upsert_manifest(manifest, directory)
    return manifest


def export_all(
    result: RunResult,
    directory: Path | str,
    *,
    strategy_name: str | None = None,
    capital: float | None = None,
    instrument: dict[str, Any] | None = None,
) -> None:
    """HTML tearsheet + JSON summary + CSV trades + Parquet bundle in v2 layout."""
    directory = Path(directory)
    cap = float(capital or result.params.get("cash", 100_000.0))

    if result.ohlcv is not None and not result.ohlcv.empty:
        sessions = sessions_from_ohlcv(result.ohlcv)
        ohlcv = result.ohlcv
        start_date = sessions[0].strftime("%Y-%m-%d") if len(sessions) else None
        end_date = sessions[-1].strftime("%Y-%m-%d") if len(sessions) else None
        n_sessions = len(sessions)
    else:
        sessions = pd.DatetimeIndex([], dtype="datetime64[ns]")
        ohlcv = None
        start_date = None
        end_date = None
        n_sessions = 0

    inst = instrument or {
        "asset_class": "equity",
        "markets": [],
        "exchange": "NSE",
        "structure": "long",
        "dte": [],
        "lot_size": None,
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    }

    # Normalize trades
    if result.trades.empty:
        mapping = SourceMapping(
            price_columns="none",
            structure="unknown",
            market=inst.get("market"),
            lot_size=None,
            side="from_column",
        )
    else:
        is_options = inst.get("asset_class") == "index_options"
        p_col = "premium" if is_options else "underlying"
        side_val = "from_column" if "side" in result.trades.columns else ("SHORT" if is_options else "LONG")
        mapping = SourceMapping(
            price_columns=p_col,
            structure="short_strangle" if is_options else "long",
            market=inst.get("market"),
            lot_size=None,
            side=side_val,
        )

    trades_v2, legs_v2 = normalize_trades(result.trades, mapping)

    has_mtm_equity = hasattr(result, "equity") and result.equity is not None and not result.equity.empty
    equity_basis = "mark_to_market" if has_mtm_equity else "realized"

    # Build daily
    if not trades_v2.empty and len(sessions) > 0:
        daily = build_daily(
            trades_v2,
            cap,
            sessions,
            equity=result.equity if has_mtm_equity else None,
            tz=inst.get("timezone", "Asia/Kolkata"),
        )
    else:
        daily = pd.DataFrame(columns=["session", "pnl", "equity", "drawdown", "trades_closed"])

    # Metrics
    if not daily.empty:
        metrics = compute_run_metrics(
            trades_v2,
            cap,
            daily,
            intraday_equity=result.equity if has_mtm_equity else None,
            equity_basis=equity_basis,
        )
    else:
        metrics = {
            "basis": "calendar_daily",
            "equity_basis": equity_basis,
            "net_pnl": 0.0,
            "gross_pnl": 0.0,
            "fees": 0.0,
            "slippage": None,
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": None,
            "calmar": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "intraday_max_drawdown": None,
            "volatility": 0.0,
            "ulcer_index": 0.0,
            "worst_day": 0.0,
            "expected_shortfall_95": 0.0,
            "num_trades": 0,
            "hit_rate": 0.0,
            "profit_factor": None,
            "payoff": None,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
            "avg_r": None,
            "final_equity": cap,
            "annualised_from_short_window": True,
        }

    # Robustness
    net_pnl_series = trades_v2["net_pnl"].values if not trades_v2.empty and "net_pnl" in trades_v2.columns else []
    robustness_dict = robustness(net_pnl_series)

    # Diagnostics
    source_manifest_mock = {"params": result.params, "metrics": result.metrics}
    diagnostics_dict = build_diagnostics(trades_v2, daily, cap, source_manifest_mock)

    group = {"id": None, "label": None, "axes": {}}
    code_version = _get_git_commit_short()
    config = {
        "capital": cap,
        "window": {"start": start_date, "end": end_date, "sessions": n_sessions},
        "entry_rule": None,
        "exit_rule": None,
        "execution": None,
        "cost_model": None,
        "data_source": None,
        "code_version": code_version,
        "raw_params": result.params,
    }

    # Build extra files (tearsheet, summary.json, positions)
    tmp_scratch = directory.with_name(directory.name + ".scratch")
    if tmp_scratch.exists():
        shutil.rmtree(tmp_scratch)
    tmp_scratch.mkdir(parents=True)

    extra_files: dict[str, Path] = {}
    if hasattr(result, "report") and hasattr(result.report, "to_html"):
        t_path = tmp_scratch / "tearsheet.html"
        result.report.to_html(t_path)
        extra_files["tearsheet.html"] = t_path

    if hasattr(result, "to_json"):
        s_path = tmp_scratch / "summary.json"
        result.to_json(s_path)
        extra_files["summary.json"] = s_path

    if not result.positions.empty:
        pos_path = tmp_scratch / "positions.parquet"
        result.positions.to_parquet(pos_path)
        extra_files["parquet/positions.parquet"] = pos_path

    try:
        export_run_v2(
            directory,
            run_id=directory.name,
            name=strategy_name or directory.name,
            trades_v2=trades_v2,
            legs_v2=legs_v2,
            daily=daily,
            instrument=inst,
            group=group,
            config=config,
            metrics=metrics,
            robustness=robustness_dict,
            diagnostics=diagnostics_dict,
            ohlcv=ohlcv,
            intraday_equity=result.equity if hasattr(result, "equity") and not result.equity.empty else None,
            extra_files=extra_files,
        )
    finally:
        if tmp_scratch.exists():
            shutil.rmtree(tmp_scratch)


def export_sweep(
    df: pd.DataFrame,
    directory: Path,
    *,
    param_grid: dict[str, Any],
    strategy_name: str,
) -> None:
    directory = Path(directory)
    tmp = directory.with_name(directory.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    df.to_parquet(tmp / "results.parquet", index=False)
    manifest = {
        "schema_version": 1,
        "run_id": directory.name,
        "kind": "sweep",
        "strategy": strategy_name,
        "param_grid": {k: list(v) for k, v in param_grid.items()},
        "created_at": _now_iso(),
        "path": str(directory),
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    _replace_directory(tmp, directory)
    _upsert_manifest(manifest, directory)
