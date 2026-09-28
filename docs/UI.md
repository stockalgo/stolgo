# Stolgo UI

The Stolgo UI is a local, read-only browser for completed backtest and sweep
exports. It is designed for reviewing artifacts produced by `export_all()` and
`export_sweep()`, not for starting live trading or placing orders.

## Install

The UI server dependencies are optional:

```bash
pip install "stolgo[ui]"
```

From a source checkout, build the frontend assets once before serving the UI:

```bash
npm ci --prefix frontend
npm run build --prefix frontend
```

`pyarrow` is a base dependency because Parquet export is now part of Stolgo's
reporting contract. `fastapi`, `uvicorn`, and `duckdb` stay in the `ui` extra.

## Produce a run

Backtests write standardized v2 artifacts, including a manifest, normalized trades,
daily session series, and series files needed by the UI:

```python
from pathlib import Path

from stolgo.report.exporters import export_all

result = Backtest(MyStrategy(), df, symbol="BTCUSDT", interval="1h").run()
export_all(result, Path("runs/btcusdt-sma"), strategy_name="BTCUSDT SMA")
```

### Artifacts layout (v2)

By default, `export_all()` writes:

- `manifest.json` (schema_version: 2)
- `summary.json`
- `trades.csv`
- `tearsheet.html`
- `audit.html` (optional)
- `parquet/trades.parquet` (normalized trade schema v2)
- `parquet/legs.parquet` (multi-leg trade breakdown, optional)
- `parquet/daily.parquet` (calendar daily session P&L, equity, and drawdown)
- `parquet/equity.parquet` (intraday equity curve, optional)
- `parquet/positions.parquet` (when positions exist, optional)
- `parquet/ohlcv.parquet` (underlying OHLCV, optional)

> Note: `drawdown.parquet` is removed in v2; drawdown series are now derived from `daily.parquet`.

Set `STOLGO_PERSIST_SERIES=0` to skip the optional OHLCV Parquet file:

```bash
STOLGO_PERSIST_SERIES=0 python examples/trend_breakout_backtest.py
```

### Metric basis note

All run-level performance metrics (`cagr`, `sharpe`, `sortino`, `calmar`, `max_drawdown`) use the **`calendar_daily`** basis computed over every trading session in the exchange calendar window (annualized with $\sqrt{252}$ and risk-free rate = 0). Days without closed trades record ₹0 P&L and preserve prior equity.

### Migration

Legacy runs (v1 schema) can be migrated to v2 with the migration CLI:

```bash
# Preview changes first
PYTHONPATH=lib python scripts/migrate_runs_v2.py --runs-dir runs --dry-run

# Run migration
PYTHONPATH=lib python scripts/migrate_runs_v2.py --runs-dir runs
```

## Serve

```bash
stolgo serve --runs-dir runs --host 127.0.0.1 --port 8000
```

The server reconciles completed `*/manifest.json` files into a local DuckDB index (`_index.duckdb`) at startup based on file modification times. Runs published as `*.tmp` remain invisible until the atomic rename finishes, so the UI does not browse partially written artifacts.

## API contract v2

The API is read-only:

- `GET /api/runs`: Run summaries (`schema_version == 2`). Legacy v1 runs are excluded and counted as warnings.
- `GET /api/runs/{id}`: Detailed run information, configuration, full metrics, robustness metrics, diagnostics, and metric registry definitions.
- `GET /api/runs/{id}/daily`: Calendar daily session P&L, cumulative equity, and drawdown.
- `GET /api/runs/{id}/monthly`: Monthly P&L, return %, and trade counts aggregated from daily sessions.
- `GET /api/runs/{id}/trades`: Trade rows with epoch second timestamps and normalized schema v2 columns.
- `GET /api/runs/{id}/trades/{trade_id}`: Trade detail including individual execution legs and intraday OHLCV bars for the session.
- `GET /api/runs/{id}/candles?tf=1D|1H|15m&from=YYYY-MM-DD&to=YYYY-MM-DD`: Resampled OHLCV candle series.
- `GET /api/runs/{id}/equity`: High-resolution intraday equity curve (when available).
- `GET /api/groups`: Grouped runs metadata and parameter sweep axes.
- `GET /api/groups/{id}`: Group details and list of constituent run summaries.
- `GET /api/migration-report`: Migration report (`runs/_migration_report.md`).
- `GET /api/runs/{id}/audit`: HTML audit report (when present).
- `GET /api/runs/{id}/series`: Legacy series endpoint (maintained for backwards compatibility until UI migration).
- `GET /api/sweeps` and `GET /api/sweeps/{id}`: Legacy parameter sweep results.

Unmigrated v1 runs return `409 Conflict` with `{"detail":"run_not_migrated","hint":"python scripts/migrate_runs_v2.py"}` on detail endpoints.

## Security notes

- The UI is intended for local use on `127.0.0.1`.
- Manifests are treated as untrusted input. The API rejects manifest paths that resolve outside the configured `runs_dir`.
- Missing or corrupt run artifacts return `409` instead of falling back to fake chart data.
- Tests use local fixtures and exported artifacts only; they do not call live data APIs.

## Example

The CoinDCX BTCUSDT example exports a UI-ready run:

```bash
PYTHONPATH=lib .venv/bin/python examples/btc_usdt_coindcx_backtest.py \
  --output runs/coindcx-btcusdt-sma
```

Then open it with:

```bash
stolgo serve --runs-dir runs
```
