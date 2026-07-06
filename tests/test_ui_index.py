"""Tests for the UI run index."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from stolgo.ui import index


def _manifest(root: Path, run_id: str, kind: str) -> dict:
    path = root / run_id
    path.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "kind": kind,
        "strategy": "TrendBreakout" if kind == "run" else "SmaTrend",
        "params": {"symbol": "SYN", "interval": "1d"},
        "metrics": {"total_return": 0.1, "sharpe": 1.2, "max_drawdown": -0.05, "num_trades": 3}
        if kind == "run"
        else {},
        "created_at": "2026-07-06T10:00:00+00:00",
        "path": str(path),
    }
    if kind == "sweep":
        manifest["param_grid"] = {"period": [10, 20]}
    (path / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def test_upsert_and_reconcile_rebuild_counts(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    index_path = index.default_index_path(runs_dir)
    m1 = _manifest(runs_dir, "run-1", "run")
    m2 = _manifest(runs_dir, "run-2", "run")
    m3 = _manifest(runs_dir, "sweep-1", "sweep")

    index.upsert_run(m1, index_path=index_path)
    index.upsert_run(m2, index_path=index_path)
    index.upsert_run(m3, index_path=index_path)

    con = duckdb.connect(str(index_path), read_only=True)
    try:
        counts = dict(con.execute("SELECT kind, count(*) FROM runs_index GROUP BY kind").fetchall())
    finally:
        con.close()
    assert counts == {"run": 2, "sweep": 1}

    index_path.unlink()
    index.reconcile(runs_dir)

    con = duckdb.connect(str(index_path), read_only=True)
    try:
        rebuilt = dict(con.execute("SELECT kind, count(*) FROM runs_index GROUP BY kind").fetchall())
    finally:
        con.close()
    assert rebuilt == {"run": 2, "sweep": 1}


def test_list_runs_and_get_manifest_roundtrip_json(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    index_path = index.default_index_path(runs_dir)
    manifest = _manifest(runs_dir, "run-1", "run")
    index.upsert_run(manifest, index_path=index_path)

    listed = index.list_runs(index_path=index_path, kind="run")
    assert len(listed) == 1
    assert listed[0]["params"]["symbol"] == "SYN"
    assert listed[0]["metrics"]["sharpe"] == 1.2
    assert index.get_manifest("run-1", index_path=index_path)["run_id"] == "run-1"
    assert index.get_manifest("missing", index_path=index_path) is None


def test_reconcile_skips_tmp_directories(tmp_path) -> None:
    runs_dir = tmp_path / "runs"
    _manifest(runs_dir, "complete", "run")
    _manifest(runs_dir, "in-progress.tmp", "run")

    index.reconcile(runs_dir)

    listed = index.list_runs(index_path=index.default_index_path(runs_dir), kind="run")
    assert [row["run_id"] for row in listed] == ["complete"]
