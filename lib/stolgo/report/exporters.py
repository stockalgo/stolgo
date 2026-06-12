# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Export RunResult artifacts (HLD §8.4)."""

from __future__ import annotations

import json
from pathlib import Path

from stolgo.report.result import RunResult


def export_csv(result: RunResult, trades_path: Path) -> None:
    """Write trades only (accounting export)."""
    result.trades.to_csv(trades_path, index=False)


def export_parquet(result: RunResult, directory: Path) -> None:
    """Write trades, equity, and events to Parquet files."""
    directory.mkdir(parents=True, exist_ok=True)
    result.trades.to_parquet(directory / "trades.parquet", index=False)
    result.equity.to_frame("equity").to_parquet(directory / "equity.parquet")
    if not result.positions.empty:
        result.positions.to_parquet(directory / "positions.parquet")


def export_json(result: RunResult, path: Path) -> None:
    result.to_json(path)


def export_all(result: RunResult, directory: Path) -> None:
    """HTML tearsheet + JSON summary + CSV trades + Parquet bundle."""
    directory.mkdir(parents=True, exist_ok=True)
    result.report.to_html(directory / "tearsheet.html")
    export_json(result, directory / "summary.json")
    export_csv(result, directory / "trades.csv")
    export_parquet(result, directory / "parquet")
