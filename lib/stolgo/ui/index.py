"""DuckDB-backed materialized index for exported stolgo runs."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import duckdb


SCHEMA_VERSION = 1
_DB_LOCK = threading.Lock()


DDL = """
CREATE TABLE IF NOT EXISTS runs_index (
  schema_version INTEGER,
  run_id VARCHAR PRIMARY KEY,
  kind VARCHAR,
  strategy VARCHAR,
  params JSON,
  metrics JSON,
  created_at TIMESTAMP,
  path VARCHAR
);
"""


def default_index_path(runs_dir: Path | str = Path("runs")) -> Path:
    return Path(runs_dir) / "_index.duckdb"


def ensure_schema(index_path: Path | str = default_index_path()) -> None:
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with _DB_LOCK:
        con = duckdb.connect(str(index_path))
        try:
            con.execute(DDL)
        finally:
            con.close()


def upsert_run(manifest: dict[str, Any], index_path: Path | str = default_index_path()) -> None:
    index_path = Path(index_path)
    ensure_schema(index_path)
    params = manifest.get("params", manifest.get("param_grid", {}))
    metrics = manifest.get("metrics", {})
    row = (
        int(manifest.get("schema_version", SCHEMA_VERSION)),
        str(manifest["run_id"]),
        str(manifest["kind"]),
        str(manifest.get("strategy", "Unknown")),
        json.dumps(params, default=str),
        json.dumps(metrics, default=str),
        manifest.get("created_at"),
        str(manifest["path"]),
    )
    with _DB_LOCK:
        con = duckdb.connect(str(index_path))
        try:
            con.execute(
                """
                INSERT INTO runs_index
                  (schema_version, run_id, kind, strategy, params, metrics, created_at, path)
                VALUES (?, ?, ?, ?, ?::JSON, ?::JSON, ?, ?)
                ON CONFLICT (run_id) DO UPDATE SET
                  schema_version = excluded.schema_version,
                  kind = excluded.kind,
                  strategy = excluded.strategy,
                  params = excluded.params,
                  metrics = excluded.metrics,
                  created_at = excluded.created_at,
                  path = excluded.path
                """,
                row,
            )
        finally:
            con.close()


def reconcile(runs_dir: Path | str = Path("runs"), index_path: Path | str | None = None) -> None:
    runs_dir = Path(runs_dir)
    index_path = Path(index_path) if index_path is not None else default_index_path(runs_dir)
    ensure_schema(index_path)
    for manifest_path in runs_dir.glob("*/manifest.json"):
        if manifest_path.parent.name.endswith(".tmp"):
            continue
        manifest = json.loads(manifest_path.read_text())
        upsert_run(manifest, index_path=index_path)


def list_runs(
    *,
    index_path: Path | str = default_index_path(),
    kind: str | None = None,
) -> list[dict[str, Any]]:
    index_path = Path(index_path)
    if not index_path.exists():
        return []
    query = "SELECT schema_version, run_id, kind, strategy, params, metrics, created_at, path FROM runs_index"
    params: list[Any] = []
    if kind is not None:
        query += " WHERE kind = ?"
        params.append(kind)
    query += " ORDER BY created_at DESC"
    with _DB_LOCK:
        con = duckdb.connect(str(index_path), read_only=True)
        try:
            rows = con.execute(query, params).fetchall()
        finally:
            con.close()
    return [_row_to_manifest(row) for row in rows]


def get_manifest(run_id: str, *, index_path: Path | str = default_index_path()) -> dict[str, Any] | None:
    index_path = Path(index_path)
    if not index_path.exists():
        return None
    with _DB_LOCK:
        con = duckdb.connect(str(index_path), read_only=True)
        try:
            row = con.execute(
                """
                SELECT schema_version, run_id, kind, strategy, params, metrics, created_at, path
                FROM runs_index
                WHERE run_id = ?
                """,
                [run_id],
            ).fetchone()
        finally:
            con.close()
    return _row_to_manifest(row) if row else None


def _row_to_manifest(row: tuple[Any, ...]) -> dict[str, Any]:
    created_at = row[6].isoformat() if hasattr(row[6], "isoformat") else row[6]
    return {
        "schema_version": int(row[0]),
        "run_id": row[1],
        "kind": row[2],
        "strategy": row[3],
        "params": json.loads(row[4]) if row[4] else {},
        "metrics": json.loads(row[5]) if row[5] else {},
        "created_at": created_at,
        "path": row[7],
    }
