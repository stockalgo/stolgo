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
    equity = pd.Series([100.0, 105.0, 102.0], index=index)
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
            "tag": ["exit"],
        }
    )
    positions = pd.DataFrame({"qty": [0.0, 1.0, 0.0], "equity": equity}, index=index)
    return RunResult(
        params={"symbol": "SYN", "interval": "1d"},
        trades=trades,
        equity=equity,
        positions=positions,
        signals=pd.DataFrame(),
        ohlcv=ohlcv,
    )


def _client(tmp_path: Path) -> TestClient:
    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="TrendBreakout")
    export_sweep(
        pd.DataFrame({"period": [10], "sharpe": [1.2]}),
        runs_dir / "sweep-1",
        param_grid={"period": [10]},
        strategy_name="SmaTrend",
    )
    return TestClient(create_app(runs_dir))


def test_read_only_endpoints_return_adapter_shapes(tmp_path) -> None:
    client = _client(tmp_path)

    runs = client.get("/api/runs").json()
    assert runs["warnings"] == 0
    assert runs["items"][0]["id"] == "run-1"

    detail = client.get("/api/runs/run-1").json()
    assert detail["strategy"] == "TrendBreakout"
    assert all(set(card) == {"key", "label", "value", "fmt"} for card in detail["metrics"])

    series = client.get("/api/runs/run-1/series").json()
    assert set(series) == {"candles", "volume", "equity", "drawdown"}
    assert isinstance(series["candles"][0]["time"], int)

    trades = client.get("/api/runs/run-1/trades").json()
    assert trades[0]["side"] == "Long"

    sweeps = client.get("/api/sweeps").json()
    assert sweeps["items"][0]["id"] == "sweep-1"

    sweep = client.get("/api/sweeps/sweep-1").json()
    assert sweep["param_grid"] == {"period": [10]}
    assert sweep["rows"] == [{"period": 10, "sharpe": 1.2}]


def test_error_contract_404_409_and_list_warnings(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="TrendBreakout")
    client = TestClient(create_app(runs_dir))

    assert client.get("/api/runs/missing").status_code == 404

    (runs_dir / "run-1" / "parquet" / "ohlcv.parquet").unlink()
    assert client.get("/api/runs/run-1/series").status_code == 409

    bad_dir = runs_dir / "bad"
    bad_dir.mkdir()
    bad_manifest = {
        "schema_version": 99,
        "run_id": "bad",
        "kind": "run",
        "strategy": "Future",
        "params": {},
        "metrics": {},
        "created_at": "2026-07-06T10:00:00+00:00",
        "path": str(bad_dir),
    }
    (bad_dir / "manifest.json").write_text(json.dumps(bad_manifest))
    client = TestClient(create_app(runs_dir))
    listing = client.get("/api/runs").json()
    assert listing["warnings"] == 1


def test_manifest_path_must_stay_inside_runs_dir(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    export_all(_result(), runs_dir / "run-1", strategy_name="TrendBreakout")
    manifest_path = runs_dir / "run-1" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["path"] = str(tmp_path / "outside")
    manifest_path.write_text(json.dumps(manifest))

    client = TestClient(create_app(runs_dir))

    assert client.get("/api/runs").json()["warnings"] == 1
    response = client.get("/api/runs/run-1")
    assert response.status_code == 409
    assert "outside runs_dir" in response.json()["detail"]
