# Stolgo Frontend Wiring — Implementation Spec (package → DB → UI)

**Audience: the implementer.** This is a build sheet, not a discussion. Follow the
phases in order; each step lists exact files, signatures, data shapes, and an
acceptance check. Companion to `FRONTEND_SPEC.md` (storage-layer design) — where
this doc and the spec disagree, **this doc wins** (it reflects the built frontend).

---

## 0. Locked decisions (do not re-litigate)

1. **Series persistence is gated by an env flag, default ON.** New OHLCV/drawdown
   Parquet output is written when `STOLGO_PERSIST_SERIES` is unset or truthy
   (`1/true/yes/on`), skipped when explicitly falsy (`0/false/no/off`). Default =
   persist.
2. **Invented UI fields are OUT OF SCOPE for V1** — hidden/removed, not faked. This
   covers: Library `status` pill (Deploy/Review/Discard), metric-card `cue`/`micro`
   copy, the regime-analysis table (`regimeRows`), the Detail "recommendation/
   decision strip", and `InsightsRail`. V1 renders **only real stolgo numbers**. No
   heuristic grading in V1.
3. **Stack is React + Vite + TradingView `lightweight-charts`** (already installed
   and in use). No plain-HTML rewrite. The `FRONTEND_SPEC.md` "single static HTML,
   no build step" line is superseded — ignore it.
4. **V1 is read-only.** No `POST /api/runs` / trigger-backtest-from-UI. The "New
   backtest" page stays on mock or shows "coming soon". Deferred to a later phase.

---

## 1. Architecture & data flow

```
stolgo backtest / sweep  (Backtest(...).run() → RunResult)
      │
      ▼  export_all(result, runs/<id>/)          [SYSTEM OF RECORD = files]
      │     parquet/ohlcv.parquet      (NEW, gated by STOLGO_PERSIST_SERIES)
      │     parquet/drawdown.parquet   (NEW, gated by STOLGO_PERSIST_SERIES)
      │     parquet/equity.parquet, trades.parquet, positions.parquet  (exist)
      │     manifest.json              (NEW — written LAST = commit marker)
      │
      ▼  append 1 summary row → runs_index  (DuckDB table = the "DB")
      │
      ▼  FastAPI  stolgo/ui/server.py
      │     list/filter  ← runs_index          (never globs the filesystem)
      │     per-run detail ← that run's parquet, read by manifest.path
      │     stolgo/ui/adapters.py  reshapes stolgo → exact JSON the React app wants
      │
      ▼  React/Vite frontend  (fetch via src/data/client.js)
            charts: TradingView lightweight-charts
```

The **DB holds only the small per-run summary** (strategy, params, headline
metrics, path). Heavy arrays (ohlcv/equity/drawdown/trades) live in Parquet and are
read on demand per run. Do not load series into the DB.

---

## 2. Backend changes (Python, `lib/stolgo/`)

### 2.1 `report/exporters.py` — persist OHLCV + drawdown (gated)

Current `export_parquet` writes `trades/equity/positions`. Add `ohlcv` and
`drawdown`, both behind the env flag. `RunResult` already carries `ohlcv`
(`core/engine.py:154`) and `equity`.

Add a helper and extend `export_parquet`:

```python
import os

def _persist_series_enabled() -> bool:
    val = os.environ.get("STOLGO_PERSIST_SERIES", "1").strip().lower()
    return val not in {"0", "false", "no", "off"}

def _drawdown_from_equity(equity: "pd.Series") -> "pd.Series":
    # peak-relative drawdown in PERCENT, same basis as report/metrics.py
    peak = equity.cummax()
    return ((equity - peak) / peak.replace(0, float("nan"))) * 100.0

def export_parquet(result: RunResult, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    result.trades.to_parquet(directory / "trades.parquet", index=False)
    result.equity.to_frame("equity").to_parquet(directory / "equity.parquet")
    if not result.positions.empty:
        result.positions.to_parquet(directory / "positions.parquet")

    if _persist_series_enabled():
        if result.ohlcv is not None and not result.ohlcv.empty:
            # ohlcv: UTC DatetimeIndex, cols open/high/low/close/volume
            result.ohlcv.to_parquet(directory / "ohlcv.parquet")
        _drawdown_from_equity(result.equity).to_frame("drawdown").to_parquet(
            directory / "drawdown.parquet"
        )
```

**Acceptance**: run any example in `examples/`; confirm `parquet/ohlcv.parquet` and
`parquet/drawdown.parquet` appear; set `STOLGO_PERSIST_SERIES=0` and confirm they
do not.

### 2.2 `report/exporters.py` — manifest (written LAST) + atomic publish

Per `FRONTEND_SPEC.md` §3.1/§3.4. `export_all` must write everything into a temp
dir, then rename, writing `manifest.json` last.

```python
def _write_manifest(result: RunResult, directory: Path) -> None:
    import json, datetime as dt
    m = {
        "schema_version": 1,
        "run_id": directory.name,
        "kind": "run",
        "strategy": type(getattr(result, "strategy", None)).__name__
                    if getattr(result, "strategy", None) else result.params.get("strategy", "Unknown"),
        "params": result.params,
        "metrics": result.metrics,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "path": str(directory),
    }
    (directory / "manifest.json").write_text(json.dumps(m, indent=2, default=str))

def export_all(result: RunResult, directory: Path) -> None:
    directory = Path(directory)
    tmp = directory.with_name(directory.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    result.report.to_html(tmp / "tearsheet.html")
    export_json(result, tmp / "summary.json")
    export_csv(result, tmp / "trades.csv")
    export_parquet(result, tmp / "parquet")
    _write_manifest(result, tmp)                     # LAST inside tmp
    os.replace(tmp, directory)                        # atomic rename
```

Note: `strategy` name isn't currently on `RunResult`. Simplest fix — the CLI/caller
passes the strategy class name into `export_all` (add optional `strategy_name:
str | None = None` param and put it in the manifest). Do that rather than reflection.

**Acceptance**: `runs/<id>/manifest.json` exists, contains `schema_version`,
`kind`, `metrics`; during a long run no `runs/<id>/` appears until complete (only
`<id>.tmp/`).

### 2.3 `report/exporters.py` — `export_sweep`

`parameter_sweep()` (`core/sweep.py`) returns a DataFrame of params+metrics per
combo and persists nothing. Add:

```python
def export_sweep(df, directory: Path, *, param_grid: dict, strategy_name: str) -> None:
    directory = Path(directory)
    tmp = directory.with_name(directory.name + ".tmp")
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    df.to_parquet(tmp / "results.parquet", index=False)
    (tmp / "manifest.json").write_text(json.dumps({
        "schema_version": 1, "run_id": directory.name, "kind": "sweep",
        "strategy": strategy_name, "param_grid": {k: list(v) for k, v in param_grid.items()},
        "created_at": _now_iso(), "path": str(directory),
    }, indent=2, default=str))
    os.replace(tmp, directory)
```

### 2.4 New file `stolgo/ui/index.py` — `runs_index` DuckDB table

```python
# Responsibilities:
#  - open the index DuckDB file (default runs/_index.duckdb)
#  - ensure_schema(): CREATE TABLE IF NOT EXISTS runs_index (...)
#  - upsert_run(manifest: dict): called by export_all/export_sweep after rename
#  - reconcile(runs_dir): glob */manifest.json ONCE at server start, upsert missing
#  - all reads are per-connection, read-only, no long-lived handle
```

Table DDL (from `FRONTEND_SPEC.md` §3.2):

```sql
CREATE TABLE IF NOT EXISTS runs_index (
  schema_version INTEGER, run_id VARCHAR PRIMARY KEY, kind VARCHAR,
  strategy VARCHAR, params JSON, metrics JSON, created_at TIMESTAMP, path VARCHAR
);
```

Concurrency rule: **open DuckDB per call, close immediately.** Never hold the
connection open across requests (avoids the single-process file lock).

**Acceptance**: after two backtests + one sweep, `SELECT count(*), kind FROM
runs_index GROUP BY kind` returns the right counts; deleting the index file and
restarting the server rebuilds it via `reconcile`.

### 2.5 New file `stolgo/ui/adapters.py` — stolgo → frontend JSON

Pure functions. **This is the single source of truth for the API contract.** All
timestamps → **unix SECONDS** (lightweight-charts requirement).

```python
def _to_secs(ts) -> int:               # pandas Timestamp / datetime64 → int seconds
    return int(pd.Timestamp(ts).timestamp())

def run_summary(manifest: dict) -> dict:
    m = manifest.get("metrics", {})
    p = manifest.get("params", {})
    return {
        "id": manifest["run_id"],
        "strategy": manifest["strategy"],
        "market": p.get("symbol") or "—",
        "timeframe": p.get("interval") or "—",
        "return": m.get("total_return", 0.0),      # fraction, format % in UI
        "sharpe": m.get("sharpe", 0.0),
        "drawdown": m.get("max_drawdown", 0.0),
        "trades": int(m.get("num_trades", 0)),
        "created_at": manifest.get("created_at"),
    }

def metric_cards(metrics: dict) -> list[dict]:
    # V1: real numbers only, NO cue/micro (decision #2)
    order = [("total_return","Net return","pct"), ("cagr","CAGR","pct"),
             ("sharpe","Sharpe","num"), ("max_drawdown","Max drawdown","pct"),
             ("profit_factor","Profit factor","num"), ("hit_rate","Win rate","pct"),
             ("expectancy","Expectancy","r"), ("num_trades","Trades","int")]
    return [{"key": k, "label": lbl, "value": metrics.get(k, 0.0), "fmt": fmt}
            for k, lbl, fmt in order]

def series(ohlcv_df, equity_s, drawdown_s) -> dict:
    candles = [{"time": _to_secs(i), "open": float(r.open), "high": float(r.high),
                "low": float(r.low), "close": float(r.close)}
               for i, r in ohlcv_df.iterrows()]
    volume  = [{"time": _to_secs(i), "value": float(r.volume),
                "color": "rgba(20,154,90,0.18)" if r.close >= r.open else "rgba(200,63,58,0.16)"}
               for i, r in ohlcv_df.iterrows()]
    equity   = [{"time": _to_secs(i), "value": float(v)} for i, v in equity_s.items()]
    drawdown = [{"time": _to_secs(i), "value": float(v)} for i, v in drawdown_s.items()]
    return {"candles": candles, "volume": volume, "equity": equity, "drawdown": drawdown}

def trades(trades_df) -> list[dict]:
    out = []
    for i, r in trades_df.iterrows():
        pnl = float(r.get("net_pnl", 0.0))
        out.append({
            "id": int(i) + 1,
            "entryTime": _to_secs(r["entry_ts"]), "exitTime": _to_secs(r["exit_ts"]),
            "entryPrice": float(r["entry_price"]), "exitPrice": float(r["exit_price"]),
            "qty": float(r["qty"]), "pnl": pnl, "r": round(float(r.get("r_multiple", 0.0)), 2),
            "side": "Long",                        # long-only v0; add real side when shorts land
            "tag": r.get("tag") or "",
            "pnlClass": "positive" if pnl >= 0 else "negative",
        })
    return out
```

**Acceptance**: feed an existing dir (e.g. `parabolic_short_output/`) through these
and assert every key in `mockData.js`'s shapes is present with correct types.

### 2.6 New file `stolgo/ui/server.py` — FastAPI

Endpoints (read-only). List from `runs_index`; detail reads that run's Parquet by
`path`. Apply the error contract from `FRONTEND_SPEC.md` §4.

| Method | Path | Source | Adapter |
|---|---|---|---|
| GET | `/api/runs` | `runs_index` where `kind='run'` | `run_summary` per row |
| GET | `/api/runs/{id}` | manifest + `metrics` | `{strategy, params, metrics: metric_cards(...)}` |
| GET | `/api/runs/{id}/series` | `parquet/{ohlcv,equity,drawdown}.parquet` | `series(...)` |
| GET | `/api/runs/{id}/trades` | `parquet/trades.parquet` | `trades(...)` |
| GET | `/api/sweeps` | `runs_index` where `kind='sweep'` | manifest rows |
| GET | `/api/sweeps/{id}` | `results.parquet` + manifest | `{param_grid, rows}` |

Errors: unknown id or missing manifest → **404**; manifest present but a referenced
Parquet missing/corrupt → **409** with `{detail}`; `schema_version` newer than the
server → **409**; list endpoints skip bad rows and return `warnings: <count>`.

### 2.7 CLI — `stolgo serve`

Add to `cli/main.py` (argparse subcommand, matching existing style):

```
stolgo serve [--runs-dir runs] [--port 8000] [--host 127.0.0.1]
```

On start: `index.reconcile(runs_dir)` then launch uvicorn serving FastAPI + the
built frontend (`frontend/dist/`, §4). Also wire `export_all`/`export_sweep` (or
the CLI run path) to call `index.upsert_run(manifest)` after each export.

### 2.8 Dependencies

`pyproject.toml`: promote `pyarrow` to base deps; add extra
`ui = ["fastapi>=0.110", "uvicorn>=0.29", "duckdb>=0.10"]`. (WebSockets not needed
for V1.)

---

## 3. Field mapping reference (authoritative)

Timestamps: stolgo stores UTC (ns / tz-aware); frontend needs **unix seconds** —
convert in the adapter (§2.5), never in the UI.

| Frontend field | Stolgo source | Notes |
|---|---|---|
| `candles[].{time,open,high,low,close}` | `ohlcv.parquet` (index, open,high,low,close) | time = index→secs |
| `volume[].{time,value,color}` | `ohlcv.volume` | color by close≥open |
| `equity[].{time,value}` | `equity.parquet` | index→secs |
| `drawdown[].{time,value}` | `drawdown.parquet` (percent) | index→secs |
| trade `entryTime/exitTime` | `entry_ts/exit_ts` | →secs |
| trade `entryPrice/exitPrice/qty` | `entry_price/exit_price/qty` | direct |
| trade `pnl` | `net_pnl` | rename |
| trade `r` | `r_multiple` | round 2 |
| trade `side` | — (none) | hardcode `"Long"` (long-only v0) |
| trade `tag` | `tag` | direct |
| Library Return/Sharpe/DD/Trades | `metrics.total_return/sharpe/max_drawdown/num_trades` | format in UI |
| Metric cards | `metrics.*` (§2.5 order) | real values only |

**Dropped in V1 (decision #2)** — remove the components/columns, do not fake:
Library `status` pill, metric `cue`+`micro`, `regimeRows` table, Detail
recommendation strip, `InsightsRail`.

---

## 4. Frontend changes (`frontend/`, React + Vite + lightweight-charts)

### 4.1 New `src/data/client.js` — fetch layer mirroring `mockData.js`

Expose the **same names** pages already import, so swapping is a one-line import
change per page:

```js
const BASE = import.meta.env.VITE_API_BASE ?? "/api";
async function get(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}
export const listRuns          = ()   => get(`/runs`);
export const getRun            = (id) => get(`/runs/${id}`);
export const getRunSeries      = (id) => get(`/runs/${id}/series`);
export const getRunTrades      = (id) => get(`/runs/${id}/trades`);
export const listSweeps        = ()   => get(`/sweeps`);
export const getSweep          = (id) => get(`/sweeps/${id}`);
```

### 4.2 Page rewiring

- **`App.jsx`**: replace `useMemo(makeData)` + `strategies` import with state loaded
  from `listRuns()` (on mount) and, when a run is opened, `getRunSeries(id)` +
  `getRunTrades(id)` + `getRun(id)`. Keep the existing `data` prop shape
  (`{candles, volume, equity, drawdown, trades}`) so `TradingCharts` and
  `TradeTable` need no change — `getRunSeries` already returns that shape.
- **`StrategyLibraryPage.jsx`**: map `listRuns()` rows instead of `strategies`.
  Remove the **Status** column (header + cell). Keep Return/Sharpe/Drawdown/Trades.
  `Sparkline` — either drop for V1 or feed a downsampled equity array if you add it
  to the summary later; simplest V1 = remove.
- **`StrategyDetailPage.jsx`**: source metric cards from `getRun(id).metrics`
  (already `metric_cards` shape). **Remove** `InsightsRail` and the recommendation/
  decision strip. `TradingCharts` + `TradeTable` unchanged.
- **`ComparePage.jsx` / `OptimizationPage.jsx`**: wire to `listRuns()` /
  `getSweep(id)`. Overlaid equity in Compare needs each run's equity — fetch
  `getRunSeries` per selected id (fine for a handful).
- **`ReportsPage.jsx`**: V1 can link to the run's static `tearsheet.html` or reuse
  `getRun`. No new data needed.
- **`NewBacktestPage.jsx`**: leave on mock / "coming soon" (decision #4).
- Delete `regimeRows` usage; keep `mockData.js` importable behind `VITE_USE_MOCK=1`
  only during transition, then remove.

### 4.3 Charts — no change to `TradingCharts.jsx`

It already uses `lightweight-charts` v5 (`createChart`, `CandlestickSeries`,
`HistogramSeries`, `AreaSeries`, `createSeriesMarkers`) and expects
`{candles, volume, equity, drawdown, trades}` keyed by `time` in seconds — which is
exactly what `getRunSeries` + `getRunTrades` return. Verify markers land on the
right bars (entry/exit times must match candle times).

### 4.4 Serving & dev

- **Dev**: run Vite (`npm run dev`, :5173) + FastAPI (:8000). Add to
  `vite.config.mjs`: `server.proxy = { "/api": "http://127.0.0.1:8000" }` so
  `fetch("/api/...")` works with hot reload.
- **Prod (`stolgo serve`)**: `npm run build` → `frontend/dist/`; FastAPI mounts
  `dist/` as static root and `/api/*` as the API. One process, one port.

---

## 5. Build order (do in sequence, each independently testable)

**Phase A — backend produces consumable artifacts**
1. §2.1 ohlcv+drawdown persistence (env-gated) + test.
2. §2.2 manifest + atomic publish (+ `strategy_name` param on `export_all`) + test.
3. §2.3 `export_sweep`; call it from `examples/parameter_sweep.py` path.
4. §2.4 `runs_index` (`stolgo/ui/index.py`) + upsert + reconcile + test.
5. §2.5 `adapters.py` + golden test against an existing `*_output/` dir.

**Phase B — API**
6. §2.6 `server.py` endpoints + error contract.
7. §2.7 `stolgo serve` + §2.8 deps.
8. Smoke test with `curl`/httpie: every endpoint returns adapter-shaped JSON.

**Phase C — frontend swap**
9. §4.1 `client.js` + §4.4 Vite proxy.
10. Wire Library + Detail (the two critical pages); remove §2/§3 dropped fields.
11. Wire Compare + Optimization.
12. Delete/relocate `mockData.js`; `regimeRows` gone.

**Phase D — verification (required)**
13. Run a real backtest, open it in the UI, assert each visible number equals
    `summary.json`/`tearsheet.html`.
14. Marker correctness: entry/exit arrows sit on the correct candles.
15. Concurrency: start a long backtest while browsing — the in-progress run must be
    invisible until its atomic rename completes (proves §2.2).

---

## 6. Definition of done (V1)

- A strategy backtested with stolgo appears in the Library with real
  Return/Sharpe/Drawdown/Trades, no code edits to the frontend.
- Opening it shows real candles + trade markers, equity, drawdown, trade log, and a
  metrics panel of real values.
- Sweeps appear under Optimization with the real per-combo metrics table.
- No invented field is rendered (all dropped per decision #2).
- `STOLGO_PERSIST_SERIES=0` cleanly disables the new Parquet output (charts then
  degrade to "no series available", not a crash).
```
