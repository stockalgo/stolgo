"""Tests for the read-only UI API."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from stolgo.report.exporters import export_all, export_sweep
from stolgo.report.result import RunResult
from stolgo.ui.server import create_app


def _result() -> RunResult:
    index = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    equity = pd.Series([100.0, 101.0, 101.0], index=index)
    ohlcv = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [12.0, 13.0, 14.0],
            "low": [9.0, 10.0, 11.0],
            "close": [11.0, 12.0, 12.5],
            "volume": [100.0, 120.0, 130.0],
        },
        index=index,
    )
    trades = pd.DataFrame(
        {
            "entry_ts": [index[0]],
            "exit_ts": [index[1]],
            "entry_price": [11.0],
            "exit_price": [12.0],
            "qty": [1.0],
            "net_pnl": [1.0],
            "side": ["BUY"],
            "tag": ["exit"],
        }
    )
    positions = pd.DataFrame({"qty": [0.0, 1.0, 0.0], "equity": equity}, index=index)
    return RunResult(
        params={"symbol": "SYN", "interval": "1d", "cash": 100.0},
        trades=trades,
        equity=equity,
        positions=positions,
        signals=pd.DataFrame(),
        ohlcv=ohlcv,
    )


def _client(tmp_path: Path) -> TestClient:
    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="TrendBreakout")
    # Add a mock group to run-1's manifest for group endpoint testing
    m_path = runs_dir / "run-1" / "manifest.json"
    manifest = json.loads(m_path.read_text())
    manifest["group"] = {"id": "test-group", "label": "Test Group", "axes": {"market": "SYN", "dte": 0}}
    manifest["has"]["intraday_equity"] = True
    m_path.write_text(json.dumps(manifest))

    export_sweep(
        pd.DataFrame({"period": [10], "sharpe": [1.2]}),
        runs_dir / "sweep-1",
        param_grid={"period": [10]},
        strategy_name="SmaTrend",
    )
    (runs_dir / "_migration_report.md").write_text("# Mock Migration Report")
    return TestClient(create_app(runs_dir))


def test_api_v2_endpoints(tmp_path: Path) -> None:
    client = _client(tmp_path)

    # 4.1 GET /api/runs
    runs = client.get("/api/runs").json()
    assert runs["warnings"] == 0
    assert len(runs["items"]) == 1
    summary = runs["items"][0]
    expected_summary_keys = {
        "id",
        "name",
        "status",
        "status_reasons",
        "markets",
        "structure",
        "dte",
        "group",
        "window",
        "capital",
        "metrics",
        "robustness",
        "data_quality",
        "has",
        "created_at",
    }
    assert expected_summary_keys.issubset(set(summary.keys()))

    # 4.2 GET /api/runs/{id}
    detail = client.get("/api/runs/run-1").json()
    assert detail["id"] == "run-1"
    assert "instrument" in detail
    assert "config" in detail
    assert "metric_defs" in detail
    assert any(m["key"] == "sharpe" for m in detail["metric_defs"])

    # 4.3 GET /api/runs/{id}/daily
    daily = client.get("/api/runs/run-1/daily").json()
    assert "rows" in daily
    assert len(daily["rows"]) > 0
    assert set(daily["rows"][0].keys()) >= {"session", "pnl", "equity", "drawdown", "trades_closed"}

    # 4.4 GET /api/runs/{id}/monthly
    monthly = client.get("/api/runs/run-1/monthly").json()
    assert "rows" in monthly
    assert len(monthly["rows"]) > 0
    assert set(monthly["rows"][0].keys()) >= {"month", "pnl", "return_pct", "trades"}

    # 4.5 GET /api/runs/{id}/trades
    trades_resp = client.get("/api/runs/run-1/trades").json()
    assert "rows" in trades_resp and "columns" in trades_resp
    assert len(trades_resp["rows"]) == 1
    trade_id = trades_resp["rows"][0]["trade_id"]
    assert isinstance(trades_resp["rows"][0]["entry_ts"], int)

    # 4.6 GET /api/runs/{id}/trades/{trade_id}
    t_detail = client.get(f"/api/runs/run-1/trades/{trade_id}").json()
    assert set(t_detail.keys()) == {"trade", "legs", "bars"}
    assert t_detail["trade"]["trade_id"] == trade_id
    assert client.get("/api/runs/run-1/trades/999").status_code == 404

    # 4.7 GET /api/runs/{id}/candles
    candles = client.get("/api/runs/run-1/candles?tf=1D").json()
    assert "rows" in candles and candles["tf"] == "1D"
    assert len(candles["rows"]) > 0

    # 4.8 GET /api/runs/{id}/equity
    eq = client.get("/api/runs/run-1/equity").json()
    assert "rows" in eq
    assert len(eq["rows"]) > 0

    # 4.9 GET /api/groups and /api/groups/{id}
    groups = client.get("/api/groups").json()
    assert len(groups["items"]) == 1
    assert groups["items"][0]["id"] == "test-group"
    assert groups["items"][0]["axes"] == {"dte": [0], "market": ["SYN"]}

    grp_detail = client.get("/api/groups/test-group").json()
    assert grp_detail["id"] == "test-group"
    assert len(grp_detail["runs"]) == 1

    # 4.10 GET /api/migration-report
    rep = client.get("/api/migration-report")
    assert rep.status_code == 200
    assert "# Mock Migration Report" in rep.text

    # 4.11 GET /api/runs/{id}/audit
    assert client.get("/api/runs/run-1/audit").status_code == 404

    # 4.12 GET /api/sweeps and /api/sweeps/{id}
    sweeps = client.get("/api/sweeps").json()
    assert len(sweeps["items"]) == 1
    assert sweeps["items"][0]["id"] == "sweep-1"
    assert sweeps["items"][0]["strategy"] == "SmaTrend"

    sweep_detail = client.get("/api/sweeps/sweep-1").json()
    assert sweep_detail["id"] == "sweep-1"
    assert sweep_detail["strategy"] == "SmaTrend"
    assert len(sweep_detail["rows"]) == 1
    assert sweep_detail["rows"][0]["period"] == 10


def test_v1_run_returns_409_and_warning(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    v1_dir = runs_dir / "v1-run"
    v1_dir.mkdir(parents=True)
    v1_manifest = {
        "schema_version": 1,
        "run_id": "v1-run",
        "kind": "run",
        "strategy": "Old",
        "params": {},
        "metrics": {},
        "created_at": "2026-01-01T00:00:00+00:00",
        "path": str(v1_dir),
    }
    (v1_dir / "manifest.json").write_text(json.dumps(v1_manifest))

    client = TestClient(create_app(runs_dir))

    # /api/runs excludes v1 runs with warnings += 1
    runs = client.get("/api/runs").json()
    assert runs["warnings"] == 1
    assert len(runs["items"]) == 0

    # Detail endpoints return 409 {"detail":"run_not_migrated", "hint": "..."}
    for ep in ["/api/runs/v1-run", "/api/runs/v1-run/daily", "/api/runs/v1-run/trades"]:
        res = client.get(ep)
        assert res.status_code == 409
        data = res.json()
        assert data["detail"] == "run_not_migrated"
        assert "python scripts/migrate_runs_v2.py" in data["hint"]


def test_audit_report_security(tmp_path: Path) -> None:
    client = _client(tmp_path)
    runs_dir = tmp_path / "runs"

    report = runs_dir / "run-1" / "audit.html"
    report.write_text("<h1>Audit</h1>")
    assert client.get("/api/runs/run-1/audit").status_code == 200

    report.unlink()
    outside = tmp_path / "outside.html"
    outside.write_text("outside")
    report.symlink_to(outside)
    assert client.get("/api/runs/run-1/audit").status_code == 409


def test_error_contracts_and_sweeps(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/groups/missing-group").status_code == 404

    sweeps = client.get("/api/sweeps").json()
    assert sweeps["items"][0]["id"] == "sweep-1"

    sweep = client.get("/api/sweeps/sweep-1").json()
    assert sweep["rows"] == [{"period": 10, "sharpe": 1.2}]


def test_spa_fallback_serves_index_html(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="TrendBreakout")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<!doctype html><html><body>Stolgo</body></html>")
    (dist_dir / "assets").mkdir()
    (dist_dir / "assets" / "style.css").write_text("body { color: red; }")

    app = create_app(runs_dir, frontend_dist=dist_dir)
    client = TestClient(app)

    # Root serves index.html
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "Stolgo" in root_res.text

    # Deep-linked client-side route serves index.html
    deep_res = client.get("/runs/run-1")
    assert deep_res.status_code == 200
    assert "Stolgo" in deep_res.text

    # Static asset served
    asset_res = client.get("/assets/style.css")
    assert asset_res.status_code == 200
    assert "color: red" in asset_res.text

    # Unknown API route still returns 404, not index.html
    api_res = client.get("/api/unknown")
    assert api_res.status_code == 404


def test_spa_fallback_rejects_paths_outside_dist(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("Stolgo")
    outside = tmp_path / "private.txt"
    outside.write_text("private content")
    (dist / "linked.txt").symlink_to(outside)
    client = TestClient(create_app(tmp_path / "runs", frontend_dist=dist))
    for path in ["/..%2fprivate.txt", "/linked.txt"]:
        response = client.get(path)
        assert response.status_code == 404
        assert "private content" not in response.text


def test_library_refreshes_edited_and_deleted_runs(tmp_path: Path) -> None:
    import shutil

    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="InitialName")
    client = TestClient(create_app(runs_dir))
    manifest_path = runs_dir / "run-1" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["name"] = "UpdatedName"
    manifest_path.write_text(json.dumps(manifest))
    assert client.get("/api/runs").json()["items"][0]["name"] == "UpdatedName"
    shutil.rmtree(runs_dir / "run-1")
    assert client.get("/api/runs").json()["items"] == []


def test_dynamic_reconcile_on_runs_dir_change(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="TrendBreakout")

    app = create_app(runs_dir)
    client = TestClient(app)

    res = client.get("/api/runs").json()
    assert len(res["items"]) == 1
    assert res["items"][0]["id"] == "run-1"

    # Export a second run after app creation
    export_all(_result(), runs_dir / "run-2", strategy_name="SecondStrat")

    # Next request dynamically detects the new run without restarting
    res2 = client.get("/api/runs").json()
    assert len(res2["items"]) == 2
    ids = {item["id"] for item in res2["items"]}
    assert ids == {"run-1", "run-2"}


def test_dynamic_reconcile_on_manifest_mtime_change(tmp_path: Path) -> None:
    import os
    import time
    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="InitialName")

    app = create_app(runs_dir)
    client = TestClient(app)

    detail1 = client.get("/api/runs/run-1").json()
    assert detail1["name"] == "InitialName"

    runs_dir_mtime = runs_dir.stat().st_mtime_ns

    time.sleep(0.01)
    manifest_path = runs_dir / "run-1" / "manifest.json"
    manifest_data = json.loads(manifest_path.read_text())
    manifest_data["name"] = "UpdatedName"
    manifest_path.write_text(json.dumps(manifest_data, indent=2))
    os.utime(runs_dir, ns=(runs_dir_mtime, runs_dir_mtime))

    detail2 = client.get("/api/runs/run-1").json()
    assert detail2["name"] == "UpdatedName"

