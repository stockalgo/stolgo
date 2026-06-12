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
| **Price-action first** | Write `pa.crosses_above(pa.resistance(21))` — readable rules, not indicator soup |
| **Composable** | Combine levels, relations, candles, and streaks with `&` `\|` `~` `.then()` |
| **Trade in one line** | `trade.long(ctx, rr=(1, 2), stop="candle_low")` — stops, targets, sizing handled |
| **Presets** | `pa.preset.consolidation_breakout(7)` and friends — proven setups, zero wiring |
| **Honest simulation** | Event loop with configurable fill timing (`next_open` or `close`), commission, slippage |
| **No look-ahead** | `ctx.data` only exposes history up to the current bar; MTF levels align safely |
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

## Price action in 30 seconds

This is the heart of stolgo. Describe a setup the way you'd say it out loud, attach a
risk/reward bracket, and backtest it. One import: `import stolgo.pa as pa`.

```python
from datetime import datetime, timedelta, timezone

import stolgo.pa as pa
from stolgo import Backtest, Bandl, Context, Strategy, trade

# 1. Describe the edge in plain price-action language
entry = pa.crosses_above(pa.resistance(21))      # close breaks the 21-bar high

# 2. Trade it with a 1:2 risk/reward bracket, stop under the signal candle
class Breakout(Strategy):
    bracket = None

    def on_bar(self, ctx: Context) -> None:
        if not ctx.position.flat:                        # in a trade → manage exit
            if trade.bracket_hit(ctx, self.bracket):     # stop or target touched
                trade.close(ctx)
                self.bracket = None
        elif entry(ctx):                                 # flat + breakout → enter
            self.bracket = trade.long(ctx, rr=(1, 2), stop="candle_low", qty=0.05)

# 3. Run it on real data
end = datetime.now(timezone.utc)
df = Bandl().history("BTCUSDT", "1h", end - timedelta(days=365), end)
result = Backtest(Breakout(), df, fill_on="close").run()
print(result.summary())
result.report.to_html("tearsheet.html")
```

That's a complete, look-ahead-safe breakout backtest with stops, targets, fees, and a
shareable tearsheet — no indicators required.

---

## The price-action vocabulary

Everything below is a flat attribute on `pa`. Mix and match with `&` (and), `|` (or),
`~` (not), and `.then()` (sequence) to build any setup.

**Levels** — a price line per bar

```python
pa.resistance(20)        pa.support(20)         # rolling highs / lows
pa.range_high(7)         pa.range_low(7)        # consolidation box edges
pa.donchian_high(20)     pa.donchian_low(20)
pa.vwap()                pa.prev_day_high()     pa.prev_day_low()
pa.swing_high(5)         pa.swing_low(5)        pa.pivot_point()
pa.level(42_000)                                # a fixed price
pa.resistance(21, tf="1d")                      # daily level on intraday bars (MTF)
```

**Relations** — turn a level into a true/false rule

```python
pa.above(lvl)            pa.below(lvl)
pa.crosses_above(lvl)    pa.crosses_below(lvl)   # breakouts / breakdowns
pa.rejected_at(lvl)      pa.recovered_at(lvl)    # failed break / reclaim
pa.near(lvl, pct=0.005)  pa.touched(lvl)
```

**Patterns** — candles, streaks, structure, momentum

```python
pa.bullish_engulfing()   pa.bearish_engulfing()  pa.hammer()   pa.doji()
pa.streak.green(3)       pa.streak.red(3)         pa.first_red_day()
pa.consolidation(days=7) pa.breakout_up(7)        pa.breakout_down(7)
pa.run_up(min_pct=2.0)   pa.parabolic_up()        pa.giant_uptrend()
```

**Compose** them into the setup you actually trade

```python
# 7-day box, then close breaks the box high
entry = pa.consolidation(days=7) & pa.crosses_above(pa.range_high(7))

# three green candles, then a bearish engulfing → fade it
fade = pa.streak.green(3).then(pa.bearish_engulfing())

# break above 21-day daily resistance, but only near VWAP
intraday = pa.crosses_above(pa.resistance(21, tf="1d")) & pa.near(pa.vwap())
```

---

## Trade it: risk/reward brackets (`stolgo.trade`)

`stolgo.trade` turns a signal into an order with a stop and target — no manual SL/TP math.

```python
from stolgo import trade

trade.long(ctx,  rr=(1, 2), stop="candle_low",  qty=0.05)   # target = 2× risk
trade.short(ctx, rr=(1, 3), stop="candle_high", qty=0.05)
trade.bracket_hit(ctx, bracket)   # -> "stop", "target", or None on this bar
trade.close(ctx)                  # flatten (longs sell, shorts cover)
```

Size by fixed `qty`, or risk a fixed fraction of equity per trade with
`size_risk_pct=0.01`.

---

## Presets: battle-tested setups in one line

Don't want to wire rules yourself? `pa.preset.*` returns ready-made rules.

```python
import stolgo.pa as pa

pa.preset.scalp_green_fade(min_green=3)        # fade a green run on a reversal candle
pa.preset.consolidation_breakout(days=7)       # classic box breakout
pa.preset.breakout_intraday(days=7)            # daily S/R, intraday trigger → (long, short)
pa.preset.failed_break_intraday(days=7)        # fade failed breaks of daily S/R
pa.preset.parabolic_short(min_pct=2.0)         # short the first red day after a parabola
```

See **[docs/PA.md](docs/PA.md)** for the full grammar, multi-timeframe levels, and every
rule. Runnable bots live under [`examples/pa/`](examples/pa/).

---

## Not just price action

Prefer indicators or vector signals? The same engine runs those too.

```python
from stolgo import Backtest, Context, Strategy, load
from stolgo.signals import sma

class Trend(Strategy):
    def on_start(self, ctx: Context) -> None:
        self._sma = sma(ctx.data.close, 50)

    def on_bar(self, ctx: Context) -> None:
        if ctx.position.flat and ctx.data.close[-1] > self._sma[ctx.i]:
            ctx.buy(size_pct=0.25)
        elif not ctx.position.flat and ctx.data.close[-1] < self._sma[ctx.i]:
            ctx.close()

df = load("ohlcv.csv", symbol="BTCUSDT")
print(Backtest(Trend(), df, cash=100_000, commission=0.001).run().summary())
```

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
| `stolgo.pa` | **Price-action toolkit**: levels, relations, patterns, presets |
| `trade` | Risk/reward brackets: `trade.long`, `trade.short`, `trade.bracket_hit`, `trade.close` |
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

**Price action (`stolgo.pa` + `trade`)** — start here:

| Script | Setup |
|--------|-------|
| [`examples/pa/btc_21d_sr_intraday.py`](examples/pa/btc_21d_sr_intraday.py) | Break of 21-day daily support/resistance on intraday bars (long + short) |
| [`examples/pa/btc_consolidation_pa.py`](examples/pa/btc_consolidation_pa.py) | 7-day consolidation breakout with a 1:4 bracket |
| [`examples/pa/scalp_green_fade.py`](examples/pa/scalp_green_fade.py) | Fade a green streak on a reversal candle |
| [`examples/pa/intraday_breakout.py`](examples/pa/intraday_breakout.py) | `pa.preset.breakout_intraday` long/short |
| [`examples/pa/failed_break.py`](examples/pa/failed_break.py) | Fade failed breaks of daily S/R |
| [`examples/pa/parabolic_short.py`](examples/pa/parabolic_short.py) | Short the first red day after a parabolic run |

**Indicators & vector signals:**

| Script | Demonstrates |
|--------|----------------|
| [`examples/trend_breakout_backtest.py`](examples/trend_breakout_backtest.py) | SMA trend, signals, tearsheet |
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
