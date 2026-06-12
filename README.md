<p align="center">
  <a href="https://stolgo.com" target="_blank">
    <img src="https://raw.githubusercontent.com/stockalgo/stolgo/master/stolgo.svg" alt="stolgo" width="320">
  </a>
</p>

<p align="center">
  <strong>Backtest price-action and quant strategies in Python — simple API, serious simulation.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/stolgo/">pip install stolgo</a> ·
  Python 3.10+ · MIT License ·
  <a href="https://bandl.io">bandl</a> data &amp; brokers
</p>

---

## What is stolgo?

**stolgo** is a lightweight backtesting framework built for traders who think in **price action** — breakouts, consolidation, support/resistance, candle behaviour — not only indicator crossovers.

Most libraries optimise for MACD/RSI grids. stolgo optimises for **clear rules on OHLCV**, a **deterministic event loop** (fills, cash, positions), and **reporting you can share** (equity curve, drawdown, trade log, Plotly tearsheet).

Write your logic once. Point it at market data or a CSV. Get metrics and charts.

---

## Why stolgo?

| Strength | What you get |
|----------|----------------|
| **Simple surface** | `Strategy` + `Context` + `Backtest(...).run()` — no boilerplate engine |
| **Price-action first** | Express rules on open/high/low/close; see `examples/btc_consolidation_breakout.py` |
| **Honest simulation** | Event loop with configurable fill timing (`next_open` or `close`), commission, slippage |
| **No look-ahead** | `ctx.data` only exposes history up to the current bar |
| **Vector or event style** | Precompute `entries`/`exits` masks *or* implement `on_bar` — same engine |
| **Data your way** | **[bandl](https://bandl.io)** for crypto/equity OHLCV, or **`load()`** for CSV/Parquet |
| **Built-in analytics** | Sharpe, drawdown, hit rate, profit factor, HTML tearsheet |

---

## Installation

```bash
pip install stolgo
```

For live market data via [bandl](https://bandl.io) (recommended):

```bash
pip install stolgo bandl
```

Optional extras: `pip install stolgo[numba]` for faster sweeps.

---

## Quickstart

Two imports. One strategy. One backtest.

```python
from datetime import datetime, timedelta, timezone

from stolgo import Backtest, Bandl, Context, Strategy, load
from stolgo.signals import sma

# --- Data: pick one ---

# Option A: bandl (crypto, equity, multiple venues — see bandl.io)
end = datetime.now(timezone.utc)
start = end - timedelta(days=365)
df = Bandl().history("BTCUSDT", "1d", start, end)

# Option B: local file (CSV or Parquet, auto-normalized to UTC OHLCV)
# df = load("ohlcv.csv", symbol="BTCUSDT")

# --- Strategy ---

class Trend(Strategy):
    def on_start(self, ctx: Context) -> None:
        self._sma = sma(ctx.data.close, 50)

    def on_bar(self, ctx: Context) -> None:
        if ctx.position.flat and ctx.data.close[-1] > self._sma[ctx.i]:
            ctx.buy(size_pct=0.25)
        elif not ctx.position.flat and ctx.data.close[-1] < self._sma[ctx.i]:
            ctx.close()

# --- Run ---

result = Backtest(Trend(), df, cash=100_000, commission=0.001).run()
print(result.summary())
result.report.to_html("tearsheet.html")
```

---

## Price action (`stolgo.pa`)

Composable levels and rules on OHLCV — flat import, no sub-packages in user code:

```python
import stolgo.pa as pa
from stolgo import trade, Backtest, Context, Strategy

entry = pa.consolidation(days=7) & pa.crosses_above(pa.range_high(7))

class Bot(Strategy):
    def on_bar(self, ctx: Context) -> None:
        if ctx.position.flat and entry(ctx):
            trade.long(ctx, rr=(1, 4), stop="candle_low")
```

See **[docs/PA.md](docs/PA.md)** for the full grammar, presets (`pa.preset.*`), and multi-timeframe levels. Example bots live under `examples/pa/`.

---

## Data sources

stolgo does not lock you into one vendor. Use whichever fits your workflow.

### [bandl](https://bandl.io) — `Bandl`

[`bandl`](https://github.com/stockalgo/bandl) aggregates OHLCV from crypto exchanges, equity feeds, and other providers. stolgo wraps it as **`Bandl`**: fetch, normalize columns, optional parquet cache, then backtest.

```python
from stolgo import Bandl

df = Bandl(provider="crypto").history("BTCUSDT", "1d", start, end)
```

Use this for **crypto (e.g. BTCUSDT)**, **Indian/US equity**, and any symbol bandl supports. Configure credentials per bandl’s docs when required.

### Local files — `load`

For research archives, exports, or offline work:

```python
from stolgo import load

df = load("data/btc_daily.parquet", symbol="BTCUSDT")
```

Supports **`.csv`**, **`.parquet`**, **`.pq`**. Timestamps are parsed to **UTC**; columns are normalized to `open`, `high`, `low`, `close`, `volume`.

### Bring your own `DataFrame`

Already have pandas OHLCV? Pass it directly to `Backtest` as long as it has a UTC datetime index (or a `timestamp` column).

---

## Public API (v0.2)

| Import | Purpose |
|--------|---------|
| `Backtest` | High-level runner → `RunResult` |
| `Strategy` | Base class: `on_start`, `on_bar`, `on_fill`, `on_end` |
| `Context` | Per-bar API: `ctx.data`, `ctx.position`, `ctx.buy` / `ctx.close` |
| `Bandl` | Market data via bandl (`BandlDataSource` alias) |
| `load` | Load CSV / Parquet |
| `RunResult` | `metrics`, `trades`, `equity`, `report` |
| `parameter_sweep` | Grid search over strategy parameters |
| `stolgo.signals` | `sma`, `ema`, `atr`, `rsi`, `donchian`, … |

Advanced: `Engine`, `RunConfig`, `Pipeline` (cross-sectional), `stolgo.report.export_all`.

---

## Examples

| Script | Demonstrates |
|--------|----------------|
| [`examples/trend_breakout_backtest.py`](examples/trend_breakout_backtest.py) | SMA trend, signals, tearsheet |
| [`examples/btc_consolidation_breakout.py`](examples/btc_consolidation_breakout.py) | 7-day consolidation breakout, SL/TP, bandl BTCUSDT |
| [`examples/vector_momentum_backtest.py`](examples/vector_momentum_backtest.py) | Vector `entries` / `exits` (no `on_bar` body) |
| [`examples/parameter_sweep.py`](examples/parameter_sweep.py) | 100-combo parameter sweep |

CLI:

```bash
stolgo my_strategy.py --class MyStrategy --data ohlcv.csv --output ./results
```

---

## How it works (short)

```text
OHLCV (Bandl / load / DataFrame)
        ↓
   Backtest(strategy, data).run()
        ↓
   Engine: for each bar → match fills → on_bar → risk → submit orders
        ↓
   RunResult: equity, trades, metrics, Plotly tearsheet
```

Default fill model: signal on bar **t** → fill at bar **t+1 open** (`fill_on="next_open"`). Use `fill_on="close"` when you want same-bar close fills (e.g. breakout-on-close setups).

---

## Legacy price-action helpers

The original stolgo modules (`candlestick`, `breakout`, `trend`, …) remain available for pattern checks on raw DataFrames. New projects should prefer the **`Strategy` + `Backtest`** API above.

```python
from stolgo.candlestick import CandleStick
from stolgo.breakout import Breakout

cs = CandleStick()
is_engulfing = cs.is_bullish_engulfing(df)
```

---

## Development

```bash
git clone https://github.com/stockalgo/stolgo.git
cd stolgo
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -q
```

Architecture notes: [`docs/HLD.md`](docs/HLD.md).

---

## Contributing

Pull requests are welcome. For larger changes, open an issue first. Follow PEP 8, add tests for new behaviour, and keep the public API intuitive (prefer `from stolgo import …` over deep internal paths).

---

## License

[MIT](https://choosealicense.com/licenses/mit/)
