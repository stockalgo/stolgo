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

Backtests continue to write the existing artifacts, plus a manifest and the
series files needed by the UI:

```python
from pathlib import Path

from stolgo.report.exporters import export_all

result = Backtest(MyStrategy(), df, symbol="BTCUSDT", interval="1h").run()
export_all(result, Path("runs/btcusdt-sma"), strategy_name="BTCUSDT SMA")
```

By default, `export_all()` writes:

- `summary.json`
- `trades.csv`
- `tearsheet.html`
- `manifest.json`
- `parquet/trades.parquet`
- `parquet/equity.parquet`
- `parquet/positions.parquet` when positions exist
- `parquet/ohlcv.parquet`
- `parquet/drawdown.parquet`

Set `STOLGO_PERSIST_SERIES=0` to skip the new OHLCV and drawdown Parquet files:

```bash
STOLGO_PERSIST_SERIES=0 python examples/trend_breakout_backtest.py
```

## Serve

```bash
stolgo serve --runs-dir runs --host 127.0.0.1 --port 8000
```

The server reconciles completed `*/manifest.json` files into a local DuckDB index
at startup. Runs published as `*.tmp` remain invisible until the atomic rename
finishes, so the UI does not browse partially written artifacts.

## API

The API is read-only:

- `GET /api/runs`
- `GET /api/runs/{id}`
- `GET /api/runs/{id}/series`
- `GET /api/runs/{id}/trades`
- `GET /api/sweeps`
- `GET /api/sweeps/{id}`

There is intentionally no endpoint that starts a backtest or places orders.

## Security notes

- The UI is intended for local use on `127.0.0.1`.
- Manifests are treated as untrusted input. The API rejects manifest paths that
  resolve outside the configured `runs_dir`.
- Missing or corrupt run artifacts return `409` instead of falling back to fake
  chart data.
- Tests use local fixtures and exported artifacts only; they do not call live data
  APIs.

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
