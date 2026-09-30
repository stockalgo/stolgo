# Plan 03 — Review fixes (review of `feat/ui-cockpit` @ 53c79f0, 2026-09-29)

> Same rules as Plans 01/02. Do the tasks **in order**. Commit after each with `review-fix: Rn — <title>`.
> Run `PYTHONPATH=lib pytest -q` and `npm test --prefix frontend` after each task. Both must stay green.
> After R1–R5, re-run `python scripts/migrate_runs_v2.py --runs-dir runs`. It reads from `runs/_backup_v1`, so it is safe.

Reviewed on `/runs/combined-top3-weekly-calendar`, `/runs/.../trades`, `/runs/.../diagnostics` and `/`.
Metric values, statuses and verdicts are correct. The problems below are the remaining ones.

---

## Must fix

### R1 — Data: P&L does not reconcile in 12 legacy weekly runs → flag them
In `runs/_backup_v1/*/trades.csv`, `gross_pnl − commission − net_pnl` is far from 0 for every G1 run:

| run | Σ(gross − fees − net) |
|---|---|
| NIFTY-iron-condor-0dte | −17,086 |
| NIFTY-iron-condor-1dte | −18,226 |
| NIFTY-strangle-0dte | −9,951 |
| NIFTY-strangle-1dte | −10,410 |
| SENSEX-iron-condor-0dte | −20,069 |
| SENSEX-iron-condor-1dte | −4,207 |
| SENSEX-strangle-0dte | −10,747 |
| SENSEX-strangle-1dte | −4,028 |
| combined-top3-weekly-calendar | −5,674 |
| top1-sensex-1dte-strangle | −935 |
| top2-nifty-pre-expiry-strangle | −2,505 |
| top3-nifty-0dte-strangle | −2,234 |

G2 (3-year benchmark/IC/fly) runs are within ±₹40. **Do not "fix" the numbers.** The source is wrong and must be checked by the generator owner. Instead:
1. `lib/stolgo/report/diagnostics.py`: add `data_quality.pnl_unreconciled_inr = round(Σ(gross − fees − slippage_or_0 − net), 2)` and
   `data_quality.pnl_reconciles = abs(that) <= 0.05 * n_trades`.
2. `lib/stolgo/report/quality.py`: `data_issues` also triggers when `pnl_reconciles` is False. Reason string, exactly:
   `"net P&L differs from gross − fees by ₹{abs:,.0f}"`.
3. UI `DataCoverage.jsx`: when `pnl_reconciles === false`, show a red `banner--bad`:
   **P&L does not reconcile.** Net P&L is ₹X higher than gross − fees − slippage across N trades. Metrics for this run may be overstated.
   Also show it in `CostBreakdown.jsx` instead of the waterfall bars (the waterfall is meaningless here). Keep the footer ⚠ in the Trades tab as is.
4. Append to `docs/plans/QUESTIONS.md`: `- [ ] 2026-09-29 · 03 R1 · G1 generator: net_pnl ≠ gross_pnl − commission. Which one is wrong?`

**Done when:** the 12 runs above have status `data_issues` (status counts become 8 ok / 3 low_sample / 111 data_issues / 2 superseded / 4 empty). The 3 low_sample runs are the S/R `one_lot_diagnostic` runs. Update §8.1 acceptance in Plan 02 accordingly.

### R2 — Migration: keep the real run names
`scripts/migrate_runs_v2.py:429` builds names from the run id (`"Nifty 0Dte Strangle Benchmark"`). Use the v1 name:
```python
name = manifest.get("name") or manifest.get("strategy") or run_id
```
**Done when:** `/api/runs` returns `"NIFTY 0-DTE Strangle Benchmark"`, `"Combined Top 3 Weekly Calendar Portfolio"` and
`"SENSEX 0DTE STATIC — corrected timing / conditional data"` for those ids. `superseded` detection still gives 2.

### R3 — Migration: market per trade for mixed-market runs
`combined-top3-weekly-calendar` trades have `market = "UNKNOWN"`. For runs whose `instrument.markets` has more than one value, set the market per trade by lot size:
`qty % 20 == 0 and qty < 65` → `SENSEX`, `qty % 65 == 0` → `NIFTY`, otherwise `UNKNOWN`. For single-market runs, always write `instrument.markets[0]`. Also set `lots` from the market's lot size (SENSEX 20, NIFTY 65).
Add `tests/test_migrate_market.py` with a qty 20 → SENSEX case and a qty 65 → NIFTY case.
**Done when:** no trade in any run has `market == "UNKNOWN"`.

### R4 — API: never pair a trade with another market's bars
`lib/stolgo/ui/adapters.py::trade_detail`: return `bars: []` when `trade.market` is not the market of the run's `ohlcv.parquet`. That is `instrument.markets[0]` for single-market runs. For mixed runs, record `ohlcv_market` in the manifest's `has` block during migration (the combined run's ohlcv is NIFTY).
`CandleChart.jsx`: draw markers only for trades whose `market` equals the chart's market.
**Done when:** SENSEX trade #53 of the combined run shows the inspector EmptyState `No intraday bars for this session`, and there is no SENSEX marker on the NIFTY chart.

### R5 — Migration: fill `dte` for S/R and premium-spike runs
These runs have an empty `dte` although `trades.parquet` has a `dte` column. Set `instrument.dte = sorted(unique(trades.dte))`.

### R6 — UI: remove invented fallback text
`frontend/src/components/diagnostics/ValidationConfig.jsx`:
- `executionModel`: use `run.config?.execution`. If it is null, render `—` with the muted note `not recorded by generator`. **Delete** the hard-coded "Stolgo options replay / SimBroker…" string.
- `metricBasis`: read `run.metrics?.basis`. If it is null, render `—`. Delete the `"calendar_daily"` default.
- The group line in the code block: when `group.id` is null, print `group:      none` (not "not recorded by generator").
Then grep the whole `frontend/src` for other `|| "<literal sentence>"` fallbacks on data fields and replace each with `—`.
**Done when:** `grep -rn "SimBroker" frontend/src` is empty.

### R7 — UI: the strategy P&L strip must align with the candles by date
`frontend/src/components/chart/PnlStepChart.jsx` spaces trades evenly by index. Replace it with a second lightweight-charts line series in its own pane of the **same** chart as the candles, or with an SVG whose x-coordinates come from
`chart.timeScale().timeToCoordinate(sessionTime)` (and re-render on `subscribeVisibleTimeRangeChange`). The step line is flat until the first trade date. Its values are cumulative `net_pnl` by `session_date`.
**Done when:** on the combined run, the strip is flat from Jan–Jun and starts rising at 11 Jun, directly under the first marker.

---

## Should fix

| # | File | Change |
|---|---|---|
| R8 | `components/ui/RangeBand.jsx`, `overview/EdgeIntegrity.jsx` | Domain = `[0, max(3, pf_p95 * 1.1)]`, ticks at 0, 1, and the max. The point and band must always be inside the track |
| R9 | `overview/EdgeIntegrity.jsx:124` | `pct(feeRatio, { signed: false })` |
| R10 | `lib/format.js` | Add `prob(v)`: `≥ 0.999` → `>99.9%`, `≤ 0.001` → `<0.1%`, else `pct(v,{dec:1,signed:false})`. Use it for P(net > 0) everywhere (EdgeIntegrity, Library P(>0), Compare) + a unit test |
| R11 | `pages/LibraryPage.jsx:374` | `migratedCount` = runs whose metrics were recomputed (v1 basis ≠ calendar_daily). The migration must write `migrated_changed_basis: true/false` into the manifest. The expected text is `23 older runs were recomputed` |
| R12 | `frontend/index.html` | `<title>Stolgo</title>`. Set `document.title` per page: `{run name} · Stolgo`, `Library · Stolgo`, etc. |
| R13 | `trades/TradesTable.jsx` | Omit the sub-line when the value is null (no `→ —`). When `instrument.markets.length > 1`, add a **Market** column after Session |
| R14 | `scripts/migrate_runs_v2.py` | Do not keep the duplicate `tag` column when `source_tag` holds the same value. Delete `runs/index.duckdb` (only `runs/_index.duckdb` is valid) and make sure no code writes `index.duckdb` |
| R15 | all `frontend/src/**/*.jsx` | Replace the 47 hard-coded hex colours with CSS variables (`var(--pos)` …) or `lib/colors.js`. Check with `grep -rnE "#[0-9a-fA-F]{6}" frontend/src --include=*.jsx`: it must be empty |

## Not required now (note in QUESTIONS.md only)
- Equity, drawdown and compare charts are hand-drawn SVG, not lightweight-charts as Plan 02 §2 says. Accept this unless it causes a bug.
- The folder layout differs slightly from Plan 02 §3 (`components/chart`, `components/diagnostics`, …). Accept it.

## Final check
- [ ] `/runs/combined-top3-weekly-calendar`: the real name, the red "P&L does not reconcile" banner on Diagnostics, status `Data issues`, the P&L strip aligned, the PF band inside the track, "Fees ÷ gross profit 29.3%", "P(net P&L > 0) >99.9%".
- [ ] Library: banner says 23 recomputed. Names are human names. Status counts are as in R1.
- [ ] No "SimBroker" text on runs that don't record it. No `UNKNOWN` markets. Tab title is Stolgo.
- [ ] Both test suites are green.
