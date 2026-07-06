"""Export RunResult artifacts (HLD §8.4)."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from stolgo.report.result import RunResult


def export_csv(result: RunResult, trades_path: Path) -> None:
    """Write trades only (accounting export)."""
    result.trades.to_csv(trades_path, index=False)


def _persist_series_enabled() -> bool:
    val = os.environ.get("STOLGO_PERSIST_SERIES", "1").strip().lower()
    return val not in {"0", "false", "no", "off"}


def _drawdown_from_equity(equity: pd.Series) -> pd.Series:
    # Peak-relative drawdown in percent, matching the report metrics basis.
    peak = equity.cummax()
    return ((equity - peak) / peak.replace(0, float("nan"))) * 100.0


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
        _drawdown_from_equity(result.equity).to_frame("drawdown").to_parquet(
            directory / "drawdown.parquet"
        )


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _write_manifest(
    result: RunResult,
    directory: Path,
    *,
    final_directory: Path | None = None,
    strategy_name: str | None = None,
) -> dict[str, Any]:
    final_directory = final_directory or directory
    manifest = {
        "schema_version": 1,
        "run_id": final_directory.name,
        "kind": "run",
        "strategy": strategy_name or result.params.get("strategy", "Unknown"),
        "params": result.params,
        "metrics": result.metrics,
        "created_at": _now_iso(),
        "path": str(final_directory),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    return manifest


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


def export_all(result: RunResult, directory: Path, *, strategy_name: str | None = None) -> None:
    """HTML tearsheet + JSON summary + CSV trades + Parquet bundle."""
    directory = Path(directory)
    tmp = directory.with_name(directory.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    result.report.to_html(tmp / "tearsheet.html")
    export_json(result, tmp / "summary.json")
    export_csv(result, tmp / "trades.csv")
    export_parquet(result, tmp / "parquet")
    manifest = _write_manifest(result, tmp, final_directory=directory, strategy_name=strategy_name)
    _replace_directory(tmp, directory)
    _upsert_manifest(manifest, directory)


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
