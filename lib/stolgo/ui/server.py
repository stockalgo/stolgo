"""Read-only FastAPI server for exported stolgo runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from stolgo.ui import adapters
from stolgo.ui import index as runs_index


SUPPORTED_SCHEMA_VERSION = 2
NOT_MIGRATED = {"detail": "run_not_migrated", "hint": "python scripts/migrate_runs_v2.py"}


def _check_migrated(manifest: dict[str, Any]) -> JSONResponse | None:
    if int(manifest.get("schema_version", 0)) < 2:
        return JSONResponse(status_code=409, content=NOT_MIGRATED)
    return None


def create_app(runs_dir: Path | str = Path("runs"), frontend_dist: Path | str | None = None) -> FastAPI:
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    index_path = runs_index.default_index_path(runs_dir)
    runs_index.reconcile(runs_dir, index_path=index_path)

    app = FastAPI(title="stolgo UI", version="2")

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        items = []
        warnings = 0
        for manifest_row in runs_index.list_runs(index_path=index_path, kind="run"):
            try:
                manifest = _load_manifest_from_row(
                    manifest_row,
                    expected_kind="run",
                    runs_dir=runs_dir,
                )
                if int(manifest.get("schema_version", 0)) < 2:
                    warnings += 1
                    continue
                items.append(adapters.run_summary_v2(manifest))
            except Exception:
                warnings += 1
        return {"items": items, "warnings": warnings}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        if err := _check_migrated(manifest):
            return err
        return adapters.run_detail_v2(manifest)

    @app.get("/api/runs/{run_id}/daily")
    def get_run_daily(run_id: str):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        if err := _check_migrated(manifest):
            return err
        daily_path = Path(manifest["path"]) / "parquet" / "daily.parquet"
        if not daily_path.is_file():
            raise HTTPException(status_code=409, detail="daily series unavailable")
        daily_df = pd.read_parquet(daily_path)
        return adapters.daily_rows(daily_df)

    @app.get("/api/runs/{run_id}/monthly")
    def get_run_monthly(run_id: str):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        if err := _check_migrated(manifest):
            return err
        daily_path = Path(manifest["path"]) / "parquet" / "daily.parquet"
        if not daily_path.is_file():
            raise HTTPException(status_code=409, detail="daily series unavailable")
        daily_df = pd.read_parquet(daily_path)
        capital = manifest.get("config", {}).get("capital", 0.0)
        return adapters.monthly_rows(daily_df, capital)

    @app.get("/api/runs/{run_id}/trades")
    def get_run_trades(run_id: str):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        if err := _check_migrated(manifest):
            return err
        trades_path = Path(manifest["path"]) / "parquet" / "trades.parquet"
        if not trades_path.is_file():
            raise HTTPException(status_code=409, detail="run trades unavailable")
        trades_df = pd.read_parquet(trades_path)
        return adapters.trades_v2_rows(trades_df)

    @app.get("/api/runs/{run_id}/trades/{trade_id}")
    def get_run_trade_detail(run_id: str, trade_id: int):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        if err := _check_migrated(manifest):
            return err
        run_dir = Path(manifest["path"])
        trades_path = run_dir / "parquet" / "trades.parquet"
        if not trades_path.is_file():
            raise HTTPException(status_code=409, detail="run trades unavailable")
        trades_df = pd.read_parquet(trades_path)
        legs_path = run_dir / "parquet" / "legs.parquet"
        legs_df = pd.read_parquet(legs_path) if legs_path.is_file() else None
        ohlcv_path = run_dir / "parquet" / "ohlcv.parquet"
        ohlcv_df = pd.read_parquet(ohlcv_path) if ohlcv_path.is_file() else None
        try:
            return adapters.trade_detail(trades_df, legs_df, ohlcv_df, trade_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"trade {trade_id} not found")

    @app.get("/api/runs/{run_id}/candles")
    def get_run_candles(
        run_id: str,
        tf: str = "1D",
        from_date: str | None = Query(None, alias="from"),
        to_date: str | None = Query(None, alias="to"),
    ):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        if err := _check_migrated(manifest):
            return err
        ohlcv_path = Path(manifest["path"]) / "parquet" / "ohlcv.parquet"
        if not ohlcv_path.is_file():
            return JSONResponse(status_code=409, content={"detail": "no_ohlcv"})
        ohlcv_df = pd.read_parquet(ohlcv_path)
        return adapters.candles(ohlcv_df, tf=tf, frm=from_date, to=to_date)

    @app.get("/api/runs/{run_id}/equity")
    def get_run_equity(run_id: str):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        if err := _check_migrated(manifest):
            return err
        if not manifest.get("has", {}).get("intraday_equity", False):
            raise HTTPException(status_code=404, detail="no intraday equity for run")
        equity_path = Path(manifest["path"]) / "parquet" / "equity.parquet"
        if not equity_path.is_file():
            raise HTTPException(status_code=404, detail="equity file missing")
        equity_df = pd.read_parquet(equity_path)
        if "equity" in equity_df.columns:
            eq_s = equity_df["equity"]
        else:
            eq_s = equity_df.iloc[:, 0]
        rows = []
        for idx, val in eq_s.items():
            t_s = int(pd.to_datetime(idx, utc=True).timestamp())
            rows.append({"time": t_s, "equity": float(val)})
        return {"rows": adapters._clean(rows)}

    @app.get("/api/groups")
    def list_groups() -> dict[str, Any]:
        group_map: dict[str, dict[str, Any]] = {}
        for manifest_row in runs_index.list_runs(index_path=index_path, kind="run"):
            try:
                manifest = _load_manifest_from_row(
                    manifest_row,
                    expected_kind="run",
                    runs_dir=runs_dir,
                )
                if int(manifest.get("schema_version", 0)) < 2:
                    continue
            except Exception:
                continue

            grp = manifest.get("group")
            if not isinstance(grp, dict) or not grp.get("id"):
                continue
            gid = str(grp["id"])
            if gid not in group_map:
                group_map[gid] = {
                    "id": gid,
                    "label": grp.get("label", gid),
                    "runs": 0,
                    "axes_sets": {},
                }
            group_map[gid]["runs"] += 1
            axes = grp.get("axes", {})
            if isinstance(axes, dict):
                for k, v in axes.items():
                    if k not in group_map[gid]["axes_sets"]:
                        group_map[gid]["axes_sets"][k] = set()
                    if isinstance(v, list):
                        group_map[gid]["axes_sets"][k].update(v)
                    elif v is not None:
                        group_map[gid]["axes_sets"][k].add(v)

        items = []
        for gid, data in group_map.items():
            axes = {}
            for k, s in data["axes_sets"].items():
                try:
                    axes[k] = sorted(list(s))
                except TypeError:
                    axes[k] = list(s)
            items.append(
                {
                    "id": data["id"],
                    "label": data["label"],
                    "runs": data["runs"],
                    "axes": axes,
                }
            )
        return {"items": items}

    @app.get("/api/groups/{group_id}")
    def get_group(group_id: str) -> dict[str, Any]:
        group_info = None
        runs = []
        axes_sets: dict[str, set] = {}
        for manifest_row in runs_index.list_runs(index_path=index_path, kind="run"):
            try:
                manifest = _load_manifest_from_row(
                    manifest_row,
                    expected_kind="run",
                    runs_dir=runs_dir,
                )
                if int(manifest.get("schema_version", 0)) < 2:
                    continue
            except Exception:
                continue

            grp = manifest.get("group")
            if isinstance(grp, dict) and str(grp.get("id")) == group_id:
                if group_info is None:
                    group_info = {"id": group_id, "label": grp.get("label", group_id)}
                runs.append(adapters.run_summary_v2(manifest))
                for k, v in grp.get("axes", {}).items():
                    if k not in axes_sets:
                        axes_sets[k] = set()
                    if isinstance(v, list):
                        axes_sets[k].update(v)
                    elif v is not None:
                        axes_sets[k].add(v)

        if group_info is None:
            raise HTTPException(status_code=404, detail=f"group not found: {group_id}")

        axes = {}
        for k, s in axes_sets.items():
            try:
                axes[k] = sorted(list(s))
            except TypeError:
                axes[k] = list(s)

        return {
            "id": group_info["id"],
            "label": group_info["label"],
            "axes": axes,
            "runs": runs,
        }

    @app.api_route("/api/migration-report", methods=["GET", "HEAD"])
    def get_migration_report():
        report_path = (runs_dir / "_migration_report.md").resolve()
        if not report_path.is_file():
            raise HTTPException(status_code=404, detail="migration report not found")
        return FileResponse(report_path, media_type="text/markdown")

    @app.get("/api/runs/{run_id}/series")
    def get_run_series(run_id: str) -> dict[str, Any]:
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        parquet_dir = Path(manifest["path"]) / "parquet"
        try:
            ohlcv = pd.read_parquet(parquet_dir / "ohlcv.parquet")
            equity = pd.read_parquet(parquet_dir / "equity.parquet")["equity"]
            drawdown_path = parquet_dir / "drawdown.parquet"
            if drawdown_path.is_file():
                drawdown = pd.read_parquet(drawdown_path)["drawdown"]
            else:
                daily_df = pd.read_parquet(parquet_dir / "daily.parquet")
                drawdown = pd.Series(
                    (daily_df["drawdown"] * 100.0).values,
                    index=pd.to_datetime(daily_df["session"], utc=True),
                )
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"run series unavailable: {exc}") from exc
        return adapters.series(ohlcv, equity, drawdown)

    @app.get("/api/runs/{run_id}/audit")
    def get_run_audit(run_id: str):
        manifest = _manifest_for_id(run_id, index_path=index_path, expected_kind="run")
        directory = Path(manifest["path"]).resolve()
        report = (directory / "audit.html").resolve()
        if not report.is_relative_to(runs_dir.resolve()) or report.parent != directory:
            raise HTTPException(status_code=409, detail="Audit path outside run directory")
        if not report.is_file():
            raise HTTPException(status_code=404, detail="No audit report exported for this run")
        return FileResponse(report, media_type="text/html")

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
        assets_dir = dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            if full_path.startswith("api/") or full_path == "api":
                raise HTTPException(status_code=404, detail="Not found")
            file_path = dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            index_html = dist / "index.html"
            if index_html.is_file():
                return FileResponse(index_html)
            raise HTTPException(status_code=404, detail="Frontend index.html not found")

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
