# Plan 02 — UI revamp ("Cockpit")

> **Audience:** an implementing engineer or a smaller LLM. Build **exactly** what is described.
> The pictures in `docs/design/png/` are the visual contract. The HTML in `docs/design/mockups/`
> is the DOM/CSS contract. Where this text and a picture disagree, **this text wins**. Note the
> difference in `docs/plans/QUESTIONS.md`.
>
> **Branch:** `feat/ui-cockpit` (branch from `fix/data-contract-v2` after its step 6 is merged).
> **Depends on:** Plan 01 §4 (API contract v2). Do not start U3+ until `/api/runs` returns v2 summaries.

---

## 0. How to use the design files

| File | What it is | How to use it |
|---|---|---|
| `docs/design/png/*.png` | 1440 px wide screenshots of every page | Put each PNG next to your running page at 1440 px width and compare. Spacing, sizes, colours and copy must match. |
| `docs/design/mockups/*.html` | Static HTML/CSS for the same pages. Open it in a browser | Copy the markup structure and class names into JSX. Inspect it with devtools to read exact sizes. |
| `docs/design/tokens.css` | Design tokens (colours, type, spacing) | Copy **verbatim** to `frontend/src/styles/tokens.css`. |
| `docs/design/components.css` | Component classes | Copy **verbatim** to `frontend/src/styles/components.css`. Add new classes at the bottom only. |
| `docs/design/_build/` | Python that generated the mockups from real run data | Reference only. It shows exactly how each chart is computed (scales, bins, colours). |

Page ↔ picture map:

| Route | Picture(s) |
|---|---|
| `/` Library | `01-library.png` |
| `/runs/:id` Overview (price) | `02-run-overview.png` |
| `/runs/:id` Overview (equity segment) | `03-run-overview-equity.png` |
| `/runs/:id/trades` | `04-run-trades.png` |
| `/runs/:id/diagnostics` | `05-run-diagnostics.png` |
| `/runs/:id/chart` | `06-run-chart-fullscreen.png` |
| `/compare?ids=a,b,c,d` | `07-compare.png` |
| `/groups/:groupId` | `08-group-heatmap.png` |
| `/new` | `09-new-run.png` |
| (design system) | `10-components-states.png` |

---

## 1. Scope

### 1.1 New information architecture

| Old page (file) | New | Why |
|---|---|---|
| Library (`StrategyLibraryPage.jsx`) | **Library** `/` | Scatter + filters + honest ranking |
| Reports (`ReportsPage.jsx`) | **Removed**. Merged into Library | It duplicated Library as cards |
| Detail (`StrategyDetailPage.jsx` + rail) | **Run** `/runs/:id` with tabs Overview / Trades / Diagnostics | One place per run. The rail content is redistributed |
| Full-screen chart (`FullScreenChartPage.jsx`) | **Run chart** `/runs/:id/chart` | Kept and restyled |
| Compare (`ComparePage.jsx`) | **Compare** `/compare?ids=` | Aligned equity/drawdown + metric table with comparability rules |
| Optimization (`OptimizationPage.jsx`) | **Groups** `/groups` and `/groups/:id` | Sweeps saved as individual runs are shown as groups (heatmap) |
| New backtest (`NewBacktestPage.jsx`) | **New run** `/new` | An honest CLI command builder. The fake queue and fake checks are removed |

### 1.2 Removed features (delete the code, do not hide it)

- The **INR/USD toggle**. The API gives ₹. There is no FX conversion. Always show ₹.
- The **timezone toggle**. Always show IST. Label it once per page ("Times in IST").
- The **light theme**. v1 is dark only. Keep tokens so a light theme can be added later.
- **Fake data** in New backtest: "Run Queued…" timer, the static "Pre-run checks" ticks, "Estimated runtime 18s", and options not backed by the CLI.
- **Engine-internal stats** in the UI: "Candles", "Equity points", "Underwater bars".
- The **Volume** pane and the volume-based indicators (Volume, Volume MA, VWAP) **when every volume value is 0**. That is the case for index data.
- The `Export` button in the top nav. Trades CSV moves to the run page and uses the v2 columns.

### 1.3 Non-goals
Live trading, starting runs from the UI (`POST /api/runs` does not exist), user accounts, mobile layouts below 1024 px
(show the notice "Stolgo needs a window at least 1024 px wide" below that width).

---

## 2. Tech decisions (exact)

| Topic | Decision |
|---|---|
| Framework | Keep React 19 + Vite 6 (already in `frontend/package.json`). Keep JavaScript + JSX. Add **JSDoc typedefs** (§4.2) instead of TypeScript |
| Routing | Add `react-router-dom@7.9.x` (`npm i react-router-dom@^7.9.0`). Use `createBrowserRouter`. FastAPI already serves `index.html` for unknown paths? **No.** Add a SPA fallback in `server.py`: any GET that is not `/api/*` and not a static file returns `index.html` (see U2) |
| Fonts | `npm i @fontsource/ibm-plex-sans@^5 @fontsource/ibm-plex-mono@^5`. Import weights 400/500/600/700 (sans) and 400/500/600 (mono) in `main.jsx`. Remove the Google Fonts `@import` from `styles.css` |
| Charts | Keep `lightweight-charts@^5.2` for **time-series** charts (price candles, equity, drawdown, compare overlay, trade inspector). Use **hand-written SVG React components** for the small charts (histogram, monthly heatmap, scatter, group heat grid, meters, range band, waterfall). Add no other chart library |
| State | React state + URL search params. No Redux/Zustand. A tiny in-memory cache in the API layer (§4.3) |
| Styling | Plain CSS files: `tokens.css`, `components.css`, `pages.css` (page-specific layout only). No CSS-in-JS. No Tailwind |
| Tests | Add `vitest@^3`, `@testing-library/react@^16`, `@testing-library/jest-dom@^6`, `jsdom@^25`. Script `"test": "vitest run"` |
| Lint | Not in scope |

---

## 3. Target folder structure (create exactly this)

```
frontend/src/
  main.jsx                      # fonts + styles + <RouterProvider>
  router.jsx                    # route table (§6)
  styles/
    tokens.css                  # = docs/design/tokens.css
    components.css              # = docs/design/components.css
    pages.css                   # page grids only
  api/
    client.js                   # fetch wrapper + cache
    endpoints.js                # one function per endpoint (§4.1)
    types.js                    # JSDoc typedefs (§4.2)
  lib/
    format.js                   # all number/date formatting (§5)
    metrics.js                  # metric_defs lookup + formatMetric()
    verdict.js                  # verdict + status + insights rules (§7)
    colors.js                   # market×dte colour, series colours (read from CSS vars)
    url.js                      # query-param helpers
    indicators.js               # MOVE from utils/indicators.js (unchanged)
    resample.js                 # MOVE from utils/resample.js (unchanged)
  hooks/
    useApi.js
    useHotkeys.js
  components/
    shell/AppShell.jsx  Rail.jsx  TopBar.jsx  CommandPalette.jsx  MinWidthNotice.jsx
    ui/Button.jsx  Seg.jsx  Tabs.jsx  Chip.jsx  StatusBadge.jsx  VerdictPill.jsx  Panel.jsx
       Kpi.jsx  KpiStrip.jsx  KV.jsx  Meter.jsx  RangeBand.jsx  HBar.jsx  Banner.jsx
       EmptyState.jsx  Skeleton.jsx  Tooltip.jsx  DataTable.jsx  Pagination.jsx  CopyButton.jsx
    charts/CandleChart.jsx  EquityChart.jsx  DrawdownChart.jsx  PnlStepChart.jsx
           SessionChart.jsx  Histogram.jsx  MonthlyHeatmap.jsx  Scatter.jsx  HeatGrid.jsx
           CompareChart.jsx  Waterfall.jsx  IndicatorsMenu.jsx  GoToDateDialog.jsx
    run/RunHeader.jsx  RunTabs.jsx  EdgeIntegrity.jsx  TradeInspector.jsx  TradeRowDetail.jsx
        DataCoverage.jsx  ExitReasons.jsx  CostBreakdown.jsx  Stability.jsx  Extremes.jsx
        MonthlyConsistency.jsx  SignalFunnel.jsx  ValidationConfig.jsx
    library/LibraryFilters.jsx  LibraryScatter.jsx  Leaders.jsx  RunsTable.jsx
  pages/
    LibraryPage.jsx  RunLayout.jsx  RunOverviewPage.jsx  RunTradesPage.jsx
    RunDiagnosticsPage.jsx  RunChartPage.jsx  ComparePage.jsx  GroupsPage.jsx
    GroupPage.jsx  NewRunPage.jsx  NotFoundPage.jsx
  __tests__/                    # vitest files (§10)
```

**Delete** after U12: `App.jsx`, `components/AppNav.jsx`, `components/MetricCard.jsx`, `components/PageHeader.jsx`,
`components/charts/*` (old), `components/detail/*`, `data/*`, `pages/*` (old), `utils/*` (after moving the two files), `styles.css`.

---

## 4. Data layer

### 4.1 Endpoints (from Plan 01 §4). Implement in `api/endpoints.js`

```js
export const listRuns        = ()                 => get("/runs");                        // {items, warnings}
export const getRun          = (id)               => get(`/runs/${enc(id)}`);             // RunDetail
export const getDaily        = (id)               => get(`/runs/${enc(id)}/daily`);       // {rows}
export const getMonthly      = (id)               => get(`/runs/${enc(id)}/monthly`);     // {rows}
export const getTrades       = (id)               => get(`/runs/${enc(id)}/trades`);      // {rows, columns}
export const getTrade        = (id, tradeId)      => get(`/runs/${enc(id)}/trades/${tradeId}`); // {trade, legs, bars}
export const getCandles      = (id, tf, from, to) => get(`/runs/${enc(id)}/candles?${qs({tf, from, to})}`); // {rows, tf}
export const getEquity       = (id)               => get(`/runs/${enc(id)}/equity`);      // {rows} | 404
export const listGroups      = ()                 => get("/groups");                      // {items}
export const getGroup        = (gid)              => get(`/groups/${enc(gid)}`);          // {id,label,axes,runs}
export const auditUrl        = (id)               => `/api/runs/${enc(id)}/audit`;
```

`get()` throws `ApiError {status, detail, path}`. `detail` is read from the JSON `{"detail": …}` body when present.

### 4.2 JSDoc types (`api/types.js`). Copy the field lists from Plan 01 §4.1–4.6 exactly.

```js
/** @typedef {"ok"|"low_sample"|"short_window"|"data_issues"|"superseded"|"empty"} RunStatus */
/** @typedef {{id:string,name:string,status:RunStatus,status_reasons:string[],markets:string[],structure:string,dte:number[],
 *   group:{id:string|null,label:string|null,axes:Object},window:{start:string,end:string,sessions:number},capital:number,
 *   metrics:Object<string, number|null>,robustness:{p_net_positive:number|null,net_without_top5:number|null},
 *   data_quality:{trades_with_missing_data:number,trades_total:number},has:{ohlcv:boolean,legs:boolean,intraday_equity:boolean,audit:boolean},
 *   created_at:string}} RunSummary */
/** @typedef {RunSummary & {instrument:Object, config:Object, diagnostics:Object, metric_defs:MetricDef[]}} RunDetail */
/** @typedef {{key:string,label:string,unit:"inr"|"fraction"|"ratio"|"count"|"sessions"|"r",decimals:number,better:"higher"|"lower"|"none",help:string}} MetricDef */
```

### 4.3 `useApi(key, fetcher, deps)` hook

- Returns `{data, error, loading, reload}`.
- Module-level `Map` cache keyed by `key`. It holds resolved values for the page session and has no TTL. `reload()` clears that key.
- It ignores responses from stale calls (compare a request counter).
- When `error.status === 409 && error.detail === "run_not_migrated"`, the page renders `<EmptyState variant="not-migrated">`.

---

## 5. Formatting (`lib/format.js`). The only place numbers become strings

| Function | Input → Output (examples are test cases) |
|---|---|
| `inr(v, {signed=false, dec=0})` | `30330.69` → `₹30,331`; signed → `+₹30,331`; `-6014` → `−₹6,014` (U+2212); `123456789` → `₹12,34,56,789` (Indian grouping); `null`/`NaN` → `—` |
| `inrCompact(v)` | `53787` → `₹53.8k`; `1234567` → `₹12.3L`; `-8000` → `−₹8k` (use `k` < 1 lakh, `L` < 1 crore, `Cr` above) |
| `pct(v, {dec=1, signed=true})` | `0.168504` → `+16.9%`; `-0.095192` → `−9.5%`; `0` → `0.0%`; null → `—` |
| `ratio(v, dec=2)` | `0.733478` → `0.73`; `-0.004` → `0.00` (never `−0.00`); null → `—` |
| `count(v)` | `157` → `157`; `12000` → `12,000` |
| `sessions(v)` | `347` → `347 sessions` |
| `rmult(v)` | `0.6416` → `+0.64R`; null → `—` |
| `premium(v)` | `26.7` → `26.7` (1 decimal, no ₹) |
| `level(v)` | `23671.8` → `23,671.8` |
| `dateIST(epochSec)` | `1788771600` → `08 Sep 2026` |
| `timeIST(epochSec)` | → `09:30` |
| `sessionLabel("2026-09-08")` | → `08 Sep 2026`; short form `sessionShort` → `08 Sep` |
| `formatMetric(key, value, defs)` | Dispatches on `def.unit`: inr→`inr(signed if better!=="lower")`, fraction→`pct`, ratio→`ratio(def.decimals)`, count→`count`, sessions→`sessions`, r→`rmult` |

Colour rule for numbers: add class `pos` when `value > 0` and `better === "higher"`, `neg` when `value < 0`. **Never** colour counts,
ratios < 0 excepted. `max_drawdown` is always `neg` when < 0.

---

## 6. Routes (`router.jsx`)

```
/                          LibraryPage
/runs/:runId               RunLayout → index: RunOverviewPage
/runs/:runId/trades        RunLayout → RunTradesPage
/runs/:runId/diagnostics   RunLayout → RunDiagnosticsPage
/runs/:runId/chart         RunChartPage            (no AppShell. Full-screen)
/compare                   ComparePage             (?ids=a,b,c,d)
/groups                    GroupsPage
/groups/:groupId           GroupPage
/new                       NewRunPage
*                          NotFoundPage
```

`RunLayout` loads `getRun(runId)` once and passes it to children via `useOutletContext()`. It renders RunHeader + RunTabs + `<Outlet/>`.
Rail items → routes: Library `/`, Run → last opened run (remember it in `sessionStorage["stolgo.lastRun"]`, disabled if none),
Compare `/compare`, Groups `/groups`, New run `/new`. Mark the active item with `aria-current="page"`.

---

## 7. Domain rules (`lib/verdict.js`). Implement exactly and unit-test

### 7.1 Comparability
```js
export const MIN_TRADES = 100, MIN_SESSIONS = 252;
export const isComparable = (r) => r.metrics.num_trades >= MIN_TRADES && r.window.sessions >= MIN_SESSIONS
                                && !["empty","superseded"].includes(r.status);
```

### 7.2 Verdict (header pill). First match wins.

| # | Condition | Label | Style | Text |
|---|---|---|---|---|
| 1 | `num_trades === 0` | `NO TRADES` | muted | `Nothing to evaluate` |
| 2 | `num_trades < 30` | `EDGE · UNPROVEN` | amber | `Fewer than 30 trades` |
| 3 | `net_pnl <= 0` or `p_net_positive < 0.80` | `NO EDGE` | red | `P(net > 0) below 80%` or `Net P&L is not positive` |
| 4 | `net_without_top5 <= 0` | `EDGE · FRAGILE` | amber | `Profitable, but the best 5 trades carry it` |
| 5 | `p_net_positive < 0.95` or status ∈ {low_sample, short_window, data_issues} | `EDGE · FRAGILE` | amber | the first of: `{x}% forced data exits` (data_issues), `Only {n} trades` (low_sample), `Only {s} sessions` (short_window), `P(net > 0) is {p}%` |
| 6 | otherwise | `EDGE · ROBUST` | green | `Survives bootstrap and top-5 removal` |

When `p_net_positive` is null, skip the rules that use it.

### 7.3 Status badge
| status | label | class |
|---|---|---|
| ok | `OK` | `badge--ok` |
| low_sample | `Low sample` | `badge--low` |
| short_window | `Short window` | `badge--low` |
| data_issues | `Data issues` | `badge--warn` |
| superseded | `Superseded` | `badge--muted` |
| empty | `Empty` | `badge--muted` |
Tooltip = `status_reasons.join(" · ")`.

### 7.4 Auto-insight callout (Overview → Edge integrity, bottom). Pick the first rule that applies. It renders **one** sentence.
1. `hit_rate < 0.45 && payoff >= 1.5` → `Right-tail strategy: {hit}% hit rate, payoff {payoff}×. Cutting costs by ₹50 per trade adds {inr(50*num_trades)}.`
2. `hit_rate >= 0.6 && payoff < 1` → `Left-tail strategy: wins {hit}% of trades but a loss costs {1/payoff}× a win. Watch the worst day ({inr(worst_day)}).`
3. `fees / gross_pnl > 0.4` → `Costs take {pct} of gross profit.`
4. otherwise → no callout.

### 7.5 Colours (`lib/colors.js`)
`marketColor(markets, dte)`: a single market with one DTE → `--market-{nifty|sensex}-{0|1}`. Anything else → `--market-other`.
Compare slots 1–4 → `--series-1..4`. Read the values with `getComputedStyle(document.documentElement)` once, then cache them.

---

## 8. Page specifications

All pages sit in `AppShell` (60 px rail + 56 px top bar + `.page` with 24 px side padding and a 14 px gap) unless stated otherwise.
Grids below are CSS grid templates. Put them in `pages.css` under a class named after the page, e.g. `.p-run-overview__row1`.

### 8.1 Library `/` (`01-library.png`)

**Data:** `listRuns()`. All filtering, sorting and paging is client-side.

**URL state (all optional):** `?market=NIFTY&dte=0&structure=short_strangle&status=ok,low_sample,data_issues&group=validated-timing-3y&min=100&sort=sharpe&dir=desc&page=1&q=text`.
Defaults: `status=ok,low_sample,short_window,data_issues` (superseded and empty are hidden), `sort=sharpe`, `dir=desc`, `page=1`, `min=0`.

**Layout:**
1. Header row: eyebrow `LIBRARY`. H1 `{visible count} runs` (28 px/600). Sub-line: `{empty} empty and {superseded} superseded runs hidden · {n in largest group} belong to the {group label}` plus, **only when the number is > 0**, `· {k} of them have more than 5% forced data exits`. Right side: `Compare selected ({n})` (disabled when n < 2; navigates to `/compare?ids=…`) and the primary `New run` button (→ `/new`).
2. Info banner (blue, `.banner` with inline info colours as in the mockup). Show it only if at least one manifest has `migrated_at`: `All metrics use the calendar_daily basis: every exchange session, idle days included. {n} older runs were recomputed on {date of latest migrated_at}.` Link `Migration report →` opens `/api/migration-report` in a new tab. Hide the link if a `HEAD` request returns 404.
3. Grid `240px minmax(0,1fr)`:
   - **Filters panel** (`LibraryFilters`): Market chips (All/NIFTY/SENSEX), DTE chips (Any/0/1/2), Structure select (options from the data, with counts), Status checkboxes, each with a StatusBadge and a right-aligned count, Group select (Any + groups with counts), Min. trades range 0–160 step 10, and the callout text from the mockup.
   - **Right column**, grid rows:
     - Row A, grid `minmax(0,1fr) 380px`:
       - `LibraryScatter`. x = `|max_drawdown|` in % (0–55, ticks every 10). y = `total_return` in % (−55–+20, ticks every 15). Radius = `2.2 + sqrt(num_trades)*0.36`. Fill = `marketColor`. **Hollow** (fill none, stroke colour) when `num_trades < 100`. Dashed "sweet spot" rect for dd < 10 and return > 0.
         Hover → Tooltip (name, return, max DD, Sharpe, trades). Click → navigate to the run.
         Legend chips below it (5 colours + `Dashed box = …` + `○ hollow = < 100 trades`). Scale domains are fixed so the view is stable across filters.
       - `Leaders`: the top 6 of the **filtered** runs that pass `isComparable`, by Sharpe. Each row: rank, colour dot, name (ellipsis), Sharpe, return. Footer: a sentence naming how many higher-Sharpe runs were excluded and why.
     - Row B: `RunsTable` (DataTable, dense). Columns in order: select checkbox · **Run** (name + group chip, id underneath in mono 11 px, max width 300, ellipsis) · **Market · DTE** (dot + `NIFTY · 0D`) · **Status** · **Trades** · **Return** · **CAGR** (append ⚠ with a tooltip when `annualised_from_short_window`) · **Sharpe** (bold) · **Max DD** · **PF** · **P(>0)** (`p_net_positive` as a %).
       Sortable headers: all numeric columns and Run. Rows with `num_trades < 100` have `opacity:.78`. Row click → `/runs/:id`. Checkbox click does not navigate. At most 4 can be selected (a 5th click shows a toast "Compare holds 4 runs").
       Page size 25. Footer: `Showing a–b of N · sorted by {label} ↓` + Prev/Next.
4. Search box in the top bar (`CommandPalette` trigger): see §9.

**States:** loading → skeleton rows (8) and a skeleton scatter. Error → red banner + Retry. Zero results → EmptyState `No runs match these filters` + `Clear filters` button.

**Acceptance:** with today's data after migration the H1 reads `122 runs`. Status counts are 8 ok / 3 low_sample / 111 data_issues / 2 superseded / 4 empty (the 3 low_sample runs are the S/R one_lot_diagnostic runs, while the 12 legacy weekly runs have status data_issues due to unreconciled P&L). The default sort puts `combined-top3-weekly-calendar` first, with a `Data issues` badge. The Leaders #1 is `SENSEX 0DTE STATIC_LEG100_CLOSE_ALL` (0.78).

### 8.2 Run layout `/runs/:runId`

**Data:** `getRun(runId)`. **RunHeader** (`02-run-overview.png`, top):
- Line 1: StatusBadge + eyebrow `RUN · {id}`.
- H1 = `name` (30 px/600).
- Chips: markets joined `+` · `{structure label} · {dte list} DTE` · `{num_trades} trades` · `{window.start as 14 Sep 2023} → {window.end} · {sessions} sessions` · `Capital {inr(capital)}` · `Entry {HH:MM} · Exit {HH:MM} IST`. The last chip is shown **only** if every trade has the same entry and exit clock time. That comes from `diagnostics` if present, otherwise it is hidden.
- The VerdictPill on the right (§7.2).
**RunTabs:** `Overview`, `Trades {num_trades}`, `Diagnostics`. Right side buttons: `Add to compare` (adds the id to `sessionStorage["stolgo.compare"]`, max 4, toast), `Audit report` (only if `has.audit`; opens `auditUrl` in a new tab), `Trades CSV` (client-side CSV of `getTrades` rows with the v2 column names exactly).
Breadcrumb in the top bar: `Library / {group label or "markets · structure"} / {id}`.

### 8.3 Overview tab (`02`, `03`)

**Data:** `getRun` (from context), `getDaily`, `getMonthly`, `getTrades`, `getCandles(id,"1D")` if `has.ohlcv`, and `getTrade(id, lastTradeId)` for the inspector.

Row 1: **KpiStrip**, 6 cells, in this order and with these sub-lines:
| Cell | Value | Sub-line |
|---|---|---|
| Net P&L | `inr(net_pnl, signed)` coloured | `{pct(total_return)} on capital` |
| CAGR | `pct(cagr)` (⚠ in label if short window) | `calendar · {years to 1 dp} yrs` or, if short window, `from {sessions} sessions · not comparable` in amber |
| Sharpe | `ratio(sharpe)` | `Sortino {ratio(sortino)} · daily, √252` |
| Max drawdown | `pct(max_drawdown)` neg | `{max_drawdown_duration} sessions underwater` |
| Profit factor | `ratio(profit_factor)` or `—` | `payoff {ratio(payoff)}×` |
| Hit rate | `pct(hit_rate,{signed:false})` | `{W} W · {L} L · {inr(expectancy)} / trade` (W = round(hit_rate·n), L = n − W − zero-P&L trades) |

Row 2: grid `minmax(0,1fr) 330px`.
- **Chart panel** (`Panel`). Header: `Seg` [Price · candles | Equity · drawdown]. The segment state is saved in `?view=price|equity`, default `price`; if `!has.ohlcv` the default is `equity` and the Price segment is disabled with the tooltip "No price data exported for this run".
  - *Price view:* symbol label = `instrument.markets[0]` (e.g. `NIFTY`), timeframe `Seg` [15m 1H 1D] (fetch with `getCandles`), `Indicators` menu (EMA20/50/200, SMA20/50, Bollinger, RSI; volume-based items are hidden when all volumes are 0), OHLC readout of the hovered bar (default: last bar, close coloured by direction), full-screen icon (→ `/runs/:id/chart`).
    `CandleChart` height 262 px, up `--pos`, down `--neg`, grid `--line-faint`, price scale on the right, last-price dashed line + label.
    **Trade markers:** one circle per trade on its `session_date` bar, placed 12 px below the low. Fill pos/neg by `net_pnl`. The selected trade gets a 2 px `--accent` ring. Click a marker → select that trade in the inspector.
    Below it: a legend line (mono 11 px) and **PnlStepChart**: height 54 px, a step line of cumulative net P&L of the trades inside the visible range, and the end label `inr(sum, signed)`. It syncs to the visible time range of the candle chart (`timeScale().subscribeVisibleTimeRangeChange`).
  - *Equity view:* `EquityChart` (daily `equity − capital`, area fill 8%, zero dashed line, rings on the 5 highest-P&L trades), then the caption `DRAWDOWN · max {pct} · {duration} sessions · {peak note}` and `DrawdownChart` (64 px, red area, 28%). Range `Seg` [1Y ALL].
    `peak note` = `{Mon-YYYY of peak} peak not yet reclaimed` if the final drawdown < 0, else `recovered in {n} sessions`.
- **EdgeIntegrity** panel (330 px): eyebrow + `Bootstrap of trade P&L · {resamples} resamples · seed {seed}` · `P(net P&L > 0)` + Meter · `Profit factor, 90% band` + RangeBand (domain 0–3, break-even line at 1.0 red, point = profit_factor) + caption · KV rows: Without best 5 trades, Without best 10 trades, Longest losing streak, Fees ÷ gross profit (amber if > 0.4), Worst day · auto-insight callout (§7.4) pinned to the bottom.

Row 3: grid `300px minmax(0,1fr) 560px`.
- **Histogram**: trade net P&L, bins of ₹1,000 from floor(min/1000)·1000 to ceil(max/1000)·1000. Bars red for bins < 0, green otherwise. Axis labels at the min, 0, the mid-positive value and the max. Seg [₹ | R]: R mode uses `r_multiple` bins of 0.5 and is **disabled** when every R is null. Footer: `Median trade … · mean …`.
- **MonthlyHeatmap**: rows = years, cols = J…D. Cell colour = pos/neg with alpha `min(1, 0.15 + |pnl|/8000)`. Empty months use `--bg-raised`. Tooltip `YYYY-MM: ₹`. Header right: `{green} of {months} months green`. Footer legend.
- **TradeInspector**: title `TRADE INSPECTOR · #{id} · 15m`, link `Open in Trades →` (→ `/runs/:id/trades?trade={id}`). 6 buttons for the last 6 trades (date + net, selected = active style). `SessionChart` (`getTrade`) with 15m candles, a shaded holding window, SELL/BUY vertical lines labelled with times, and the short CE/PE strike lines (CE `--neg-text`, PE `--info`) labelled on the right. Footer 4 columns: SHORT CE (strike · entry→exit premium), SHORT PE, FEES · SLIPPAGE, NET (₹ + R).
  If `legs` is empty, show only the strike-less chart and replace the leg columns with `Legs not recorded for this run`. If `bars` is empty, show EmptyState `No intraday bars for this session`.
  Keyboard: `[` / `]` move to the previous/next trade (any trade, not only the last 6).

### 8.4 Trades tab (`04-run-trades.png`)

**Data:** `getTrades(id)`. Filters live in the URL: `?result=all|win|loss&reason=…&flag=…&from=…&to=…&trade=ID&page=1`.
Filter bar: Seg [All N | Winners W | Losers L] · Select `Exit reason: any` (values from the data) · Select `Data flag: any` (values from the data + `none`) · date range (two `input type="date"`, IST sessions) · the text `Times in IST · amounts in ₹ · premium per unit` · `CSV (v2 columns)` button (exports the **filtered** rows).

Table columns (DataTable, 36 px rows, sticky header):
`▸` expander · `#` · **Session** (`YYYY-MM-DD` + sub `HH:MM → HH:MM IST`) · **Structure · legs** (Chip with the structure label + sub `legs_label`) ·
**Underlying** (`underlying_entry` + sub `→ underlying_exit`, `—` if null) · **Premium** (`premium_entry` + sub `→ premium_exit`) ·
**Qty** (`qty` + sub `{lots} lot(s)` if lots) · **Gross** · **Fees** (muted) · **Slippage** (`—` if null) · **Net** (coloured) · **R** (`—` if null) ·
**Exit** (badge--muted with `exit_reason`. Use badge--warn for `DATA_EXIT`) · **Flag** (badge--warn with `data_flag` if not empty).
Default sort: session desc. Page size 50.

**Expanded row** (`TradeRowDetail`, lazy `getTrade`): grid `420px minmax(0,1fr)`. Left: a Legs table (Type, Strike, Action, Entry ₹, Exit ₹, Leg P&L = `(entry−exit)·qty` for SELL, `(exit−entry)·qty` for BUY, `—` if a premium is missing) and an **auto note** (§8.4.1). Right: `SessionChart` 760×200 with strikes.
Only one row is expanded at a time. `?trade=ID` expands and scrolls to that row on load.

**Footer row** (tfoot, mono): `{n} trades · {W} W / {L} L · filtered: {desc}` | Σgross | Σfees | Σslippage | Σnet | mean R | reconciliation text:
`Gross − fees − slippage = net ✓` if `|Σgross − Σfees − Σslip − Σnet| ≤ 0.05·n`, otherwise `⚠ does not reconcile by ₹X` in amber.

#### 8.4.1 Auto note for an expanded trade (first rule that applies)
- The losing leg is a SELL whose `exit_premium ≥ 1.5 × entry_premium` → `Spot moved toward the {strike} {CE|PE}: it went from {entry} to {exit}. The other short leg did not offset it.`
- Both SELL legs decayed and net > 0 → `Both short legs decayed. Kept {pct of credit}% of the credit.`
- Otherwise no note.

### 8.5 Diagnostics tab (`05-run-diagnostics.png`)

**Data:** `getRun` (diagnostics), `getTrades` (for the net per exit reason).
Grid `repeat(3, minmax(0,1fr))`, two rows, then a full-width panel:
1. **DataCoverage**: amber `Banner` if `trades_with_missing_data > 0`: `**{x} of {n} trades ({p}%)** exited because market data went missing. Their P&L is known but was forced.` + ` Status: DATA ISSUES.` when status is data_issues.
   KV rows: Eligible sessions (`—` if null), Traded, Skipped, Unresolved P&L (green if 0, red otherwise), one row per `missing_reasons` key (`Forced exit · {KEY}`, amber).
2. **ExitReasons**: HBar per reason (label col 96 px, track, `count · pct`). DATA_* bars are amber, others `--text-3`. Then a dense table: Reason · Trades · Net · Per trade.
3. **CostBreakdown** (`Waterfall`): 4 rows: Gross (green, full width), Fees (red, positioned from gross−fees to gross), Slippage (amber, from net to net+slippage), Net (white, 0→net). Footer: `Costs take {pct} of gross. Slippage alone is {inr} (₹{per trade} per trade).` + the stop/target sentence when both exist and `|avg STOP| > avg TARGET`.
   If slippage is null, draw 3 rows and write `Slippage not recorded`.
4. **Stability**: two boxes (early/recent: trades, net coloured, hit, date range) + a callout:
   both halves > 0 → `Both halves are profitable…`; exactly one > 0 → `Only the {early|recent} half is profitable. The edge may be period-specific.`; neither → `Neither half is profitable.`
5. **Extremes**: Best trade/expiry, Worst, Worst intraday MTM, Max stop overshoot, ES 95%, Intraday max drawdown. Hide rows whose value is null.
6. **MonthlyConsistency**: Profitable months `a / b`, Mean month, Median month. Then **SignalFunnel**: if `decision_counts` exists, render HBars sorted desc (label = key with `_` → space). Otherwise show the muted sentence from the mockup.
7. Full width **ValidationConfig**: left = KV (Execution model, Window, Metric basis badge, Orders if present, Validation status if present) + a list of `limitations` (a `<details>` "Model limitations (n)") + a caveat callout for each `caveats` item. Right = `.code` block with the `instrument`, `group`, `capital`, `window`, `cost_model`, `data_source`, `code_version` lines. Show `null ← not recorded by generator` for nulls. Header button `Copy manifest JSON` (copies `JSON.stringify(runDetail, null, 2)`).

### 8.6 Full-screen chart `/runs/:runId/chart` (`06`)
No rail. Top bar: `← Back to run` · `{market} · {id}` · TF Seg · Indicators · Go to date (dialog, reuse `GoToDateModal` logic) · range Seg [1M 3M 1Y ALL].
Body grid `minmax(0,1fr) 320px`: CandleChart filling the height with trade markers. Right: a list of trades in the visible range (session, net, R). Click → select + centre the chart on it. The selected row gets the amber inset. Esc → back to run.

### 8.7 Compare `/compare?ids=a,b,c,d` (`07`)
**Data:** `getRun` + `getDaily` for each id (parallel).
- Header: eyebrow, H1 `{n} runs, one calendar`, `Copy link` button.
- Chips row: one chip per run with the slot colour square, name, and × (removes the id from the URL). `+ Add run` opens the CommandPalette in "pick run" mode. The right text is `Max 4 · colours are fixed by slot`.
- Amber Banner for **each** run that is not `isComparable`: `**{name}** covers {sessions} sessions ({start month}–{end month}) and {n} trades. Its CAGR and Sharpe are annualised from a short window and are not comparable to the 3-year runs.` (Use the fitting half of the sentence.)
- Panel: `CompareChart` with lightweight-charts line series per run. The value is `% return on capital = (equity/capital − 1)` on session dates (series may start at different dates). Seg [% return | ₹ P&L]. Below it a drawdown overlay (90 px, same colours, 1.2 px lines).
- Table: rows = Status, Trades, Sessions in window, Net P&L, Total return, CAGR, Sharpe, Sortino, Max drawdown, Profit factor, Hit rate, P(net > 0), Net without best 5. Columns = runs, with a colour square in the header.
  **Best-value highlight** (bold + `rgba(245,165,36,.07)` background) = the max of the row's values **among comparable runs only**. Non-comparable runs never get highlighted, and their Trades/CAGR cells get ⚠.
- Footnote sentence from the mockup. With fewer than 2 ids: EmptyState `Pick at least two runs` + a button to the Library.

### 8.8 Groups `/groups` and `/groups/:groupId` (`08`)
- `/groups`: a simple list (DataTable) of `listGroups()` rows: label, runs, axes (chips). Row → group page. Legacy `kind:"sweep"` items (if any) appear in a second table titled `Parameter sweeps (results.parquet)` with the old columns rendered generically.
- `/groups/:groupId`: header (eyebrow `GROUP`, H1 label, sub `{runs} runs · {window} · axes: …`, `Compare top 4` → the 4 best comparable runs by the current cell metric).
  Controls: Rows select (any axis, default `family`), Columns select (default `market × dte`; options: any axis or the pair `market × dte`), Cell Seg [Mean return | Mean Sharpe | Max DD (worst) | % positive].
  **HeatGrid**: cell = aggregate over the runs in that cell. Label `{value} ·{count}`. Colour diverging **blue (≥0) / orange (<0)**, alpha `min(.95, .12 + |v|/18)` for returns in %. Scale the Sharpe option by |v|/1. Text is dark when alpha > .6. Empty cells show `—`. Click → select (amber outline) and fill the table below.
  **Knob effects** panel: generate these rows from the data, in this order:
  1. For each column value: `{col} · variants positive  {pos} / {n}` (amber when 0 < ratio < 1, red when 0, green when 1).
  2. For each axis with exactly 2 values present inside the best column (the highest mean): `{best col} {rows-filter?} · {axis}={v} positive {a}/{b}`.
  3. For each other 2-valued axis over the whole group: `{axis} {v1} vs {axis} {v2} · mean return  x% vs y%`.
  Then the callout: `The market/DTE regime matters more than any knob…`. Show it only when the spread between column means is larger than the spread between row means; otherwise use `Knob choice matters more than market/DTE regime here.`
  **Selected cell table**: Variant (id with the group prefix removed), then one column per axis not used as a row/column, Return, Sharpe, Max DD, PF, `Open →`.

### 8.9 New run `/new` (`09`)
A pure client-side form. Fields and validation:
| Field | Input | Rule |
|---|---|---|
| Strategy file (.py) | text, mono | required, ends with `.py` |
| Strategy class | text | required, `^[A-Za-z_][A-Za-z0-9_]*$` |
| Data CSV (OHLCV) | text | required, ends with `.csv` or `.parquet` |
| Run id | text | required, `^[a-z0-9][a-z0-9-]{2,80}$`. Warn if it already exists in `listRuns()` |
| Starting cash (₹) | number | > 0 |
| Commission (fraction per fill) | number | 0 ≤ x < 0.05. Help text as in the mockup |
Command preview (`.code`), updated live and exactly this format:
```
stolgo {file} \
  --class {cls} \
  --data {data} \
  --cash {cash} \
  --commission {commission} \
  --output runs/{runId}
```
Buttons: `Copy command` (primary, CopyButton → toast "Copied"), `Reset`. Right column: the two panels with the copy from the mockup, verbatim.

### 8.10 NotFound
EmptyState `Page not found` + `Go to Library`. For an unknown run id (404 from `getRun`): `Run "{id}" not found` + Library link.

---

## 9. Global interactions

- **Command palette** (`⌘K` / `Ctrl+K`, or click the top-bar field): a modal with a search input and a result list (max 8). Sources: runs (name, id, group label). Actions: `Go to Library`, `Open Compare`, `Open Groups`, `New run`. On a run page it also offers trade numbers (`#157` → open the Trades tab with `?trade=157`).
  Arrow keys move, Enter opens, Esc closes. Fuzzy match = case-insensitive substring over `name + id`, ranked by position.
- **Tooltips**: `Tooltip` component with a 120 ms delay, positioned above the target and flipped if clipped. Every KPI label and table header with a metric key shows `metric_defs[key].help` on hover.
- **Toasts**: bottom-right, 2.5 s, one at a time.
- **Focus**: every interactive element is a real `<button>`/`<a>`/`<input>`. Visible focus ring = `outline: 2px solid var(--accent)`.
- **Min width**: below 1024 px, show `MinWidthNotice` instead of the app.

---

## 10. Tests (vitest)

| File | Must cover |
|---|---|
| `__tests__/format.test.js` | every example in §5 |
| `__tests__/verdict.test.js` | each row of §7.2 with a minimal run object. `isComparable` edges (99/100 trades, 251/252 sessions) |
| `__tests__/insight.test.js` | the 3 rules of §7.4 + the no-callout case |
| `__tests__/histogram.test.js` | the bin edges for `[-4282.4, 10570.6]` are −5000…11000 |
| `__tests__/RunsTable.test.jsx` | the default sort is Sharpe desc. Clicking the Trades header sorts asc then desc. The 5th selection is refused |
| `__tests__/TradesFooter.test.jsx` | the reconciliation ✓ vs ⚠ |
| `__tests__/compareHighlight.test.js` | a non-comparable run is never highlighted even when its value is the maximum |

Run with `npm test --prefix frontend`. All must pass before U14.

---

## 11. Implementation steps (do them in order. Each ends with `npm run build --prefix frontend` green and a commit `ui: Uxx …`)

| Step | Work | Done when |
|---|---|---|
| U0 | Create the branch. Install deps (§2). Add the `vitest` config (`environment: "jsdom"`) | `npm test` runs (0 tests OK) |
| U1 | Copy `tokens.css`, `components.css`. Create `pages.css`. `main.jsx` imports the fonts + CSS and renders the router with placeholder pages | The app shows the rail + top bar styled like `10-components-states.png` (header area) |
| U2 | Router (§6), AppShell, Rail, TopBar, MinWidthNotice. Add the SPA fallback in `server.py`: `@app.get("/{full_path:path}")` returning `index.html` for non-`api/` paths when `dist` exists (register it **after** the API routes) | Deep-linking `/runs/x` works under `stolgo serve` |
| U3 | `api/*`, `useApi`, `lib/format.js`, `lib/verdict.js`, `lib/metrics.js`, `lib/colors.js` + tests §10 (format, verdict, insight, compareHighlight) | the tests pass |
| U4 | UI kit components (`components/ui/*`). Create a hidden route `/_kit` that renders `10-components-states` from real components | `/_kit` matches `10-components-states.png` |
| U5 | Library page | Matches `01-library.png` with real data. The acceptance of §8.1 passes |
| U6 | RunLayout + RunHeader + RunTabs | The header matches `02` |
| U7 | Overview: KpiStrip, EdgeIntegrity, Histogram, MonthlyHeatmap | Rows 1–3 match `02`, excluding the charts |
| U8 | CandleChart + PnlStepChart + markers, EquityChart + DrawdownChart, Seg switch | Matches `02` and `03` |
| U9 | TradeInspector + SessionChart + `[`/`]` keys | Matches the `02` bottom-right |
| U10 | Trades tab (table, filters, expanded row, footer, CSV) | Matches `04`. The CSV header equals the v2 columns |
| U11 | Diagnostics tab | Matches `05` for `validated-timing-3y-sensex-0dte-static` |
| U12 | Full-screen chart. Delete the old files listed in §3 | Matches `06`. No imports from the deleted paths remain (`grep -r "components/detail" src` is empty) |
| U13 | Compare page + Groups pages | Match `07` and `08` |
| U14 | New run page, NotFound, CommandPalette, tooltips, toasts. Run a final QA pass (§12) | All §12 items ticked |

---

## 12. QA checklist (paste into the PR and tick every box)

- [ ] At 1440×900, each page is visually side-by-side equal to its PNG (spacing ±4 px, same copy, same colours).
- [ ] `nifty-0dte-strangle-benchmark` Overview shows Net `+₹30,331`, CAGR `+5.4%`, Sharpe `0.73`, Sortino `1.56`, Max DD `−9.5%`, `347 sessions`, PF `1.31`, Hit `35.0%`, verdict `EDGE · FRAGILE`.
- [ ] `top1-sensex-1dte-strangle` shows Sharpe `4.78` (not 12.2), a `Low sample` badge, the CAGR ⚠, and verdict `EDGE · UNPROVEN`.
- [ ] Every trade time on `top1-*` shows 09:21 → 14:30 IST (not 14:51).
- [ ] Nothing renders `NaN`, `undefined`, `Infinity`, or `0.00R` for an unknown R. Unknowns render `—`.
- [ ] No `$`, no currency toggle, no timezone toggle, no light-theme toggle anywhere.
- [ ] The Trades footer reconciles (✓) for the benchmark and for the validated S0-static run (slippage included).
- [ ] The Price segment is disabled with a tooltip on runs without ohlcv (e.g. any `validated-timing-*`), and Overview opens on Equity.
- [ ] Keyboard: ⌘K opens the palette. `[`/`]` step trades. Esc closes dialogs. Tab order is visible everywhere.
- [ ] `npm test` is green. `npm run build` is green. `PYTHONPATH=lib pytest -q` is green.

## 13. Guardrails — do NOT

- Do not compute any metric in the frontend that the API provides. Only presentation maths (bins, cumulative sums for display, W/L counts) is allowed.
- Do not invent numbers or placeholder data. If the API lacks a field, render `—` and add a line to `QUESTIONS.md`.
- Do not add chart or UI libraries beyond §2.
- Do not use colour alone to encode meaning. Badges carry text, and hollow vs filled marks encode sample size.
- Do not hard-code hex colours in JSX or JS, except inside `lib/colors.js`, which reads the CSS variables.
