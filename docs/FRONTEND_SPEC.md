# Stolgo Frontend — Spec & Implementation Plan

Companion to `HLD.md` / `IMPLEMENTATION_PLAN_BACKTEST.md`. Covers a lightweight, local
frontend for (V1) backtest/sweep visualization and (V2) live event/position
visualization once a real broker is wired in via bandl.

Stack decision (see prior discussion): **FastAPI + a single-file HTML/JS frontend
(no build step) + DuckDB as the query layer** over the existing Parquet/CSV/JSON
exports — nothing about `report/exporters.py`'s output format changes.

> **Framing correction (post-review).** DuckDB is used here as a *stateless query
> engine over files*, **not** as "the database" / a system of record. It is opened
> per-request (connection setup is microseconds), reads Parquet/JSON by glob, and
> closes — it never holds a long-lived read-write handle. This is deliberate: a
> long-held DuckDB handle is single-process, so `stolgo serve` holding one open
> would lock out a concurrent CLI backtest writing to the same tree. Statelessness
> dissolves that contention entirely. See §2.1 and §3.2. V1's system of record
> stays exactly what it is today: **files on disk**, made safe to read concurrently
> via the atomic-publish rule in §3.4.

**Build scope:** V2 (live) is explicitly out of scope to build right now — this
plan delivers V1 only (Phases 0-2, §6). V2 is not being ignored, though: every
V1 decision below (files-as-record + DuckDB query layer, the `kind`-tagged manifest
schema, the atomic-publish rule, the REST/WS split in the API surface) is chosen
so V2 slots in as additive work (Phases 3-4). One honest caveat: V2's live path
introduces a genuinely **new subsystem** — async event fan-out (in-memory pub/sub
→ WebSocket) plus a durable journal — that V1's request/response server gives no
scaffolding toward. That's "new subsystem," not "new endpoints." It's unavoidable
(and blocked on bandl streaming regardless), but it is not merely additive and the
plan says so plainly rather than implying V2 is free. Everything on the storage/read
side *is* additive if V1 adopts the §3 conventions.

---

## 1. Requirements

### 1.1 V1 — Backtest & sweep visualization

- Browse all past backtest runs (strategy, params, key metrics, created_at), sorted/filtered.
- Open a run and see: candlestick + trade markers, equity curve, drawdown, position size
  over time, trade log, full metrics panel. (Interactive superset of the current static
  `tearsheet.html`.)
- Browse sweep results: metrics table across all param combinations, sortable/filterable,
  overlaid equity curves or a parameter heatmap.
- Fast: sorting/filtering hundreds — into low thousands — of runs or sweep combos
  must stay responsive. Note the cost driver is filesystem stat/open per manifest
  file, not the (tiny) metric payloads; a glob-every-request approach degrades on a
  cold cache or a synced folder (Dropbox/iCloud), so V1 ships a materialized index
  table, not raw glob (§3.2).
- Reading the run browser while a backtest/sweep is still writing must never surface
  a partial/corrupt run — enforced by the atomic-publish rule (§3.4).
- No auth, no multi-user, no server dependency beyond the local Python process.

### 1.2 V2 — Live event/position visualization (bandl-backed)

- Real-time view of: current positions, latest quotes/bars, open orders, fill stream,
  running equity — for whichever broker bandl is configured against (Zerodha, Dhan,
  CoinDCX, etc. — broker-agnostic via the existing `BrokerAdapter` interface).
- Push-based updates (WebSocket), not polling.
- Session durability: live events persisted so a crashed/restarted UI (or backend)
  can reload "what happened this session" — this satisfies the open question already
  flagged in `HLD.md` §5.2 ("journal for resume, disconnect → backfill → resubscribe").
- Not required for V2: raw tick-level ingestion — stolgo's live mode is bar-driven
  (`on_bar`), so event rates are bounded by bar interval, not tick rate.

### 1.3 Explicit non-goals (both versions)

- No authentication/multi-tenancy.
- No client-server DB (Postgres/Mongo/Influx) — adds ops burden this tool doesn't
  need. Storage is files-on-disk + an embedded DuckDB query/index layer only.
- No frontend build step (no npm/webpack/React) — plain HTML/JS/CSS, libraries via CDN.
- No raw tick storage/analytics.

---

## 2. Architecture

```
stolgo run/sweep  →  export_all() / export_sweep()  →  runs/<id>/ (parquet+csv+json+html)
                          │  (atomic publish: write <id>.tmp/ → fsync → rename → <id>/)
                          │   manifest.json written LAST = commit marker
                          ▼
                     append 1 row to index table (runs_index) at export time
                                                              │
                        FastAPI (stolgo.ui.server)            │
                          │  per-request DuckDB connection (stateless, no held handle)
                          │  - list/sort/filter  → runs_index table (materialized)
                          │  - per-run detail     → read that run's Parquet by path
                          │                    │
                     REST endpoints      WebSocket (V2 only)
                          │                    │
                        single-page frontend (static/index.html)
                          - Plotly (equity/drawdown/heatmap)
                          - TradingView lightweight-charts (candlestick + live ticks)
                          - plain table/grid (trade log, metrics, sweep comparison)
```

**Role of DuckDB (and why not glob-every-request).** DuckDB is the SQL query
engine over the file exports — it is *not* the system of record (that stays as
files on disk). Two distinct access patterns:

- **List / sort / filter across many runs** → served from a **materialized index
  table** (`runs_index`), one row per run/sweep, appended at export time. The
  earlier "just `SELECT ... FROM read_json_auto('runs/*/manifest.json')` every
  request" idea was rejected on review: it re-opens and re-parses every manifest
  on every browser hit, and the dominant cost is per-file `open`/`stat`, which
  glob cannot avoid. At hundreds that's tens of ms; into low thousands, or on a
  cold cache / cloud-synced folder, it breaks the "stay fast" requirement. The
  index is cheap to keep correct precisely because writes are append-only and go
  through our own `export_all()`/`export_sweep()`.
- **Detail for one run** → read that run's Parquet directly by its stored `path`
  (`SELECT * FROM 'runs/<id>/trades.parquet'`). No index needed; it's a single
  known file.

**Concurrency, not throughput, is why DuckDB isn't "the DB."** A single `.duckdb`
file opened read-write by one long-lived process blocks other processes from
opening it — the exact shape of "UI server up while a CLI backtest writes." We
avoid this two ways: (1) the server never holds a long-lived handle — it opens a
DuckDB connection per request and closes it; (2) the index table lives in its own
DuckDB file written only through the export path, and the server opens it
read-only. Live-event *throughput* (V2, ~1–10 events/sec, bar-driven not
tick-driven) was never the concern; concurrency semantics were.

**V2 journal — decided, not deferred.** The live event journal is **not** forced
into the analytics DuckDB file. Whether it lands in SQLite (purpose-built for many
small concurrent writes) or append-only JSONL/Parquet is a V2 implementation
choice, but it is a *separate* store from the read/analytics path by design. This
removes the previously-flagged "split to SQLite later if it hurts" escape hatch —
the split of concerns is made now; only the concrete journal backend is left open
(§7).

### 2.1 New dependencies

Add as an optional extra so the core library stays dependency-light:

```toml
[project.optional-dependencies]
ui = ["fastapi>=0.110", "uvicorn>=0.29", "duckdb>=0.10", "websockets>=12.0"]
```

`pyarrow` (currently dev-only) must become a base dependency once Parquet export
is load-bearing for the UI — it already is via `export_parquet`, so this is a
correctness fix independent of the UI work.

---

## 3. Data layer

### 3.1 Manifest — the contract, versioned and `kind`-tagged

The manifest **is** the schema — it's the denormalized index-of-record for every
artifact the UI browses. Treat it as a hard contract from day one. Every
`export_all()` writes `runs/<run_id>/manifest.json`:

```json
{
  "schema_version": 1,
  "run_id": "<RunConfig.params_hash()>-<timestamp>",
  "kind": "run",
  "strategy": "Breakout",
  "params": { "...": "RunConfig.model_dump()" },
  "created_at": "2026-07-05T10:00:00Z",
  "metrics": { "...": "RunResult.metrics — OPEN blob, key set NOT fixed" },
  "path": "runs/<run_id>/"
}
```

Three things fixed on review:

- **`schema_version`** (integer, start at `1`). The manifest is a persisted
  contract that will outlive the current code; without a version, an evolving
  library can't tell old artifacts from new. The API rejects/upgrades on version.
- **`kind` is a first-class namespace field** — `run | sweep | live_session`. All
  three share one manifest schema and one browsing surface. This is the single most
  important V2-extensibility decision: if live sessions were a *parallel* concept,
  the runs browser, `/api/runs`, and the frontend list would all fork in V2 — the
  exact rework the plan is trying to avoid. `run_id` and (V2) `session_id` live in
  the same id namespace; the browser filters by `kind`.
- **`metrics` is an open blob, never a fixed column set.** The codebase already has
  two metric producers with *different* keys (`report/metrics.py::compute_metrics`
  and `report/rmultiple_metrics.py`). The API stores/returns whatever keys exist and
  the frontend's "full metrics panel" renders keys dynamically — it must not hardcode
  a metric list or it will silently drop new metrics.

`run_id` identity note: `params_hash + timestamp` intentionally does **not** dedupe
identical re-runs — re-running the same config is a new row (we want history), and
the timestamp breaks hash collisions. Sub-second collisions are avoided by using a
monotonic/`ns` timestamp component, not whole seconds.

Sweeps get `sweeps/<sweep_id>/manifest.json` (`kind: "sweep"`, plus `param_grid`)
and `sweeps/<sweep_id>/results.parquet` (one row per combo: params + metrics —
the `parameter_sweep()` DataFrame, persisted instead of only returned in-memory).

**Code changes required:**
- `report/exporters.py`: `export_all()` additionally writes `manifest.json`
  (LAST — see §3.4) and appends the run to `runs_index` (§3.2).
- New `report/exporters.py::export_sweep(df, directory, param_grid, strategy_name)`.
- `core/sweep.py::parameter_sweep()`: no signature change; sweep persistence is a
  separate explicit call, matching the existing `Backtest(...).run()` then
  `export_all(result, ...)` pattern in `cli/main.py`.

### 3.2 Index table (materialized), not glob-per-request

A DuckDB-native index table, `runs_index`, holds one row per run/sweep so the
browser's list/sort/filter never fans out over the filesystem:

```sql
CREATE TABLE IF NOT EXISTS runs_index (
    schema_version  INTEGER,
    run_id          VARCHAR PRIMARY KEY,
    kind            VARCHAR,   -- run | sweep | live_session
    strategy        VARCHAR,
    params          JSON,
    metrics         JSON,      -- open blob, mirrors manifest
    created_at      TIMESTAMP,
    path            VARCHAR
);
```

- **Kept in sync trivially**: appended by `export_all()`/`export_sweep()` at write
  time (writes are append-only and all go through our own export path).
- **Self-healing**: on `stolgo serve` start, reconcile — glob `*/manifest.json` once
  and upsert any rows missing from the index (covers runs produced by an older stolgo
  or copied in by hand). This is the *only* time we glob-scan; steady state is a
  single indexed table read.
- **Concurrency**: written only via the export path; the server opens it read-only,
  per request, no held handle (§2 concurrency note).

Per-run *detail* still reads that run's Parquet directly by `path` — no index
involved for single-run drill-down.

### 3.3 V2 live journal (separate store, not this file)

The live event journal is a **separate** store from `runs_index` (§2 "V2 journal —
decided, not deferred"). Reference shape (backend TBD — SQLite or append-only
JSONL/Parquet):

```sql
-- e.g. if SQLite:
CREATE TABLE IF NOT EXISTS live_events (
    session_id  TEXT,
    ts          INTEGER,   -- UTC ns, matches core/types Bar.ts / Fill.ts
    event_type  TEXT,      -- bar | order | fill | signal | position_snapshot
    symbol      TEXT,
    payload     TEXT       -- JSON
);
```

Writes are batched (buffer ~1–2s or N events, flush) — bar-driven event rates
(~1–10/sec) make this comfortable regardless of the chosen backend.

### 3.4 Atomic publish — safe concurrent reads (Phase 0, not a later patch)

The #1 real-world failure mode is the UI reading a run *while it is being written*:
partial `manifest.json`, a half-flushed Parquet, a directory that exists but isn't
done. Solved by convention, in Phase 0:

1. **Write to a temp dir, then atomic rename.** `export_all()`/`export_sweep()`
   write everything to `runs/<id>.tmp/`, `fsync`, then `os.rename()` to
   `runs/<id>/`. Rename within one filesystem is atomic — the browser only ever
   sees a fully-materialized directory.
2. **`manifest.json` is written LAST and is the commit marker.** The API treats a
   run directory as readable **iff** `manifest.json` is present. In-progress or
   crashed runs (no manifest, or a lingering `.tmp/`) are simply invisible to the
   browser — no partial reads, and abandoned `.tmp/` dirs are safe to sweep.
3. **Index append happens only after the rename succeeds**, so `runs_index` never
   points at an incomplete run.

This one rule covers partial-read, crash-mid-write, and "hide in-progress runs" at
once, with no locking.

### 3.5 Field/column reference (grounded in current code — for API response shaping)

- `trades` columns: `entry_ts, exit_ts, entry_price, exit_price, qty, gross_pnl,
  net_pnl, commission, r_multiple, tag` (`report/trades.py`).
- `metrics` keys *currently* (NOT a fixed contract — render dynamically, see §3.1):
  `total_return, cagr, sharpe, sortino, calmar, mar, max_drawdown,
  max_drawdown_duration, volatility, ulcer_index, hit_rate, expectancy,
  profit_factor, payoff, avg_win, avg_loss, num_trades, exposure_pct, turnover,
  final_equity` (`report/metrics.py`) — plus a different key set from
  `report/rmultiple_metrics.py`.
- Domain types for V2 payloads: `Bar, Order, Fill, Position` (`core/types.py`),
  event envelopes `BarEvent, OrderEvent, FillEvent, SignalEvent, TimerEvent`
  (`core/events.py`).

---

## 4. Backend API (`stolgo.ui.server`, FastAPI)

| Method | Path | Returns |
|---|---|---|
| GET | `/api/runs` | list of run manifests (id, strategy, params, metrics, created_at) |
| GET | `/api/runs/{run_id}` | full detail: metrics, equity, drawdown series, ohlcv |
| GET | `/api/runs/{run_id}/trades` | trade log rows |
| GET | `/api/runs/{run_id}/positions` | position time series |
| GET | `/api/sweeps` | list of sweep manifests |
| GET | `/api/sweeps/{sweep_id}` | param grid + per-combo metrics table |
| GET | `/api/live/sessions` | (V2) past + current live session ids |
| GET | `/api/live/sessions/{id}/events` | (V2) journaled events, for reload/backfill |
| WS | `/ws/live/{session_id}` | (V2) push: bar/fill/order/position updates |

**Error / status contract** (defined in Phase 1, not discovered during frontend
debugging):
- `GET /api/runs/{id}` on a directory with no `manifest.json` → **404** (per §3.4,
  an incomplete/crashed run is "not a run"). Same for unknown id.
- Manifest present but a referenced Parquet is missing/corrupt → **409** (or `422`)
  with a machine-readable reason, not a 500 stack trace — one bad run must not break
  the whole browser.
- `schema_version` newer than the server understands → **409** with an explicit
  "artifact newer than server" message rather than silent mis-parse.
- List endpoints skip unreadable/incompatible rows and surface a `warnings[]` count
  rather than failing the whole list.

CLI integration, matching the existing `argparse` pattern in `cli/main.py`:

```
stolgo serve [--runs-dir runs] [--port 8000]
```

Launches `uvicorn` serving the FastAPI app + static frontend.

---

## 5. Frontend (`static/index.html`, single file, no build step)

- Libraries via CDN only: Plotly.js (equity/drawdown/heatmap), TradingView
  lightweight-charts (candlestick + trade markers, and later live ticks — canvas-based,
  fast), no framework.
- Dark, dense, multi-panel layout (the "terminal" aesthetic requested) — CSS grid,
  no component library.
- Views:
  1. **Runs browser** — sortable/filterable table → click through to detail.
  2. **Run detail** — candlestick+markers, equity, drawdown, position size, trade
     log table, metrics panel.
  3. **Sweep comparison** — metrics table across combos + overlaid equity curves
     or a parameter heatmap (mirrors the "parameter heatmap" already named as a
     goal in `HLD.md`).
  4. **Live (V2, stubbed in V1 build)** — positions panel, order/fill ticker,
     live equity line fed over WebSocket.

---

## 6. Phased implementation plan

**Building now: Phases 0-2 (V1 only). Phases 3-4 (V2/live) are deferred —
listed here only so Phase 0-2 decisions can be checked against them.**

**Phase 0 — foundations (no UI yet)**
1. Promote `pyarrow` from dev-only to a **base** dependency now — Parquet export is
   already load-bearing (`export_parquet`), so this is a latent correctness fix worth
   shipping independent of the UI. Add `ui` extra (`fastapi`, `uvicorn`, `duckdb`,
   `websockets`).
2. `manifest.json` with `schema_version` + `kind` (§3.1); `export_sweep()`.
3. **Atomic-publish rule (§3.4): write to `<id>.tmp/` → fsync → rename; manifest
   LAST as commit marker.** This is a Phase 0 decision, not a later hardening pass.
4. `runs_index` table + append-at-export + start-up reconcile (§3.2).
5. Adopt `runs/` / `sweeps/` as the default output root (keep `--output` override).
6. Unit tests: manifest schema + version, `export_sweep` round-trip, atomic-publish
   (reader sees no partial dir), index append + reconcile.

**Phase 1 — V1 read API**
7. `stolgo/ui/server.py`: FastAPI app, `/api/runs`, `/api/runs/{id}`,
   `/api/runs/{id}/trades`, `/api/runs/{id}/positions` — list/filter from
   `runs_index`, detail from per-run Parquet by `path`, **per-request DuckDB
   connection** (no held handle).
8. `/api/sweeps`, `/api/sweeps/{id}`.
9. Error/status contract (§4): 404 for no-manifest, 409 for corrupt/newer-version,
   `warnings[]` on list endpoints.
10. `stolgo serve` CLI command.

**Phase 2 — V1 frontend**
11. `static/index.html`: runs browser + run detail view. Explicit **empty state**
    (no runs yet → how to produce one) and **loading/error states** (a corrupt run
    renders an inline error card, not a blank screen).
12. Sweep comparison view.
13. Manual verification pass: run a real backtest + a real sweep, confirm the UI
    matches `tearsheet.html`/`summary.json` numbers exactly; and a concurrency check —
    start a long backtest, confirm the browser stays responsive and the in-progress
    run is invisible until complete.

**Phase 3 — V2 live plumbing**
11. `live_events` DuckDB table + batched writer.
12. WebSocket endpoint broadcasting from the in-memory event bus (existing
    `core/events.py` envelopes) — no DB round-trip on the hot path.
13. Wire to bandl's live broker interface (`BrokerAdapter.subscribe_bars` /
    `subscribe_fills`) once bandl ships it — currently a gap per `HLD.md` §"Broker
    capability matrix".

**Phase 4 — V2 frontend**
14. Live panel: positions, order/fill ticker, live equity.
15. Session reload/backfill from `live_events` on reconnect.

Each phase should be independently mergeable and testable; Phase 3/4 are blocked
on bandl's live broker API landing (documented gap, not something this plan can
close on its own).

---

## 7. Open risks & resolved-on-review decisions

**Resolved on review (were previously deferred / hand-waved):**
- *DuckDB concurrency* — resolved by using DuckDB statelessly (per-request
  connection, read-only index) instead of as a held-open system of record (§2, §3.2).
  No "split to SQLite if it hurts" escape hatch remains on the read path.
- *Scaling the runs list* — resolved by a materialized `runs_index` table + startup
  reconcile, not glob-per-request (§3.2).
- *Partial/concurrent reads* — resolved by atomic-publish + manifest-as-commit-marker
  (§3.4).
- *Manifest evolution* — resolved by `schema_version` and treating `metrics` as an
  open blob rendered dynamically (§3.1, §3.5).
- *V2 unified browsing* — resolved by the `kind`-tagged single manifest/id namespace
  (§3.1).

**Genuinely open:**
- **V2 live path is a new subsystem, not just new endpoints.** Async event fan-out
  (in-memory pub/sub → WebSocket, with backpressure) plus the durable journal is the
  real V2 work; V1 gives no scaffolding toward it. Called out so the "additive"
  framing isn't mistaken for "free." Blocked regardless on bandl streaming.
- **Live journal backend undecided** — SQLite vs append-only JSONL/Parquet. The
  *separation* from the analytics store is decided (§3.3); the concrete backend is a
  V2 choice.
- **bandl live streaming** (`subscribe_bars`/`subscribe_fills`) not yet implemented
  upstream — Phase 3/4 timeline depends on it landing.
- **Sweep equity overlay** — `parameter_sweep()` persists only final metrics per
  combo, not per-combo equity/trade series. Overlay-equity-curve comparison (vs.
  heatmap-only) needs that persistence added; decide before Phase 2 sweep-view work.
  Heatmap-only is the no-extra-work fallback.
