# Plan 05 — Validation of Plan 04 (`feat/ui-cockpit` @ 47b95c0, 2026-10-01)

> Same rules as Plans 01–04: tasks **in order**, one commit per task `val-fix: <ID> — <title>`,
> failing-first test in `tests/test_engine_correctness.py` for every V1–V9 item, and
> `PYTHONPATH=lib pytest -q` plus `npm test --prefix frontend` green after every commit.
> Every bug below was **reproduced on HEAD**. The repro scripts are in §4.

## 1. What was verified OK (do not touch)

| Item | Evidence |
|---|---|
| H1 | A `git archive HEAD` copy installs and runs on clean Linux, Python 3.11: 183 passed, 1 failed (the golden test, see V6) |
| C1, C2, C5, C7, C10, C11, R1, R2, R3 | §7 repros give the expected results. R1: the 30-day 100→70→101 hold now shows MTM max DD −0.279 (it was 0.0). The C5 modes fill at 101.7 / 102.2 / 101.2, and `"close"` raises a DeprecationWarning |
| C4 | Prices pass through, limit gap improvement works, STOP_LIMIT raises, and OCO picks the stop |
| F1–F3 | Same machine, 200k bars: **27.5 s → 1.7 s** (16×). The on_bar strategy's final equity is identical (109504.9628). The vector strategy changes 119436.04 → 119429.22, which is expected from C3 (size_pct is now resolved at the fill price) |
| F4 | Full-range 1H candles take 3.75 s → ~90 ms on the same machine. The output is identical except for 2 extra hourly buckets on the Muhurat (evening) sessions of 2023-11-12 and 2024-11-01, which are now kept (more correct) |
| F5, F6 | Responses are identical across repeated calls (no cache poisoning). `useApi` is keyed everywhere |
| Data | `nifty-0dte-strangle-benchmark` through the API: Sharpe 0.733541, CAGR 0.053554, status ok (matches the fixture). The `runs/` manifests are untouched (mtime 2026-09-29) |
| Frontend | 13 test files / 65 tests pass, and the build passes |

The report's "27.60 s → 0.37 s" mixes two machines. Quote **16× on the same machine** instead.

---

## 2. Must fix: backtest correctness

### V1 — An orphan bracket exit opens a phantom reverse position
The stop/target of a bracket stay resting after the position is closed by `ctx.close()`, the end-of-data close, or anything else. When price later touches them, they **open a new position in the opposite direction**.
Repro §4-a: long bracket, stop 95, `ctx.close()` on bar 2, price hits 94 on bar 5 → an extra **SHORT 40 @94** trade.
**Fix:**
1. Add `Order.reduce_only: bool = False`. Bracket exit orders set it to True.
2. In `SimBroker._make_fill`, a reduce_only order fills only up to `abs(position)` and only in the closing direction. When the position is flat or on the same side, cancel the order and its OCO siblings (no fill).
3. When any fill makes the position flat, cancel all resting reduce_only orders for that symbol.

**Test:** the §4-a repro gives 1 trade and is flat at the end, with no SHORT row.

### V2 — `fill_on="next_close"`: bracket exits match the high/low of bars that happened before the entry
The entry fills at bar *i* **close**. `on_fill` then submits stop/target, and the engine's pre-bar block matches them against bar *i*'s high/low, which happened earlier in that bar. This is look-ahead (here it fabricates a loss).
Repro §4-b: the entry fills at 100 on bar 1, bar 1's low is 90, and the stop fills at 95 **on the same bar**.
**Fix:** add `Order.active_from: int` (bar index). `OrderBook.match` skips orders with `active_from > bar_index`. Orders created after a fill **at the close** (next_close, signal_close, end of data) get `active_from = i + 1`. Orders created after a fill at the open keep `active_from = i`.
**Test:** the §4-b repro does not exit on bar 1.

### V3 — `fill_on="signal_close"` never places bracket exits
`engine.py` (the `signal_close` block, ~line 221) calls `strategy.on_fill` but **not `ctx.on_fill(fe)`**, so the bracket's stop and target are never submitted.
Repro §4-c: the stop at 95 is touched on bar 2, but the trade exits at END_OF_DATA (94).
**Fix:** call `ctx.on_fill(fe)` there too. Factor the four copies of the "apply fill" loop in `Engine.run` into one `_apply_fills(fills)` helper so this cannot drift again. Child orders follow V2 (`active_from = i + 1`).
**Test:** the §4-c repro exits at 95 with `exit_reason` ending in `_stop`.

### V4 — Bracket size and R come from the signal close, not the fill (C6 is incomplete)
`long()`/`short()` compute `qty` and `risk_per_unit` from the **signal close**. Plan 04 C6 required `qty = equity × risk_pct / |fill − stop|`. The C6 test cannot catch this because its fill equals the signal close.
Repro §4-d: signal close 100, stop 95, fill at the gap-up open 102 → qty 40 (should be 28.57), and r_multiple −2.4 (the real value is −12/7 = −1.714).
**Fix:**
1. Add `Order.size_risk_pct` and `Order.risk_stop`. The broker resolves the qty **at fill**: `qty = equity × size_risk_pct / |fill_px − risk_stop|`, where equity = `cash + position × fill_px`. Set `Fill.risk_per_unit = |fill_px − risk_stop|`.
2. When the fill is at or through the stop (long `fill_px ≤ stop`, short `fill_px ≥ stop`), do not fill. Emit `ORDER_REJECTED` with the reason `gap_through_stop`.
3. Explicit `qty=` keeps today's behaviour, but `risk_per_unit` still comes from the fill.

**Tests:** the §4-d repro gives qty 28.5714 and r_multiple −1.7143. A gap through the stop gives no trade and one ORDER_REJECTED.

### V5 — `RunConfig.qty_step` is missing (C3 is incomplete)
`Backtest(..., qty_step=1)` raises `ValidationError: extra inputs are not permitted`.
**Fix:** add `qty_step: float | None = None`. Floor every qty resolved at fill (`size_pct`, V4 `size_risk_pct`) to the step. A qty of 0 after flooring → ORDER_REJECTED `below_qty_step`.
**Test:** the §7-c repro with `qty_step=1` gives qty 66 and cash ≥ 0.

### V6 — The golden test is platform-dependent, and the options snapshot tests nothing
- `test_golden_random_walk_200k` **fails on Linux x86** (Python 3.11.15, numpy 2.4.4, pandas 2.3.3) even at the G0 commit 4df1305 itself. The trade count (6175) and the final equity (119429.215734) match, so `"%.10g"` CSV hashing is hitting last-ULP differences.
  **Fix:** hash `trades.round(6).to_csv(index=False)` for every golden case. Regenerate the 5 values once, and note "hash format changed, no behaviour change" in the commit.
- `test_golden_options_manifest_snapshot` compares a file on disk in `runs/` with a fixture. It never runs export or migration code, and it silently passes on a clean clone (no `runs/`).
  **Fix:** check in one small v1 run under `tests/fixtures/v1_run/`. Run the migration function on it into `tmp_path`, then compare the stripped manifest with the fixture. No silent skip.

### V7 — Trade `tag` / `exit_reason` semantics (N7 is incomplete)
Today `tag = exit tag or entry tag or order_id` and `exit_reason = exit tag or "UNKNOWN"`. Both columns show the same value, an order id leaks out when there is no tag, and a plain `ctx.close()` gives `UNKNOWN`.
**Fix:**
- `tag` = the **entry** lot's tag, or None.
- `exit_reason` = the exit fill's tag, or `"SIGNAL"` when it is None.
- `END_OF_DATA` stays as it is.

Golden hashes change. Regenerate them in this commit and say why in the body.

### V8 — `halt_drawdown` trimming drops order fields
`apply_risk` rebuilds the trimmed `OrderIntent` by hand and loses `oco_group` and `risk_per_unit`. Use `dataclasses.replace(intent, qty=…)`.
**Test:** a trimmed intent keeps `oco_group`.

### V9 — `close_at_end=False`: `num_trades` counts the OPEN row
Repro §4-e: one closed trade plus one open trade → `num_trades: 2`.
**Fix:** count closed trades only, and add `diagnostics.open_at_end: {qty, mtm_pnl}`.

---

## 3. Should fix: speed and noise (behaviour-preserving, golden must stay unchanged)

| ID | What | Where |
|---|---|---|
| V10 | `trade_detail` runs `strftime` over all 23k ohlcv rows on **every inspector click** (150 of 160 ms). Select the session with `index.normalize() == day` on the tz-converted index, or `searchsorted`. Target < 15 ms | `ui/adapters.py::trade_detail` |
| V11 | Reconcile runs only when `runs_dir`'s mtime changes. Re-exporting an existing run id does not change it, so the summary goes stale. In `get_run`, also compare the manifest file's mtime with the index row's `mtime` and upsert if it is newer | `ui/server.py` |
| V12 | 3 `assert`s remain in `options/replay.py` (lines 151, 160, 175) → `raise AccountingError` | `options/replay.py` |
| V13 | `Any` is used without an import in `oms/sim_broker.py` and `trade/bracket.py`, `Bar` without an import in `core/engine.py`, and the `CloseFill` import is unused. This only works because of `from __future__ import annotations`. `ruff check lib --select F` must be clean | `oms/`, `trade/`, `core/` |
| V14 | The C9 probe is tested only on `FastMomentum`. Parametrise it over every `stolgo.pa.preset` and `examples/` strategy that sets masks, as Plan 04 C9 says | `tests/` |
| V15 | README: `lookahead_check` checks the `on_start` masks only, not `ctx.data`, so fix the text. Add the two Plan 04 §6 items (STT/exchange-rate circulars, the replay fill proxy) to `QUESTIONS.md`, which was not done | docs |
| V16 | `KitPage` is still emitted in the prod build. Use `import.meta.env.DEV` directly (not wrapped in `Boolean(typeof …)`) so Vite drops it. `"runs:list"` is cached forever, so the Library never shows a run created by the CLI: force a reload on Library mount. The main chunk is still 600 KB: lazy-load the chart components (lightweight-charts) | `frontend/src/router.jsx`, `LibraryPage.jsx` |

---

## 4. Repro scripts (turn each one into a test)

```python
import numpy as np, pandas as pd
from stolgo import Backtest, Strategy
from stolgo.trade import long
idx = pd.date_range("2024-01-01", periods=40, freq="D", tz="UTC")
def F(o, h, l, c): return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1.0}, index=idx[:len(o)])

class B(Strategy):                      # bracket on bar 0, stop = bar-0 low (95), 2 % risk of 10k
    def on_bar(self, ctx):
        if ctx.i == 0: long(ctx, stop="candle_low", size_risk_pct=0.02, rr=(1, 2))

# (a) V1: orphan exit → today: extra SHORT 40 @94
class BC(Strategy):
    def on_bar(self, ctx):
        if ctx.i == 0: long(ctx, stop=95.0, size_risk_pct=0.02, rr=(1, 2))
        if ctx.i == 2: ctx.close(tag="manual")
Backtest(BC(), F([100]*5+[94]*3, [101]*5+[95]*3, [99]*5+[93]*3, [100]*5+[94]*3), cash=10_000).run()

# (b) V2: next_close look-ahead → today: exits at 95 on bar 1 (bar-1 low 90 came BEFORE the close fill)
Backtest(B(), F([100]*4, [105, 101, 101, 101], [95, 90, 99, 99], [100]*4), cash=10_000, fill_on="next_close").run()

# (c) V3: signal_close bracket → today: exit END_OF_DATA 94, expected stop 95 on bar 2
Backtest(B(), F([100, 100, 96, 94], [105, 101, 97, 95], [95, 99, 94, 93], [100, 100, 96, 94]), cash=10_000, fill_on="signal_close").run()

# (d) V4: gap-up fill → today: qty 40, r -2.4; expected qty 28.5714, r -1.7143
Backtest(B(), F([100, 102, 101, 90], [105, 103, 102, 91], [95, 100, 100, 89], [100, 101, 101, 90]), cash=10_000).run()

# (e) V9: close_at_end=False → today num_trades 2 in export_all manifest; expected 1
```

## 5. Final check
- [ ] §4 a–e give the expected values, and the §7 repros from Plan 04 still pass.
- [ ] Golden is green on **both** macOS and Linux (run it in a `python:3.11` docker container or in CI).
- [ ] The `benchmark` mark still runs in < 3 s on the M-series Mac.
- [ ] `ruff check lib --select F` is clean, and `grep -rn "^\s*assert " lib/stolgo` is empty.
