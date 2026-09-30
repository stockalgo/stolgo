"""DuckDB-backed materialized index for exported stolgo runs."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger("stolgo.ui.index")

SCHEMA_VERSION = 2
_DB_LOCK = threading.Lock()


DDL = """
CREATE TABLE IF NOT EXISTS runs_index (
  schema_version INTEGER,
  run_id VARCHAR PRIMARY KEY,
  kind VARCHAR,
  strategy VARCHAR,
  name VARCHAR,
  status VARCHAR,
  group_id VARCHAR,
  summary JSON,
  params JSON,
  metrics JSON,
  created_at TIMESTAMP,
  path VARCHAR,
  mtime DOUBLE
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
            # Check existing tables
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
            if "runs_index" in tables:
                cols = [row[1] for row in con.execute("PRAGMA table_info('runs_index')").fetchall()]
                # If table is v1 (missing 'summary' or 'name' or 'status')
                if "summary" not in cols or "name" not in cols or "status" not in cols:
                    con.execute("DROP TABLE runs_index")
            con.execute(DDL)
        finally:
            con.close()


def upsert_run(
    manifest: dict[str, Any],
    index_path: Path | str = default_index_path(),
    mtime: float | None = None,
) -> None:
    index_path = Path(index_path)
    ensure_schema(index_path)

    schema_ver = int(manifest.get("schema_version", SCHEMA_VERSION))
    run_id = str(manifest["run_id"])
    kind = str(manifest.get("kind", "run"))
    strategy = str(manifest.get("strategy", manifest.get("name", "Unknown")))
    name = str(manifest.get("name", manifest.get("strategy", run_id)))
    status = str(manifest.get("status", "ok" if schema_ver == 2 else "not_migrated"))

    group = manifest.get("group")
    group_id = group.get("id") if isinstance(group, dict) else None

    summary_json = None
    if schema_ver == 2 and kind == "run":
        from stolgo.ui.adapters import run_summary_v2

        summary_json = json.dumps(run_summary_v2(manifest), default=str)

    params = manifest.get("params", manifest.get("param_grid", {}))
    metrics = manifest.get("metrics", {})
    created_at = manifest.get("created_at")
    path_val = str(manifest.get("path", ""))

    row = (
        schema_ver,
        run_id,
        kind,
        strategy,
        name,
        status,
        group_id,
        summary_json,
        json.dumps(params, default=str),
        json.dumps(metrics, default=str),
        created_at,
        path_val,
        float(mtime) if mtime is not None else None,
    )
    with _DB_LOCK:
        con = duckdb.connect(str(index_path))
        try:
            con.execute(
                """
                INSERT INTO runs_index
                  (schema_version, run_id, kind, strategy, name, status, group_id, summary, params, metrics, created_at, path, mtime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?::JSON, ?::JSON, ?::JSON, ?, ?, ?)
                ON CONFLICT (run_id) DO UPDATE SET
                  schema_version = excluded.schema_version,
                  kind = excluded.kind,
                  strategy = excluded.strategy,
                  name = excluded.name,
                  status = excluded.status,
                  group_id = excluded.group_id,
                  summary = excluded.summary,
                  params = excluded.params,
                  metrics = excluded.metrics,
                  created_at = excluded.created_at,
                  path = excluded.path,
                  mtime = excluded.mtime
                """,
                row,
            )
        finally:
            con.close()


def reconcile(runs_dir: Path | str = Path("runs"), index_path: Path | str | None = None) -> None:
    runs_dir = Path(runs_dir)
    index_path = Path(index_path) if index_path is not None else default_index_path(runs_dir)
    ensure_schema(index_path)

    existing_mtimes: dict[str, float] = {}
    with _DB_LOCK:
        con = duckdb.connect(str(index_path))
        try:
            rows = con.execute("SELECT run_id, mtime FROM runs_index").fetchall()
            existing_mtimes = {row[0]: row[1] for row in rows if row[1] is not None}
        finally:
            con.close()

    for manifest_path in runs_dir.glob("*/manifest.json"):
        parent_name = manifest_path.parent.name
        if parent_name.endswith(".tmp") or parent_name.startswith("_"):
            continue
        try:
            cur_mtime = manifest_path.stat().st_mtime
            if existing_mtimes.get(parent_name) == cur_mtime:
                continue
            manifest = json.loads(manifest_path.read_text())
            upsert_run(manifest, index_path=index_path, mtime=cur_mtime)
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to reconcile run %s: %s", parent_name, exc)
            continue


def list_runs(
    *,
    index_path: Path | str = default_index_path(),
    kind: str | None = None,
) -> list[dict[str, Any]]:
    index_path = Path(index_path)
    if not index_path.exists():
        return []
    query = (
        "SELECT schema_version, run_id, kind, strategy, name, status, group_id, "
        "summary, params, metrics, created_at, path FROM runs_index"
    )
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
                SELECT schema_version, run_id, kind, strategy, name, status, group_id,
                       summary, params, metrics, created_at, path
                FROM runs_index
                WHERE run_id = ?
                """,
                [run_id],
            ).fetchone()
        finally:
            con.close()
    return _row_to_manifest(row) if row else None


def _row_to_manifest(row: tuple[Any, ...]) -> dict[str, Any]:
    created_at = row[10].isoformat() if hasattr(row[10], "isoformat") else row[10]
    return {
        "schema_version": int(row[0]),
        "run_id": row[1],
        "kind": row[2],
        "strategy": row[3],
        "name": row[4],
        "status": row[5],
        "group_id": row[6],
        "summary": json.loads(row[7]) if row[7] else None,
        "params": json.loads(row[8]) if row[8] else {},
        "metrics": json.loads(row[9]) if row[9] else {},
        "created_at": created_at,
        "path": row[11],
    }
