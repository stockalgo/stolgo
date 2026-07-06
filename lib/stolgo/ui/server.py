"""Read-only FastAPI server for exported stolgo runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from stolgo.ui import adapters
from stolgo.ui import index as runs_index


SUPPORTED_SCHEMA_VERSION = 1


def create_app(runs_dir: Path | str = Path("runs"), frontend_dist: Path | str | None = None) -> FastAPI:
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    index_path = runs_index.default_index_path(runs_dir)
    runs_index.reconcile(runs_dir, index_path=index_path)

    app = FastAPI(title="stolgo UI", version="1")

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        items = []
        warnings = 0
        for manifest in runs_index.list_runs(index_path=index_path, kind="run"):
            try:
                manifest = _load_manifest_from_row(
                    manifest,
                    expected_kind="run",
                    runs_dir=runs_dir,
                )
                items.append(adapters.run_summary(manifest))
            except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError):
                warnings += 1
        return {"items": items, "warnings": warnings}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        return {
            "id": manifest["run_id"],
            "strategy": manifest["strategy"],
            "params": manifest.get("params", {}),
            "metrics": adapters.metric_cards(manifest.get("metrics", {})),
            "rawMetrics": manifest.get("metrics", {}),
            "created_at": manifest.get("created_at"),
        }

    @app.get("/api/runs/{run_id}/series")
    def get_run_series(run_id: str) -> dict[str, Any]:
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        parquet_dir = Path(manifest["path"]) / "parquet"
        try:
            ohlcv = pd.read_parquet(parquet_dir / "ohlcv.parquet")
            equity = pd.read_parquet(parquet_dir / "equity.parquet")["equity"]
            drawdown = pd.read_parquet(parquet_dir / "drawdown.parquet")["drawdown"]
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"run series unavailable: {exc}") from exc
        return adapters.series(ohlcv, equity, drawdown)

    @app.get("/api/runs/{run_id}/trades")
    def get_run_trades(run_id: str) -> list[dict[str, Any]]:
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        try:
            trades_df = pd.read_parquet(Path(manifest["path"]) / "parquet" / "trades.parquet")
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"run trades unavailable: {exc}") from exc
        return adapters.trades(trades_df)

    @app.get("/api/sweeps")
    def list_sweeps() -> dict[str, Any]:
        items = []
        warnings = 0
        for manifest in runs_index.list_runs(index_path=index_path, kind="sweep"):
            try:
                manifest = _load_manifest_from_row(
                    manifest,
                    expected_kind="sweep",
                    runs_dir=runs_dir,
                )
                items.append(
                    {
                        "id": manifest["run_id"],
                        "strategy": manifest.get("strategy", "Unknown"),
                        "param_grid": manifest.get("param_grid", {}),
                        "created_at": manifest.get("created_at"),
                        "path": manifest.get("path"),
                    }
                )
            except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError):
                warnings += 1
        return {"items": items, "warnings": warnings}

    @app.get("/api/sweeps/{sweep_id}")
    def get_sweep(sweep_id: str) -> dict[str, Any]:
        manifest = _manifest_for_id(sweep_id, index_path=index_path, expected_kind="sweep")
        try:
            rows = pd.read_parquet(Path(manifest["path"]) / "results.parquet").to_dict("records")
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"sweep results unavailable: {exc}") from exc
        return {
            "id": manifest["run_id"],
            "strategy": manifest.get("strategy", "Unknown"),
            "param_grid": manifest.get("param_grid", {}),
            "rows": rows,
        }

    dist = Path(frontend_dist) if frontend_dist is not None else _default_frontend_dist()
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app


def _default_frontend_dist() -> Path:
    return Path(__file__).resolve().parents[3] / "frontend" / "dist"


def _load_manifest_from_row(
    manifest: dict[str, Any],
    *,
    expected_kind: str,
    runs_dir: Path,
) -> dict[str, Any]:
    run_path = _safe_run_path(manifest, runs_dir=runs_dir)
    manifest_path = run_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    loaded = json.loads(manifest_path.read_text())
    _safe_run_path(loaded, runs_dir=runs_dir)
    _validate_manifest(loaded, expected_kind=expected_kind)
    return loaded


def _manifest_for_id(
    run_id: str,
    *,
    index_path: Path,
    expected_kind: str,
) -> dict[str, Any]:
    manifest = runs_index.get_manifest(run_id, index_path=index_path)
    if manifest is None or manifest.get("kind") != expected_kind:
        raise HTTPException(status_code=404, detail=f"{expected_kind} not found: {run_id}")
    try:
        return _load_manifest_from_row(
            manifest,
            expected_kind=expected_kind,
            runs_dir=index_path.parent,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"manifest missing: {run_id}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=409, detail=f"manifest unreadable: {run_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _validate_manifest(manifest: dict[str, Any], *, expected_kind: str) -> None:
    version = int(manifest.get("schema_version", 0))
    if version > SUPPORTED_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version {version}")
    if manifest.get("kind") != expected_kind:
        raise ValueError(f"expected {expected_kind}, got {manifest.get('kind')}")


def _safe_run_path(manifest: dict[str, Any], *, runs_dir: Path) -> Path:
    run_path = Path(manifest["path"]).resolve()
    root = runs_dir.resolve()
    if not run_path.is_relative_to(root):
        raise ValueError(f"manifest path outside runs_dir: {manifest.get('run_id')}")
    return run_path
