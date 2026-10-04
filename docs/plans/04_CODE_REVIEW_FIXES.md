# Plan 04 — Code review: correctness, speed, noise (review of `feat/ui-cockpit` @ cf17efc, 2026-09-30)

> Same rules as Plans 01–03: tasks **in order**, one commit per task `cr-fix: <ID> — <title>`,
> `PYTHONPATH=lib pytest -q` + `npm test --prefix frontend` green after every commit.
> Every finding below was **reproduced**. The repro scripts are in §7. The backend suite passes today (160 passed, 1 skipped)
> on a clean Python 3.11 environment. It passes only because the tests never exercise the bugs below.

## 0. Two kinds of change. Keep them apart

| Kind | IDs | Rule |
|---|---|---|
| **Behaviour-changing** (fixes wrong numbers) | H*, C*, R* | Each ships with a failing-first test that reproduces the bug. Numbers are allowed to change. Note them in the commit body |
| **Behaviour-preserving** (speed, noise) | F*, N* | **No number may change.** Before starting F1, do G0 (golden snapshot). Every F/N commit must pass the golden test byte-for-byte |

The 128 options runs in `runs/` come from `options/replay.py` + migration, not from `Engine`, so C* fixes do **not** change them. R1–R3 change only `export_all` (generic Backtest exports).

---

## P0 — Repo hygiene (do first)

### H1 — Commit the files HEAD depends on
`git status` shows these **untracked**, yet committed code imports or reads them. A fresh clone fails:
- `lib/stolgo/report/calendar_metrics.py` (imported by `report/run_metrics.py:9`)
- `lib/stolgo/options/` (replay), `tests/test_calendar_metrics.py`, `tests/test_options_replay.py`
- `docs/plans/fixtures/expected_after_migration.json` (read by `tests/test_robustness.py`, `tests/test_run_metrics.py`)
- `docs/plans/*.md`, `docs/design/`, `lib/stolgo/data/binance_universe.py`, `lib/stolgo/strategy/builtins/parabolic_short.py`, `lib/stolgo/report/rmultiple_metrics.py` + their tests
- The **uncommitted** fix in `lib/stolgo/oms/order_book.py` (gap-aware stop: `max(open, stop)` / `min(open, stop)`). HEAD still fills every triggered stop at `bar.open`, which is wrong whenever the stop is hit intrabar.
- `lib/stolgo/data/bandl_source.py`, `normalize.py`, `tests/test_data_bandl_source.py` (modified, uncommitted)

**Do NOT commit** `runs/` (data) or `parabolic_short_output/`. Add them to `.gitignore`.
**Done when:** `git clone <repo> /tmp/x && cd /tmp/x && uv venv && uv pip install -e ".[ui,dev]" && PYTHONPATH=lib pytest -q` is green.

---

## P0 — Backtest engine correctness (`lib/stolgo/core`, `oms`, `portfolio`, `report/trades.py`, `trade/`)

### C1 — Short trades disappear from the trade log
`report/trades.py::build_trades_from_fills` is "long-only v0.1". A SELL with no open long lot is **silently dropped**, and the covering BUY becomes a long lot that never closes.
Repro (§7-a): sell 10 @103, cover @101 → equity +₹20, **trades = 0 rows**. `trade.short()` is public API, so every short strategy reports no trades, a wrong hit rate and a wrong expectancy.
**Fix:** a signed-position FIFO matcher. Open lots carry `side`. A fill in the opposite direction closes lots FIFO. Any excess opens a new lot on the new side (position flip = close + open). Add a `side` column (`LONG`/`SHORT`) to the trade frame. For shorts, `gross = (entry − exit) × qty`.
**Test:** `tests/test_engine_correctness.py::test_short_round_trip` expects exactly 1 trade: side SHORT, entry 103, exit 101, qty 10, gross 20.

### C2 — The risk gate blocks exits: a position can never be closed
`portfolio/risk.py::apply_risk` returns `None` for **every** intent once drawdown exceeds 50% (a hard-coded magic number), including `ctx.close()`.
Repro (§7-b): long 100 @100, price falls to 40, `ctx.close()` → the position is still open at the end, **0 trades**.
**Fix:** add `RunConfig.halt_drawdown: float | None = None` (default **off**). When it is set and breached, block only **risk-increasing** intents (those that would increase `abs(position)`). Never block reducing or closing intents. Record a `RISK_HALT` event once. Delete the 0.5 literal.
**Test:** the repro closes (position 0, 1 trade). With `halt_drawdown=0.5`, a new buy after the breach is rejected and the close still goes through.

### C3 — `size_pct` overspends cash (silent leverage)
`resolve_qty` sizes from the **signal bar close**. The fill happens at the next open, plus slippage and commission.
Repro (§7-c): `buy(size_pct=1.0)` at close 100, next open 150 → cash **−₹5,015**.
**Fix:** resolve `size_pct` **at fill time** inside `SimBroker.match`: `qty = floor_step(cash × pct / (fill_px × (1 + commission_rate)))`. Carry `size_pct` on the `Order`. Add `RunConfig.allow_leverage: bool = False`: when False, reject any fill that would make cash < 0 and emit an `ORDER_REJECTED` event with the reason `insufficient_cash`.
**Test:** the repro ends with cash ≥ 0, and the fill qty is 66.6… (not 100).

### C4 — Limit/stop intents lose their prices. STOP_LIMIT is never matched. No OCO
- `engine.py:134` calls `broker.create_order(symbol, side, qty, order_type)`. `intent.limit_price` / `stop_price` are **dropped**, so any LIMIT/STOP intent rests forever (the book requires a price).
- `OrderBook.add` accepts `STOP_LIMIT`, but `match()` has no branch for it, so it never fills and never errors.
- There is no OCO: a bracket's stop and target orders can both fill on one bar and flip the position.

**Fix:** pass the prices through. Implement STOP_LIMIT (triggers like STOP, then behaves as LIMIT from the trigger bar), or reject it at `submit()` with `NotImplementedError`. Pick **reject** unless a strategy needs it. Add `Order.oco_group: str | None`: when one order in a group fills, cancel its siblings in the same `match()`. If both would trigger on the same bar, fill the **stop** (adverse-first, documented).
Also, limit gap improvement: BUY limit fills at `min(bar.open, limit)` and SELL limit at `max(bar.open, limit)` when the bar opens through the limit.
**Tests:** a limit intent fills at the limit. A gap-through fills at the open. STOP_LIMIT raises. An OCO pair with both hit on one bar → exactly one fill (the stop).

### C5 — `fill_on="close"` fills at the NEXT bar's close
Repro (§7-d): a signal on bar 1 (close 101.2) fills at **102.2 on bar 2**. The name promises the signal-bar close.
**Fix:** rename the existing behaviour to `fill_on="next_close"`. Add `fill_on="signal_close"`, which executes intents immediately after `on_bar(i)` at `bar[i].close` (no look-ahead: the signal used data ≤ close[i]). Keep `"close"` as a deprecated alias for `"next_close"` with a `DeprecationWarning`. The default stays `next_open`.
**Test:** one test per mode, with exact fill prices.

### C6 — Bracket helpers size and stop from the wrong numbers
`trade/bracket.py`:
- `long()` / `short()` take `cash: float = 100_000.0`, a hard-coded default that sizes risk against a phantom ₹1 lakh instead of real equity.
- Entry, stop and target are computed from the **signal close**, but the fill is at the next open.
- `bracket_hit` + `ctx.close()` exit with a market order at the **next open**, not at the stop/target price.

**Fix:** add `ctx.cash` and `ctx.equity` (read-only) to `Context` and use them by default. Compute stop/target from the **actual fill price** in `on_fill`, and submit a resting STOP + LIMIT pair with a shared `oco_group` (needs C4). Remove the market-at-next-open exit path, or keep it only behind `exit="next_open"`.
**Test:** a long bracket with the stop touched intrabar exits at the stop price (or at the open on a gap), and the position size equals `equity × risk_pct / |fill − stop|`.

### C7 — `r_multiple` in engine trades is return-on-notional, not R
`trades.py:32`: `r_multiple = net / (entry_price × qty)`. **Fix:** rename it to `return_on_notional`. Set `r_multiple` only when the risk per unit is known (a bracket supplies it), otherwise NaN. The v2 exporter already shows NaN as "—".

### C8 — An open position at the end of data is silently excluded
**Fix:** add `RunConfig.close_at_end: bool = True`. On the last bar, submit closing intents that fill at that bar's close with tag `END_OF_DATA` (`exit_reason = "END_OF_DATA"` in v2). When it is False, emit one trade row with `exit_reason="OPEN"` and `net_pnl` = the MTM value, and exclude it from hit-rate/PF (count it in the diagnostics).

### C9 — There is no look-ahead probe for vector signals
`on_start` receives a **full-data** view (`engine.py:62–76`) so strategies can precompute masks. Nothing checks that those masks are causal.
**Fix:** add `stolgo/core/lookahead.py::probe(strategy_factory, df, cuts=(0.25,0.5,0.75))`. For each cut `k`, rebuild the strategy on `df.iloc[:k]` and assert `entries[:k]`/`exits[:k]` equal the full-run masks' prefixes. Expose it as `RunConfig.lookahead_check: bool = False`. Add parametrised tests that run the probe on every `stolgo.pa.preset` and `examples/` strategy that uses masks.

### C10 — `parabolic_short.simulate_trade`: the stop ignores gaps
Lines 349–357 fill a short's stop at `stop_price` even when the day opens **above** the stop. On parabolic names that caps losses at −1R, which is unrealistic.
**Fix:** `exit_price = max(opens[pos], stop_price)` when `hit_stop`. Keep the target at `target_price` (no gap improvement, conservative). Check that fees/slippage are applied to R. If they are not, add `config.cost_bps` (default 0 with a warning in the trade log).
**Test:** a gap-up day with open 1.3R above entry → r_multiple = −1.3, not −1.0.

### C11 — Replay accounting invariants use `assert`
`options/replay.py:305–306` and `report/run_metrics.py:64` check P&L identities with `assert`, which is stripped under `python -O`. **Fix:** replace them with `raise AccountingError(...)` (new class in `core/exceptions.py`).

---

## P1 — Report pipeline correctness (`report/`, `ui/adapters.py`)

### R1 — `export_all` throws away the mark-to-market equity → drawdown and Sharpe are wrong for any multi-bar hold
`export_all` builds `daily.parquet` from **realized** trade P&L by exit date. The engine's per-bar MTM equity (`result.equity`) is ignored for metrics.
Repro (§7-e): hold 100 units from 100 → 70 → 101. Engine MTM max DD = **−30%**. The v2 manifest says `max_drawdown 0.0` and `sharpe 3.0`.
(The 128 options runs are unaffected: their positions open and close within the same session.)
**Fix:** when `result.equity` exists, daily equity = the **last equity value per session**, and pnl = diff(equity) with the first day vs capital. Keep realized-only as a fallback with `metrics.equity_basis = "realized"`; the default is `"mark_to_market"`. Put `equity_basis` in the manifest and show it in the UI's Diagnostics KV list.
**Test:** the repro gives max_drawdown ≈ −0.30 (±0.001).

### R2 — IST/NSE/INR is hard-coded for every run
`daily.py`, `run_metrics.py:42` (15:30 IST close), `trade_schema.py` (`session_date` in IST), `ui/adapters.py::candles` (09:15–15:30 hour buckets) and the `export_all` default instrument (`exchange "NSE", currency "INR", timezone "Asia/Kolkata"`) all assume Indian cash hours. Repro (§7-e): a `BTCUSDT` run is exported as NSE/INR/IST. For 24/7 data, 1H candles drop every bar outside 09:15–15:30.
**Fix:** read `instrument.timezone` and `instrument.session_close` (new, `"HH:MM"`). Defaults: NIFTY/SENSEX → `Asia/Kolkata`, `15:30`. Anything else → `UTC`, `24:00` (calendar day). Thread these through `sessions_from_ohlcv`, `build_daily`, `compute_run_metrics`, `normalize_trades` and `candles`. `export_all` without an `instrument` must set `markets=[RunConfig.symbol]`, `exchange=None`, `currency=None`, `timezone="UTC"`. **Never** default to NSE/INR.
**Test:** a BTC run has sessions = UTC dates, and 1H candles cover 24 buckets per day.

### R3 — Zero-trade exports fabricate metrics
`exporters.py` (the `else` branch after `if not daily.empty`) writes `sharpe 0.0`, `cagr 0.0`, `max_drawdown 0.0`, `hit_rate 0.0`, … **Fix:** every metric is `None` except `num_trades: 0`, `net_pnl: 0.0`, `final_equity: capital`.

### R4 — `robustness.py` assumes i.i.d. trades
This is fine as a default. Add an optional `block` parameter (stationary block bootstrap, mean block length 5) and record the `method` value. **P3, optional.**

---

## P1 — Performance (behaviour-preserving → G0 first)

### G0 — Golden snapshot (before F1)
Add `tests/golden/test_engine_golden.py`. It runs 4 fixed strategies (long MA cross on `trend_up_300bars.csv`, the vector-lift strategy, a bracket strategy, and the 200k-bar random walk from §7-f with seed 1) and asserts the SHA-256 of `trades.to_csv(float_format="%.10g")` plus `round(equity.iloc[-1], 6)` against committed values. Generate the values once on the pre-F1 commit.
Also snapshot `export_run_v2` output JSON (the manifest minus `created_at`, `migrated_at`, `path`, `code_version`) for one migrated options run.

### F1 — `bars_from_dataframe` uses `iterrows` (76% of engine runtime)
Replace it with array zips:
```python
ts = df.index.asi8.tolist()
cols = [df[c].to_numpy("float64").tolist() for c in ("open","high","low","close","volume")]
return tuple(Bar(t, o, h, l, c, v, sym) for t, o, h, l, c, v in zip(ts, *cols))
```

### F2 — `apply_risk` calls `max(equity_curve)` on every intent → O(n²)
Keep a running peak in the engine loop (`peak = max(peak, eq)`) and pass `peak`/`current` to the risk check. Combined with F1, measured on 200k 1-minute bars / 6,422 trades: **27.6 s → 2.9 s (9.5×)**, final equity identical (99,982.2461).

### F3 — Engine per-bar allocations
- Store the int ns timestamps in a list and build the `DatetimeIndex` once at the end (`engine.py:102` creates 200k `pd.Timestamp` objects).
- Create **one** `BarDataView` and update `_limit` each bar instead of allocating a new one (`engine.py:106`).

Target: ≥ 100k bars/s on the §7-f benchmark. Add `tests/benchmark/test_engine_speed.py` marked `benchmark` (not in the default run) that asserts < 3 s.

### F4 — API candles are Python loops (1H full range: **3.7 s**, 1D default: 230 ms)
Rewrite `adapters.candles` with `DataFrame.resample`. 1D: group by session date via `resample("1D", offset=…)` in the instrument tz. 1H: `resample("60min", origin=<session open>)`. 15m: pass the rows through. Target: < 50 ms for the full 917-session NIFTY file.

### F5 — The API re-reads everything on every request
- `/api/runs`, `/api/groups` and `/api/groups/{id}` read and parse **all 128 manifests per request**. Serve them from the DuckDB `summary` column the index already stores.
- Trades/ohlcv/daily parquet are re-read on every call (e.g. each inspector click reads the 800 KB ohlcv). Add `functools.lru_cache(maxsize=64)` loaders keyed by `(path, mtime_ns)`.
- The index `reconcile()` runs only at startup, so runs created by the CLI don't appear until a restart (the New-run page text says otherwise). Reconcile when `runs_dir`'s mtime changes (one `stat` per request).

### F6 — Frontend: the `useApi` cache is dead code
Every call passes a bare fetcher (no key), so `apiCache` is never used. Overview, Trades and Diagnostics each re-download the full trade list on every tab switch.
**Fix:** use keyed calls (`useApi(\`run:${id}:trades\`, …)`), or fetch run-scoped data once in `RunLayout` and pass it via outlet context. Remove the untyped two-signature overload in `useApi` and keep `useApi(key, fetcher)` only.

### F7 — Frontend bundle
One 640 KB JS chunk. Route-level `React.lazy` for Compare, Group(s), RunChart, NewRun and Kit. Mount `/_kit` only when `import.meta.env.DEV`. Import only the latin + latin-ext font CSS (`@fontsource/ibm-plex-sans/latin-400.css` …): cyrillic, greek and vietnamese files ship in `dist/` today.

---

## P2 — Remove AI noise (behaviour-preserving)

| ID | What | Where |
|---|---|---|
| N1 | Delete the `# stolgo agent mistake checklist …` header blocks | 59 files under `lib/` and `tests/`. Keep the checklist once in `CONTRIBUTING.md` |
| N2 | Delete plan-narration comments (`# Step 1:`, `# 1. trade_id: keep if present…`, `# 6. exit_reason…`) | `report/trade_schema.py`, `report/run_metrics.py`, `scripts/migrate_runs_v2.py` |
| N3 | `trade_schema.normalize_trades`: 4 copy-pasted range-check blocks → one `_check_range(series, market, kind)`. The two `iterrows` loops → `Series.map` (exit reasons) and `str.findall` + `explode` (legs) | `report/trade_schema.py` |
| N4 | `run_metrics.target_keys` duplicates the registry → derive it from `metric_registry.METRICS`. `_clean_val` (run_metrics) and `_clean` (adapters) → one `stolgo/report/_json.py::clean` | `report/`, `ui/` |
| N5 | 9 broad `except Exception:` → catch the specific errors and log `run_id` + reason. `list_runs` must not silently count unknown failures as "warnings" without logging | `ui/server.py`, `report/daily.py`, `scripts/` |
| N6 | Dead code: `/api/runs/{id}/series` (the UI no longer calls it), `/api/sweeps*` (no sweep manifests exist; keep only if `kind:"sweep"` is still written by `export_sweep`, in which case add a test), `_EMPTY_FILLS`, `SimBroker.open_orders` reaching into `_book._resting` (add `OrderBook.resting()`) | `ui/server.py`, `oms/` |
| N7 | Fill IDs reuse the order counter (`ord-N`) → use a separate `fill-N` counter. Carry `intent.tag` into `Order.tag` → trade `tag` (today it is the order id) | `oms/sim_broker.py`, `report/trades.py` |
| N8 | `scripts/migrate_runs_v2.py` (646 lines, one-off) → move it to `scripts/migrations/2026_09_v2.py`. The library must not import from `scripts/` | `scripts/` |
| N9 | Frontend pages > 450 lines (`ComparePage` 700, `GroupPage` 562): move pure logic (best-value highlight, knob effects, heat aggregation) into `src/lib/*.js` with unit tests. Pages keep only layout | `frontend/src` |

---

## 5. Order of work

1. H1 (one commit).
2. C1 → C11 (one commit each, failing-first test in `tests/test_engine_correctness.py`).
3. R1 → R3.
4. G0 (snapshot on the post-R3 commit), then F1 → F7. Each commit must pass G0 unchanged.
5. N1 → N9. Each commit must pass G0 unchanged.
6. Update `docs/UI.md` and `README.md` for new config options: `halt_drawdown`, `allow_leverage`, `fill_on` values, `close_at_end`, `lookahead_check`, `instrument.timezone` / `session_close`.

## 6. Verify before you trust (add to QUESTIONS.md, do not change code)
- `IndianOptionCharges`: STT 0.15% on option sales from 2026-04-01 and the exchange rates by date. Check them against the official NSE/BSE circulars and cite the circular numbers in the docstring.
- `options/replay.py` fills at the next-minute **open** with `valid()` requiring volume > 0. That is a coarse liquidity proxy (the docstring says so). Consider a spread/volume-aware slippage model later. **Not in scope.**

## 7. Repro scripts (put in `tests/test_engine_correctness.py` as tests)

```python
import numpy as np, pandas as pd
from stolgo import Backtest, Strategy
idx = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
def frame(px, spread=1.0):
    px = np.asarray(px, float)
    return pd.DataFrame({"open": px, "high": px + spread, "low": px - spread, "close": px, "volume": 1.0}, index=idx[:len(px)])

# (a) C1 short round trip → today: 0 trades
class ShortRT(Strategy):
    def on_bar(self, ctx):
        if ctx.i == 2: ctx.sell(qty=10)
        if ctx.i == 6: ctx.buy(qty=10)
r = Backtest(ShortRT(), frame([100,101,102,103,104,103,102,101,100,99]), cash=10_000).run()
# expect: len(r.trades) == 1, side SHORT, entry 103, exit 101, gross 20

# (b) C2 exit blocked by 50% gate → today: qty 100 at end, 0 trades
class Hold(Strategy):
    def on_bar(self, ctx):
        if ctx.i == 0: ctx.buy(qty=100)
        if ctx.i == 4: ctx.close()
r = Backtest(Hold(), frame([100,100,40,40,40,30,30,30,30,30], 0), cash=10_000).run()
# expect: r.positions.qty.iloc[-1] == 0 and len(r.trades) == 1

# (c) C3 overdraft → today: min cash −5,015
class AllIn(Strategy):
    def on_bar(self, ctx):
        if ctx.i == 0: ctx.buy(size_pct=1.0)
r = Backtest(AllIn(), frame([100]+[150]*9, 0), cash=10_000, commission=0.001).run()
# expect: (r.positions.equity - r.positions.qty * close).min() >= 0

# (d) C5 fill_on="close" → today: fills 102.2 (bar 2), not 101.2 (bar 1)
# (e) R1/R2: long 100 units 100→70→101 over 30 days, export_all → today max_drawdown 0.0, sharpe 3.0, exchange NSE
# (f) F1–F3 benchmark: 200_000 1-min bars, random walk seed 1, 50-bar momentum → today 27.6 s
```
