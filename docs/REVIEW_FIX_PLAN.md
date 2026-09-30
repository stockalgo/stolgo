# Review Fix Plan — `codex/backtest-ui-wiring`

Status: ready for implementation
Source: code review of branch `codex/backtest-ui-wiring` (2026-09-27)
Audience: an implementation agent. Follow steps literally. Do not improvise scope.

---

## 0. Rules for the implementer (read first)

1. **Do one task at a time, in the order listed.** Finish its tests before starting the next task.
2. **Line numbers in this doc are hints only.** Always locate code by searching for the quoted anchor text (e.g. `grep -n "getEffectiveVol" frontend/src/utils/resample.js`).
3. **Only touch the files named in the task.** The working tree has other uncommitted changes from other work. Never revert, reformat, or "clean up" anything you were not asked to change.
4. **Do not add npm or pip dependencies.** Frontend tests use Node's built-in `node:test` (Node 22 is installed).
5. **Do not commit or push** unless the person running you explicitly asks.
6. **If a step is ambiguous or a test you did not write starts failing, stop and report.** Do not edit unrelated tests to make them pass.
7. Match surrounding code style: 4-space Python with type hints; 2-space JS, double quotes, semicolons.

### Commands

| Purpose | Command (run from repo root unless noted) |
|---|---|
| Python tests (all) | `uv run pytest -q` |
| Python tests (one file) | `uv run pytest -q tests/<file>.py` |
| Frontend unit tests | `cd frontend && npm test` (added in Task 4) |
| Frontend build check | `cd frontend && npm run build` |

A task is **done** only when: its new tests pass, `uv run pytest -q` passes, and (for frontend tasks) `npm run build` succeeds with no new errors.

---

## Phase 1 — Python backend

### Task 1: STOP_LIMIT orders never fill

**File:** `lib/stolgo/oms/order_book.py`
**New test file:** `tests/test_oms_order_book.py`

**Problem:** `add()` accepts `OrderType.STOP_LIMIT` into the resting book, but `match()` has no branch for it. Such orders sit in the book forever and never fill.

**Required semantics (implement exactly):**

- A STOP_LIMIT order has two prices: `stop_price` (trigger) and `limit_price` (worst acceptable fill).
- **BUY**: triggers on a bar where `bar.high >= stop_price`. Trigger price = `max(bar.open, stop_price)`.
  - If trigger price `<= limit_price` → fill at the trigger price on this bar.
  - Otherwise (gapped above the limit) → do **not** fill on this bar; mark the order as *triggered* and keep it resting.
- **SELL**: triggers when `bar.low <= stop_price`. Trigger price = `min(bar.open, stop_price)`.
  - If trigger price `>= limit_price` → fill at the trigger price.
  - Otherwise mark triggered and keep resting.
- Once triggered, on later bars the order behaves **exactly like a LIMIT order** (same logic as the existing LIMIT branch: BUY fills at `limit_price` if `bar.low <= limit_price`; SELL fills at `limit_price` if `bar.high >= limit_price`).
- `Order` is a frozen dataclass, so track triggered state in the book: `self._triggered: set[str]` of order ids.
- `cancel()` must also remove the id from `_triggered`. When an order fills, remove its id from `_triggered`.
- `add()` must raise `ValueError` if a STOP_LIMIT order is missing `stop_price` or `limit_price`. Do **not** add validation for other order types (out of scope).

**Implementation — replace the class body with this (keep the file's header comment and imports):**

```python
class OrderBook:
    def __init__(self) -> None:
        self._resting: list[Order] = []
        self._triggered: set[str] = set()

    def add(self, order: Order) -> None:
        if order.order_type == OrderType.STOP_LIMIT and (
            order.stop_price is None or order.limit_price is None
        ):
            raise ValueError("STOP_LIMIT order requires both stop_price and limit_price")
        if order.order_type in (OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT):
            self._resting.append(order)

    def cancel(self, order_id: str) -> None:
        self._resting = [o for o in self._resting if o.order_id != order_id]
        self._triggered.discard(order_id)

    def match(self, bar: Bar) -> list[tuple[Order, float]]:
        filled: list[tuple[Order, float]] = []
        remaining: list[Order] = []
        for order in self._resting:
            price = None
            if order.order_type == OrderType.LIMIT and order.limit_price is not None:
                price = self._limit_fill(order, bar)
            elif order.order_type == OrderType.STOP and order.stop_price is not None:
                if order.side == Side.BUY and bar.high >= order.stop_price:
                    price = max(bar.open, order.stop_price)
                elif order.side == Side.SELL and bar.low <= order.stop_price:
                    price = min(bar.open, order.stop_price)
            elif order.order_type == OrderType.STOP_LIMIT:
                price = self._stop_limit_fill(order, bar)
            if price is not None:
                filled.append((order, price))
                self._triggered.discard(order.order_id)
            else:
                remaining.append(order)
        self._resting = remaining
        return filled

    @staticmethod
    def _limit_fill(order: Order, bar: Bar) -> float | None:
        limit = order.limit_price
        if limit is None:
            return None
        if order.side == Side.BUY and bar.low <= limit:
            return limit
        if order.side == Side.SELL and bar.high >= limit:
            return limit
        return None

    def _stop_limit_fill(self, order: Order, bar: Bar) -> float | None:
        stop, limit = order.stop_price, order.limit_price
        if stop is None or limit is None:
            return None
        if order.order_id in self._triggered:
            return self._limit_fill(order, bar)
        if order.side == Side.BUY:
            if bar.high < stop:
                return None
            trigger_px = max(bar.open, stop)
            if trigger_px <= limit:
                return trigger_px
        else:
            if bar.low > stop:
                return None
            trigger_px = min(bar.open, stop)
            if trigger_px >= limit:
                return trigger_px
        # Triggered but gapped through the limit: rest as a limit order from next bar.
        self._triggered.add(order.order_id)
        return None
```

**Tests to write in `tests/test_oms_order_book.py`:**

Helpers:
```python
import pytest

from stolgo.core.types import Bar, Order, OrderType, Side
from stolgo.oms.order_book import OrderBook


def _bar(o: float, h: float, l: float, c: float, ts: int = 1) -> Bar:
    return Bar(ts=ts, open=o, high=h, low=l, close=c, volume=1.0, symbol="X")


def _stop_limit(side: Side, stop: float, limit: float, oid: str = "o1") -> Order:
    return Order(
        order_id=oid, symbol="X", side=side, order_type=OrderType.STOP_LIMIT,
        qty=1.0, limit_price=limit, stop_price=stop,
    )
```

Test cases (one `def test_...` each):

| # | Setup | Bars | Expected |
|---|---|---|---|
| 1 | BUY stop 110 limit 112 | `_bar(108, 111, 107, 110.5)` | 1 fill at **110.0**; book empty after |
| 2 | BUY stop 110 limit 112 | `_bar(105, 109, 104, 108)` | no fill; order still resting (a second `match` with `_bar(108, 111, 107, 110.5)` fills at 110.0) |
| 3 | BUY stop 110 limit 112, gap | bar A `_bar(115, 116, 113, 114)` then bar B `_bar(113, 114, 111.5, 113)` | A: no fill. B: fill at **112.0** |
| 4 | SELL stop 90 limit 88 | `_bar(92, 93, 89, 89.5)` | fill at **90.0** |
| 5 | SELL stop 90 limit 88, gap | bar A `_bar(85, 86, 84, 85)` then bar B `_bar(86, 88.5, 85, 88)` | A: no fill. B: fill at **88.0** |
| 6 | cancel after trigger | BUY stop 110 limit 112; match gap bar `_bar(115,116,113,114)`; `book.cancel("o1")` | next `match(_bar(111,112,110,111))` returns `[]` and `book._triggered == set()` |
| 7 | validation | STOP_LIMIT with `limit_price=None` | `book.add(...)` raises `ValueError` |

Then run `uv run pytest -q tests/test_oms_order_book.py tests/test_oms_sim_broker.py tests/test_options_replay.py` and the full suite.

---

### Task 2: `normalize_ohlcv` raises wrong exception type

**File:** `lib/stolgo/data/normalize.py`
**Test file:** `tests/test_data_normalize.py` (append)

**Problem:** `work = work[cols].astype("float64")` raises a raw `ValueError`/`TypeError` for non-numeric strings. The module's contract is to raise `DataError`.

**Change:** find the line `work = work[cols].astype("float64")` and replace with:

```python
    try:
        work = work[cols].astype("float64")
    except (TypeError, ValueError) as exc:
        raise DataError(f"non-numeric values in OHLCV columns: {exc}") from exc
```

**Test:** build a small valid OHLCV DataFrame the same way existing tests in `tests/test_data_normalize.py` do (copy their fixture pattern), set one `close` value to the string `"abc"`, and assert `pytest.raises(DataError)`. Import `DataError` from the same place the existing tests do.

---

### Task 3: Trade side detection is wrong for long structures and NaN

**File:** `lib/stolgo/ui/adapters.py`
**Test file:** `tests/test_ui_adapters.py` (append new test functions; do not change existing assertions)

**Problem:**
- Any tag containing `straddle`/`strangle`/`condor` becomes `"Short"`, even `long_straddle`.
- A `side` value of `NaN` passes `if not side` (NaN is truthy) and becomes the string `"nan"`.
- A `tag` value of `NaN` becomes the string `"nan"`.

**Change:** add this helper above `def trades(`:

```python
def _trade_side(row) -> str:
    raw = row.get("side")
    if raw is not None and not (isinstance(raw, float) and pd.isna(raw)):
        if isinstance(raw, (int, float)):
            return "Short" if raw < 0 else "Long"
        text = str(raw).strip().lower()
        if text in ("long", "buy"):
            return "Long"
        if text in ("short", "sell"):
            return "Short"
    tag = _clean_tag(row.get("tag"))
    lowered = tag.lower()
    if "long" in lowered:
        return "Long"
    if any(k in lowered for k in ("short", "strangle", "straddle", "condor")):
        return "Short"
    return "Long"


def _clean_tag(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)
```

In `trades()`:
- Delete the whole block starting `side = row.get("side")` through `side = "Long"` (the `if not side:` block).
- Replace `"side": str(side),` with `"side": _trade_side(row),`.
- Replace `"tag": str(row.get("tag") or ""),` with `"tag": _clean_tag(row.get("tag")),`.

**Tests** (reuse the DataFrame pattern already used in `test_ui_adapters.py` for `options_trades_df`):

| Row input | Expected `side` | Expected `tag` |
|---|---|---|
| `tag="long_straddle"`, no side column | `"Long"` | `"long_straddle"` |
| `tag="strangle_0dte"`, no side column | `"Short"` (existing test must still pass) | |
| `side=float("nan")`, `tag="short_strangle"` | `"Short"` | |
| `side="SELL"`, `tag="x"` | `"Short"` | |
| `side=-1.0`, `tag=""` | `"Short"` | |
| `tag=float("nan")`, no side column | `"Long"` | `""` |

---

## Phase 2 — Frontend pure utilities (unit-testable)

### Task 4: Add a zero-dependency frontend test runner

**File:** `frontend/package.json`

Add to `"scripts"`:
```json
"test": "TZ=UTC node --test"
```
`TZ=UTC` is deliberate: it makes the browser-timezone bug in Task 5 reproducible. Node automatically finds files named `*.test.js`. Put all new frontend tests under `frontend/tests/`.

Create `frontend/tests/smoke.test.js`:
```js
import { test } from "node:test";
import assert from "node:assert/strict";

test("runner works", () => {
  assert.equal(1 + 1, 2);
});
```
Run `cd frontend && npm test`. It must pass. Then delete `smoke.test.js` once Task 5 has real tests.

---

### Task 5: Fix `resample.js` — weekly timezone bug, O(n²) volume lookup, fake volume

**File:** `frontend/src/utils/resample.js`
**New test file:** `frontend/tests/resample.test.js`

**Problems:**
1. Weekly bucket uses browser-local `getDay()`/`setDate()` but formats in the chart timezone → weeks split on the wrong day when browser TZ ≠ chart TZ.
2. `getEffectiveVol` does `volume.find(...)` per candle → O(n²).
3. When data has no real volume, the function **invents** volume from candle range (min 1,250). Chart, legend, Volume MA and VWAP then show fake data as real.

**New contract:** `resampleCandles(...)` returns `{ candles, volume, hasVolume }`.
- `hasVolume` is `true` only if the input has at least one `value > 0`.
- If `hasVolume` is `false`, `volume` is `[]`. **Never synthesize volume.**

**Implementation steps:**

1. Add this top-level helper (above `resampleCandles`):
```js
// Monday (YYYY-MM-DD) of the week containing `ts`, evaluated in `timeZone`.
// Weekday math is done in UTC so the browser's own timezone cannot leak in.
export function weekStartKey(ts, timeZone) {
  const localDate = new Date(ts * 1000).toLocaleDateString("en-CA", { timeZone });
  const [y, m, d] = localDate.split("-").map(Number);
  const utc = new Date(Date.UTC(y, m - 1, d));
  const day = utc.getUTCDay() || 7; // Monday=1 ... Sunday=7
  utc.setUTCDate(utc.getUTCDate() - day + 1);
  return utc.toISOString().slice(0, 10);
}
```
2. In `getBucketKey`, replace the whole `if (targetTf === "1W") { ... }` block with:
```js
    if (targetTf === "1W") {
      return weekStartKey(ts, timeZone);
    }
```
3. Delete `getEffectiveVol` entirely. Replace `hasRealVolume` handling with:
```js
  const hasVolume = Array.isArray(volume) && volume.some((v) => v.value > 0);
  const volMap = new Map();
  if (hasVolume) {
    for (const v of volume) volMap.set(v.time, v.value);
  }
```
   (Remove the later duplicate `const volMap = new Map(); for (const c of candles) ...` loop.)
4. Early return when target ≤ base interval becomes:
```js
  if (tfConfig.seconds <= baseInterval) {
    return { candles, volume: hasVolume ? volume : [], hasVolume };
  }
```
5. In the bucketing loop, `const barVol = volMap.get(bar.time) || 0;` stays. Only push to `resampledVolume` when `hasVolume` is true (wrap both `resampledVolume.push(...)` calls in `if (hasVolume)`).
6. Empty-input return becomes `{ candles: [], volume: [], hasVolume: false }`. Final return becomes `{ candles: resampledCandles, volume: resampledVolume, hasVolume }`.
7. `grep -rn "resampleCandles" frontend/src` — confirm the only caller is `TradingCharts.jsx` (handled in Task 8). If there are others, update them to tolerate `volume: []`.

**Tests (`frontend/tests/resample.test.js`)** — import from `../src/utils/resample.js`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { resampleCandles, weekStartKey } from "../src/utils/resample.js";

const ist = (iso) => Date.parse(`${iso}+05:30`) / 1000;
const bar = (time, o = 100) => ({ time, open: o, high: o + 2, low: o - 2, close: o + 1 });
```

| Test | Input | Assert |
|---|---|---|
| weekStartKey Monday IST midnight | `weekStartKey(ist("2024-06-10T00:00:00"), "Asia/Kolkata")` | `"2024-06-10"` |
| weekStartKey Sunday | `weekStartKey(ist("2024-06-16T10:00:00"), "Asia/Kolkata")` | `"2024-06-10"` |
| weekly buckets correct under TZ=UTC | daily IST candles at 00:00 for 2024-06-10..14 (Mon–Fri, opens 100..104) and 2024-06-17 (open 105); `resampleCandles(c, [], "1W", "Asia/Kolkata")` | 2 candles; first `.open === 100`, first `.time === ist("2024-06-10T00:00:00")`; second `.open === 105` |
| no volume → no fake volume | 15m candles, `volume=[]`, target `"1h"` | `hasVolume === false`, `volume.length === 0` |
| real volume summed | four 15m candles, volume values 1,2,3,4, target `"1h"` (all inside one hour bucket, e.g. starting at an exact hour in UTC seconds) | one volume point with `value === 10`, `hasVolume === true` |
| performance | 100,000 one-minute candles (`time = 1_700_000_000 + i*60`) with volume `value: 1`, target `"15m"` | completes in < 1000 ms (`performance.now()`) |

---

### Task 6: CSV export — quoting and `#` truncation

**New file:** `frontend/src/utils/csv.js`
**Edit:** `frontend/src/App.jsx` (the export handler — search for `data:text/csv`)
**New test:** `frontend/tests/csv.test.js`

**Create `csv.js`:**
```js
export function csvCell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function toCsv(headers, rows) {
  return [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
}

export function downloadCsv(filename, text) {
  const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
```

**In `App.jsx`:** import `{ downloadCsv, toCsv }` from `"./utils/csv"`. Replace everything from `const csvContent = "data:text/csv...` through `document.body.removeChild(link);` with:
```js
    downloadCsv(`${selectedRunId || "trades"}.csv`, toCsv(headers, rows));
```
Keep the `headers` and `rows` definitions and the `setExportState` lines unchanged.

**Tests:**
- `csvCell("a,b") === '"a,b"'`
- `csvCell('say "hi"') === '"say ""hi"""'`
- `csvCell("leg#2") === "leg#2"`
- `csvCell(null) === ""`, `csvCell(-12.5) === "-12.5"`
- `toCsv(["a","b"], [[1,"x,y"]]) === 'a,b\n1,"x,y"'`

(Do not test `downloadCsv` — it needs a DOM.)

---

## Phase 3 — `TradingCharts.jsx` and chart components

All edits in this phase are in `frontend/src/components/charts/`. There are no unit tests for React components; verify with `npm run build` plus the manual checks listed per task. Do tasks 7→10 in order; each is small.

### Task 7: Selecting a trade rebuilds all charts and resets zoom

**File:** `TradingCharts.jsx`

**Problem:** the big chart-building `useEffect` lists `selectedTrade` in its dependency array, so every trade click destroys/recreates every chart and calls `fitContent()` (user loses zoom).

**Steps:**
1. Near the other `useRef` calls at the top of the component (`const chartsRef = useRef(null);`), add:
   ```js
   const selectedTradeRef = useRef(selectedTrade);
   ```
2. Inside the big effect, **delete** the line `const selectedTradeRef = { current: selectedTrade };`. `updateDrawing` will now read the component-level ref (same name, no other change needed).
3. In `updateDrawing`, change the first guard so clearing the selection clears the overlay:
   ```js
      const trade = selectedTradeRef.current;
      if (!trade) {
        setDrawing(null);
        return;
      }
      if (!overlayRef.current || !activeCandles.length) return;
   ```
4. In the `chartsRef.current = { ... }` object, delete the `selectedTradeRef,` property.
5. In `priceChart.subscribeClick`, change the reduce seed from `{ trade: selectedTrade, distance: ... }` to `{ trade: null, distance: Number.POSITIVE_INFINITY }`.
6. In the dependency array of the big effect, **remove** `selectedTrade,`. Leave all other deps.
7. Replace the small sync effect (search `chartsRef.current.selectedTradeRef.current = selectedTrade`) with:
   ```js
  useEffect(() => {
    selectedTradeRef.current = selectedTrade;
    if (chartsRef.current) requestAnimationFrame(chartsRef.current.updateDrawing);
  }, [selectedTrade]);
   ```
8. `grep -n "selectedTrade" TradingCharts.jsx` — confirm no remaining reference to `chartsRef.current.selectedTradeRef`.

**Manual check:** zoom into a week, click a trade row → trade path draws, zoom is preserved.

---

### Task 8: Resizer saves the old height

**File:** `TradingCharts.jsx`, function `handleResizerMouseDown`

**Steps:**
1. After `const startHeight = chartHeight;` add `let latestHeight = startHeight;`.
2. In `onMouseMove`, after computing `newHeight`, add `latestHeight = newHeight;`.
3. In `onMouseUp`, change `String(chartHeight)` to `String(latestHeight)`.

**Manual check:** drag chart taller, reload page → new height persists.

---

### Task 9: Legend change% is wrong while hovering

**Files:** `TradingCharts.jsx`, `ChartLegend.jsx`

**Problem:** legend always computes change vs the dataset's second-to-last candle, even when hovering an old candle.

**Steps in `TradingCharts.jsx`:**
1. Initial state: `useState({ candle: null, prevCandle: null, vol: null, indicators: {} })`. Also add `prevCandle: null` in the `setHoverData(...)` reset call inside `subscribeCrosshairMove`.
2. In `subscribeCrosshairMove`, replace
   ```js
      const candle = activeCandles.find((item) => item.time === param.time);
      if (!candle) return;
   ```
   with
   ```js
      const idx = activeCandles.findIndex((item) => item.time === param.time);
      if (idx === -1) return;
      const candle = activeCandles[idx];
      const prevCandle = idx > 0 ? activeCandles[idx - 1] : null;
   ```
   and change `setHoverData({ candle, vol: hoverVol, indicators: indVals })` to `setHoverData({ candle, prevCandle, vol: hoverVol, indicators: indVals })`.
3. In the `<ChartLegend ... />` JSX, add prop `hoverPriorCandle={hoverData.prevCandle}`.

**Steps in `ChartLegend.jsx`:**
1. Add `hoverPriorCandle,` to the destructured props.
2. Replace the two lines computing `change`/`changePct` with:
   ```js
  const baseCandle = hoverCandle ? hoverPriorCandle : priorCandle;
  const change = displayCandle && baseCandle ? displayCandle.close - baseCandle.close : 0;
  const changePct = baseCandle ? change / baseCandle.close : 0;
   ```

**Manual check:** hover an old candle → change equals that candle's close minus the previous candle's close.

---

### Task 10: Use the new volume contract and the selected timezone in charts

**Files:** `TradingCharts.jsx`, `GoToDateModal.jsx`, `frontend/src/pages/StrategyDetailPage.jsx`, `frontend/src/pages/FullScreenChartPage.jsx`

**Problems:** charts ignore the timezone toggle (hard-coded `getFormattingConfig().timeZone` read inside memos without a dependency); go-to-date assumes IST; charts must stop showing volume/VWAP/Volume-MA when there is no real volume (Task 5 contract).

**Steps:**
1. Pages: in both `StrategyDetailPage.jsx` and `FullScreenChartPage.jsx`, add `timeZone={timeZone}` to the `<TradingCharts ... />` element (both pages already receive a `timeZone` prop).
2. `TradingCharts.jsx`: add `timeZone = "Asia/Kolkata",` to the destructured props.
3. Resample memo:
   ```js
  const { candles: activeCandles, volume: activeVolume, hasVolume } = useMemo(() => {
    return resampleCandles(data.candles, data.volume, activeTf, timeZone);
  }, [data.candles, data.volume, activeTf, timeZone]);
   ```
4. Indicator memo: change the VWAP line to
   `if (hasVolume && activeIndicators.vwap && !activeIndicators.vwap.hidden) out.vwap = calculateVWAP(activeCandles, activeVolume, timeZone);`
   and the Volume MA line to
   `if (hasVolume && activeIndicators.volumeMa && !activeIndicators.volumeMa.hidden) out.volumeMa = calculateVolumeMA(activeVolume, 20);`
   Add `hasVolume` and `timeZone` to that memo's dependency array.
5. Big chart effect:
   - Change `if (subcharts.volume) {` (the one that creates `volumeSeries`) to `if (subcharts.volume && hasVolume) {`.
   - Change the price scale margin `bottom: subcharts.volume ? 0.22 : 0.12` to `bottom: subcharts.volume && hasVolume ? 0.22 : 0.12`.
   - Add `hasVolume` and `timeZone` to the dependency array (timeZone is needed so the axis `timeFormatter` re-renders with the new zone).
6. Legend `hoverVol` prop: change to
   `hoverVol={!hasVolume ? null : hoverData.vol ?? activeVolume.at(-1)?.value}`
   (`ChartLegend` already hides Vol when `hoverVol == null`).
7. Volume toggle button (search `Hide Volume Histogram`): add `disabled={!hasVolume}` and make the `title` `"No volume data for this instrument"` when `!hasVolume`.
8. Go-to-date handler: replace the body's first two lines (`if (!chartsRef.current ...` and `const targetTs = ...+05:30...`) with:
   ```js
    if (!chartsRef.current || !chartsRef.current.priceChart) return;
    let targetTs = exactTs;
    if (!targetTs) {
      const match = activeCandles.find(
        (c) => new Date(c.time * 1000).toLocaleDateString("en-CA", { timeZone }) >= dateStr,
      );
      targetTs = match ? match.time : activeCandles.at(-1)?.time;
    }
    if (!targetTs) return;
   ```
   (String comparison is valid because both sides are `YYYY-MM-DD`.)
9. Pass `timeZone={timeZone}` to `<GoToDateModal ... />`.
10. `GoToDateModal.jsx`: add `timeZone = "Asia/Kolkata"` prop. Replace every `timeZone: "Asia/Kolkata"` with `timeZone` (shorthand). Replace the label text `Select calendar date (IST)` with `` `Select calendar date (${getFormattingConfig().timeZoneName})` `` — import `getFormattingConfig` from `"../../utils/formatters"`.
11. `grep -n "05:30\|Asia/Kolkata" frontend/src/components/charts/` — the only remaining `Asia/Kolkata` occurrences should be prop defaults.

**Manual check:** toggle timezone → axis labels and daily/weekly candles update. Open an index run with zero volume → no volume bars, no VWAP, no Vol in legend, volume button disabled.

---

## Phase 4 — Currency

### Task 11: INR/USD toggle shows rupees as dollars

> **Decision taken in this plan:** there is no FX data in the system, so a display-currency toggle cannot be correct. Currency becomes a property of the run (from its manifest), and the toggle is removed. If the project owner prefers a real FX conversion instead, skip this task and raise it with them.

**Files:** `lib/stolgo/ui/adapters.py`, `tests/test_ui_adapters.py`, `frontend/src/App.jsx`, `frontend/src/components/AppNav.jsx`, `frontend/src/pages/FullScreenChartPage.jsx`

**Backend:**
1. In `run_summary`, add to the returned dict: `"currency": str(p.get("currency") or "INR"),`.
2. Test: `run_summary` with no `currency` param → `"INR"`; with `params={"currency": "USD", ...}` → `"USD"`. If an existing test asserts the exact key set of `run_summary`, add `"currency"` to that set.

**Frontend:**
1. `App.jsx`:
   - Delete `const [currency, setCurrency] = useState("INR");` and the whole `handleToggleCurrency` function.
   - After the `runs`/`selectedRunId` state, add:
     ```js
  const currency = runs.find((r) => r.id === selectedRunId)?.currency ?? "INR";
  useEffect(() => {
    setFormattingConfig({ currency });
  }, [currency]);
     ```
   - Remove every `onToggleCurrency={handleToggleCurrency}` prop. Keep passing `currency={currency}` where it is already passed.
2. `AppNav.jsx` and `FullScreenChartPage.jsx`: remove the `onToggleCurrency` prop and replace the toggle `<button>` with a non-interactive label, e.g. `<span className="nav-pill" title="Run currency">{currency}</span>` (reuse an existing class from the same file if one fits; do not add CSS).
3. `grep -rn "onToggleCurrency\|handleToggleCurrency" frontend/src` → no results.

---

## Phase 5 — Small cleanups

Each is independent and small. Verify with `npm run build`.

### Task 12: `RunAnalysisRail.jsx` — duplicate `signedMoney` and expiry pill on every row

**File:** `frontend/src/components/detail/RunAnalysisRail.jsx`
1. Delete the local `function signedMoney(value) { ... }`. Change the import line to `import { dateLabel, money, signedMoney } from "../../utils/formatters";`. Existing calls already pass `currency` as the second arg, which the shared version honors.
2. In the weekday list, delete `const isExpiry = detail?.params?.dte === 0;`, its preceding comment, and `{isExpiry && <span className="expiry-pill">Expiry</span>}`.
3. Directly under the "Day of Week PnL" `<h2>`'s parent `rail-heading` div, add:
   ```jsx
          {detail?.params?.dte === 0 && (
            <small>All sessions are expiry days (0-DTE run).</small>
          )}
   ```

### Task 13: `TradeTable.jsx` — lot-size guessing is unreliable

**File:** `frontend/src/components/detail/TradeTable.jsx`

Guessing lots with `qty % N` is ambiguous (e.g. SENSEX qty 40 = 4 lots of 10 or 2 lots of 20; the `% 20` branch is unreachable). Replace the body of `getLotInfo` with:
```js
  const getLotInfo = (qty) => {
    if (!qty) return "-";
    return String(Number(qty));
  };
```
and change its call site to `getLotInfo(trade.qty)`. (Showing real lot counts needs `lot_size` in the run manifest — out of scope; note it as a follow-up.)

### Task 14: `NewBacktestPage.jsx` — fake "Run Queued"

**File:** `frontend/src/pages/NewBacktestPage.jsx`

There is no backend endpoint to launch runs. Remove the fake success state:
1. Delete `const [submitted, setSubmitted] = useState(false);`, the `handleStart` function, and the `{submitted && ( ... )}` block.
2. Replace the header action button with:
   ```jsx
          <button className="primary-button" type="button" disabled title="Launching runs from the UI is not supported yet">
            Start run (coming soon)
          </button>
   ```
3. Below the `PageHeader`, add a `surface-panel` note: "Launching from the UI is not wired yet. Run backtests with the `stolgo` CLI; results appear here after they are written to `runs/`."

### Task 15: `ComparePage.jsx` — default selection never updates

**File:** `frontend/src/pages/ComparePage.jsx`

The default `selectedIds` is computed once at mount; if `runs` is still loading (empty), nothing is ever selected.
1. Change the React import to `import { useEffect, useState } from "react";`.
2. After the `selectedIds` state, add:
   ```js
  useEffect(() => {
    setSelectedIds((prev) => {
      const valid = prev.filter((id) => runs.some((r) => r.id === id));
      return valid.length ? valid : runs.slice(0, 4).map((r) => r.id);
    });
  }, [runs]);
   ```

---

## Final verification (run all, report output)

```bash
uv run pytest -q
cd frontend && npm test && npm run build
grep -rn "getEffectiveVol\|onToggleCurrency\|selectedTradeRef.current = selectedTrade;" frontend/src   # expect: only the new selectedTradeRef line in TradingCharts sync effect
```

Report back: list of tasks completed, any task skipped and why, and the tail of each command's output.

## Out of scope / follow-ups (do not implement)

- Real lot-count display (needs `lot_size` in manifest).
- Real FX conversion.
- A backend endpoint to launch runs from the UI.
- Crosshair handler still does linear `.find` lookups per mouse move; fine for now, revisit with Map lookups if large runs lag.
- Changing timeframe/theme still calls `fitContent()` and resets zoom (only the trade-click case is fixed here).
