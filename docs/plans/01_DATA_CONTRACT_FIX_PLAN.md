# Plan 01 — Data contract v2: metric, timestamp and export fixes

> **Audience:** an implementing engineer or a smaller LLM. Follow the tasks **in order**.
> Do not improvise. When this plan says "exactly", match names, types and units
> character for character. If something here conflicts with the code, stop and
> write the conflict into `docs/plans/QUESTIONS.md`. Do not guess.
>
> **Branch:** `fix/data-contract-v2` (create from `codex/backtest-ui-wiring`).
> **Python:** 3.11, run from repo root with `PYTHONPATH=lib`.
> **Pairs with:** `02_UI_REVAMP_PLAN.md`. The UI plan depends on §4 (API contract v2).

---

## 0. Why this plan exists (audit summary, 2026-09-28)

The UI shows numbers that are wrong. Some fields are mislabelled, and useful data
that already sits in `runs/` is dropped. The table below lists each finding with its
evidence and the task that fixes it.

| # | Problem | Evidence | Fixed by |
|---|---------|----------|----------|
| F1 | `compute_metrics` annualises by **number of equity points** (`n_bars / 252`) and `sqrt(252)`. 23 runs store **one equity point per trade**, so CAGR/Sharpe/vol are inflated | `nifty-0dte-strangle-benchmark`: CAGR 29.5 % (real 5.36 %), Sharpe 1.66 (real 0.73). `top1-sensex-1dte-strangle`: Sharpe 12.2 (real 4.78) | D2, D3, D4, D10 |
| F2 | `total_return` uses the **first equity point** (already after trade #1) as the start. Initial capital is ignored | benchmark 0.1750 vs `net / capital` = 0.1685 | D4 |
| F3 | Sortino is mis-scaled: `rets.mean() / (downside.std()*sqrt(252)) * sqrt(252)` | benchmark Sortino 0.29 < Sharpe 1.66 | D2 |
| F4 | 12 runs store **IST wall-clock labelled as UTC** (`09:21+00:00`). The UI shows 14:51 entries | groups G1 (see §5.1); exits at 14:30Z are impossible for NSE/BSE | D5, D10 |
| F5 | `entry_price/exit_price` means **index level** in 8 runs, **net premium** in 12, and is **empty** in 99 | benchmark 20147.95 vs top1 391.29 vs validated NaN | D6 |
| F6 | `side` is inferred from keywords in `tag`. Short strangles show as "Long" | `adapters.trades()` | D6, D11 |
| F7 | `expectancy` (₹ per trade) is rendered with unit "R" | `adapters.metric_cards` fmt `"r"` | D1, D11 |
| F8 | Missing `r_multiple` is rendered as `0.00R`. Missing metrics default to `0.0` | `row.get("r_multiple", 0.0)`, `metrics.get(key, 0.0)` | D1, D11 |
| F9 | Cost breakdown drops `slippage` (validated runs store it separately) | S0-static slippage ₹4,479 | D6, D8 |
| F10 | `profit_factor = 0` when there are no losses (should be undefined / ∞) | `compute_metrics` | D2 |
| F11 | `turnover` multiplies qty by **index level** for options → 2,159× | benchmark manifest | D2 (drop for options) |
| F12 | Rich diagnostics exist in 105 manifests but are never served (eligible/skipped/unresolved, fees vs slippage, worst expiry, stop overshoot, early vs recent, profitable months, caveats, decision funnel, ledger audit) | `validated-timing-*`, `nifty-sr-audited-*` manifests | D8, D11 |
| F13 | Exit reasons (in `tag` for validated runs) and data-quality exits (`MISSING_SPOT`, `MISSING_HELD_QUOTE`) are invisible | S0-static: 24 / 157 trades are data-quality exits | D6, D8 |
| F14 | 99 runs have no `ohlcv.parquet`, so the chart is silently empty | `ls runs/*/parquet/ohlcv.parquet` → 29 | D3 (calendar), D11 (`has.ohlcv`) |
| F15 | `params` duplicates `metrics` and the copies disagree | SENSEX-strangle-1dte Sharpe 1.11 vs 1.13 | D9, D10 (drop duplicates) |
| F16 | Mislabelled markets. The combined portfolio is labelled NIFTY but contains SENSEX; top1/2/3 have no `dte` | manifests | D10 override table |
| F17 | No reproducibility info (lot size, rules, cost model, data source, git SHA) | all manifests | D9 |
| F18 | 3 runs are named "INVALID / SUPERSEDED" and 4 runs have 0 trades, but they still rank in the library | manifests | D9 `status` |
| F19 | **All 99 validated-timing runs** have 11–35 of 157 trades (7–22%) that exited on `MISSING_SPOT`/`MISSING_HELD_QUOTE`. This is not surfaced anywhere | `trades.parquet` `tag` column | D6, D8 (`status = data_issues`) |

**Non-goals:** changing strategy logic, adding new strategies, live trading, or
rewriting the engine. The external generators in
`~/Developer/AlgoTrader/research/...` are **out of scope**. They must adopt
`export_all` v2 later (see §7).

---

## 1. Glossary (use these words exactly)

| Term | Meaning |
|------|---------|
| **session** | One exchange trading day (NSE for NIFTY, BSE for SENSEX), keyed by IST date `YYYY-MM-DD`. |
| **daily P&L** | Sum of `net_pnl` of trades whose `exit_ts` (converted to IST) falls on that session. Sessions without exits = `0.0`. Unknown = `NaN`. |
| **metric basis** | `"calendar_daily"`: metrics computed from daily P&L over every session in the window. This is the **only** valid basis after this plan. `"legacy_per_point"`: old, only allowed inside backups. |
| **window** | `[first entry session, last exit session]` inclusive, IST dates. |
| **capital** | `params.capital` (₹). Returns are always `pnl / capital`-based. |
| **premium** | Net option premium per unit (₹ per share/unit, not per lot). |
| **underlying** | Index level (NIFTY / SENSEX spot). |
| **low sample** | `num_trades < 100` (constant `MIN_TRADES_OK = 100` in `stolgo/report/quality.py`). |
| **short window** | `sessions < 252`. Annualised metrics are still computed but flagged `annualised_from_short_window = true`. |

---

## 2. Target run directory layout (v2)

```
runs/<run_id>/
  manifest.json            # schema_version = 2  (§3.1)
  trades.csv               # same columns as parquet/trades.parquet (v2)
  summary.json             # unchanged format (RunResult.to_json) — keep for back-compat
  tearsheet.html           # unchanged
  audit.html               # optional, unchanged
  parquet/
    trades.parquet         # v2 schema (§3.2)                 REQUIRED
    daily.parquet          # v2 (§3.4)                         REQUIRED
    legs.parquet           # v2 (§3.3)                         OPTIONAL
    equity.parquet         # intraday/mark-to-market path, column "equity", UTC index   OPTIONAL
    drawdown.parquet       # DEPRECATED → delete on migration (daily.parquet has drawdown)
    ohlcv.parquet          # underlying bars, UTC index          OPTIONAL
    positions.parquet      # unchanged, optional
runs/_calendars/
  NSE.parquet              # column "session" (datetime64[ns], date only), one row per NSE session
  BSE.parquet              # same for BSE
runs/_backup_v1/<run_id>/  # untouched copy of every run before migration (D10)
runs/_index.duckdb         # schema_version 2 (D11)
```

---

## 3. Schemas

### 3.1 `manifest.json` v2 — exact shape

```json
{
  "schema_version": 2,
  "run_id": "nifty-0dte-strangle-benchmark",
  "kind": "run",
  "name": "NIFTY 0-DTE Strangle Benchmark",
  "status": "ok",
  "status_reasons": [],
  "created_at": "2026-09-26T12:31:32.576192+00:00",
  "migrated_at": "2026-09-29T10:00:00+00:00",
  "path": "/abs/path/runs/nifty-0dte-strangle-benchmark",

  "instrument": {
    "asset_class": "index_options",
    "markets": ["NIFTY"],
    "exchange": "NSE",
    "structure": "short_strangle",
    "dte": [0],
    "lot_size": 65,
    "currency": "INR",
    "timezone": "Asia/Kolkata"
  },

  "group": {
    "id": null,
    "label": null,
    "axes": {}
  },

  "config": {
    "capital": 180000.0,
    "window": {"start": "2023-09-14", "end": "2026-09-08", "sessions": 740},
    "entry_rule": "STRANGLE_OTM2_LEGDOUBLE_BENCHMARK",
    "exit_rule": null,
    "execution": null,
    "cost_model": null,
    "data_source": null,
    "code_version": null,
    "raw_params": { "...": "original params minus keys duplicated in metrics" }
  },

  "metrics": {
    "basis": "calendar_daily",
    "net_pnl": 30330.69,
    "gross_pnl": 53787.0,
    "fees": 23456.3,
    "slippage": null,
    "total_return": 0.168504,
    "cagr": 0.053554,
    "sharpe": 0.733541,
    "sortino": 1.558107,
    "calmar": 0.562589,
    "max_drawdown": -0.095192,
    "max_drawdown_duration": 347,
    "intraday_max_drawdown": null,
    "volatility": 0.076199,
    "ulcer_index": 0.0,
    "worst_day": -4282.4,
    "expected_shortfall_95": -2000.0,
    "num_trades": 157,
    "hit_rate": 0.350318,
    "profit_factor": 1.312331,
    "payoff": 2.433778,
    "avg_win": 2317.11,
    "avg_loss": -952.07,
    "expectancy": 193.19,
    "avg_r": null,
    "final_equity": 210330.69,
    "annualised_from_short_window": false
  },

  "robustness": {
    "method": "bootstrap_trade_pnl",
    "seed": 7,
    "resamples": 4000,
    "p_net_positive": 0.88075,
    "pf_p05": 0.900395, "pf_p95": 1.862512,
    "net_p05": -10851.85, "net_p95": 74258.23,
    "net_without_top5": -6013.77,
    "net_without_top10": -25634.98,
    "longest_losing_streak": 13
  },

  "diagnostics": {
    "exit_reasons": {"TIME_EXIT": 157},
    "data_quality": {
      "trades_total": 157,
      "trades_with_missing_data": 0,
      "missing_reasons": {},
      "unresolved_sessions": 0,
      "skipped_sessions": 0,
      "eligible_sessions": null
    },
    "stability": {
      "split": "half_by_trade_count",
      "early": {"trades": 79, "net_pnl": 0.0, "hit_rate": 0.0, "start": "2023-09-14", "end": "2025-03-13"},
      "recent": {"trades": 78, "net_pnl": 0.0, "hit_rate": 0.0, "start": "2025-03-20", "end": "2026-09-08"}
    },
    "monthly": {"months": 37, "profitable_months": 20, "mean_monthly_pct": 0.0, "median_monthly_pct": 0.0},
    "extremes": {"best_trade": 10570.6, "worst_trade": -4282.4, "worst_mtm": null, "max_stop_overshoot": null},
    "decision_counts": null,
    "validation": {"status": null, "summary": null, "limitations": [], "caveats": [], "ledger_audit": null, "report_available": true}
  },

  "has": {"ohlcv": true, "legs": true, "intraday_equity": false, "audit": true}
}
```

Rules:

- Every numeric metric is a JSON number **or `null`**. Never write `NaN`/`Infinity`; convert them to `null`.
- `status` ∈ `"ok" | "low_sample" | "short_window" | "data_issues" | "superseded" | "empty"`.
  Compute it with `stolgo.report.quality.run_status()` (D8). Precedence, first match wins:
  `empty` (0 trades) > `superseded` (name starts with `"INVALID"` or `raw_params.superseded == true`)
  > `data_issues` (`trades_with_missing_data / trades_total > 0.05` or `unresolved_sessions > 0`)
  > `low_sample` (< 100 trades) > `short_window` (< 252 sessions) > `ok`.
  `status_reasons` holds one short human string for **every** condition that matched, not only the first.
- The values above for `nifty-0dte-strangle-benchmark` are the real expected values
  (see `fixtures/expected_after_migration.json`). The `0.0` placeholders in `stability` and
  `monthly` are computed by D8.

### 3.2 `parquet/trades.parquet` v2 — exact columns

One row = one **position lifecycle** (for options: all legs of one structure on one session).

| column | dtype | unit | required | notes |
|--------|-------|------|----------|-------|
| `trade_id` | int64 | – | yes | 1..N in entry order |
| `session_date` | string `YYYY-MM-DD` | IST date | yes | from `entry_ts` in IST |
| `entry_ts` | datetime64[ns, UTC] | – | yes | **must be UTC**, validated by D5 |
| `exit_ts` | datetime64[ns, UTC] | – | yes | |
| `side` | string | – | yes | `"SHORT"` or `"LONG"` (net position: credit structures are SHORT) |
| `structure` | string | – | yes | `short_strangle`, `iron_condor`, `iron_fly`, `bear_call_spread`, `bull_put_spread`, `long`, `short`, `unknown` |
| `market` | string | – | yes | `NIFTY` / `SENSEX` / symbol |
| `dte` | Int64 | days | no | |
| `expiry` | string `YYYY-MM-DD` | – | no | |
| `qty` | float64 | units | yes | units, not lots |
| `lots` | Int64 | lots | no | `qty / lot_size` when that is an exact integer |
| `underlying_entry` | float64 | index pts | no | spot at entry |
| `underlying_exit` | float64 | index pts | no | |
| `premium_entry` | float64 | ₹/unit | no | net credit (SHORT) or debit (LONG) per unit |
| `premium_exit` | float64 | ₹/unit | no | |
| `gross_pnl` | float64 | ₹ | yes | |
| `fees` | float64 | ₹ | yes | statutory + brokerage (old `commission`) |
| `slippage` | float64 | ₹ | yes | `0.0` if the source has none **and** the source's `gross − fees == net` within ₹0.05, otherwise `NaN` |
| `net_pnl` | float64 | ₹ | yes | `gross_pnl − fees − slippage` (validated within ₹0.05) |
| `r_multiple` | float64 | R | no | **NaN when unknown** (never 0) |
| `risk_inr` | float64 | ₹ | no | denominator of R if known |
| `exit_reason` | string | – | yes | UPPER_SNAKE vocabulary (§3.5). `"UNKNOWN"` if not derivable |
| `data_flag` | string | – | yes | `""` or one of `MISSING_SPOT`, `MISSING_HELD_QUOTE`, `MISSING_DATA` |
| `legs_label` | string | – | no | human label, e.g. `"-C24150 -P23950"` |
| `source_tag` | string | – | no | original `tag`, unchanged |

Extra source columns (e.g. `level`, `stop_overshoot`, `signal_ts`) are **kept** with their
original names after the required columns. Never drop data.

### 3.3 `parquet/legs.parquet` v2 (optional)

| column | dtype | notes |
|--------|-------|-------|
| `trade_id` | int64 | FK to trades |
| `leg_id` | int64 | 1..k within trade |
| `option_type` | string | `CE` or `PE` |
| `strike` | int64 | |
| `action` | string | `SELL` or `BUY` (at entry) |
| `qty` | float64 | units |
| `entry_premium` | float64 | ₹/unit, NaN if unknown (wing legs in legacy tags) |
| `exit_premium` | float64 | ₹/unit, NaN if unknown |
| `entry_ts` / `exit_ts` | datetime64[ns, UTC] | NaT if unknown (use the trade's) |

### 3.4 `parquet/daily.parquet` v2 (required)

Index: none (plain columns).

| column | dtype | notes |
|--------|-------|-------|
| `session` | string `YYYY-MM-DD` | every exchange session in the window |
| `pnl` | float64 | daily P&L (§1). NaN = unknown |
| `equity` | float64 | `capital + cumsum(pnl)` |
| `drawdown` | float64 | **fraction**, `equity / cummax(equity) − 1`, where cummax includes the initial `capital` |
| `trades_closed` | int64 | trades with exit on that session |

### 3.5 Exit-reason vocabulary

Map source values into this set. **Keep the original string in `source_tag`.**

| source value (case-insensitive) | `exit_reason` | `data_flag` |
|---|---|---|
| `PORTFOLIO_TARGET`, `target*` | `TARGET` | |
| `DAILY_STOP`, `hard_loss*`, `stop*` | `STOP` | |
| `TIME_EXIT`, `max_hold*`, `eod*` | `TIME_EXIT` | |
| `EXIT_TOUCH`, `touch*` | `TOUCH_EXIT` | |
| `CONVERSION`, `adjust*` | `ADJUSTMENT` | |
| `MISSING_SPOT` | `DATA_EXIT` | `MISSING_SPOT` |
| `MISSING_HELD_QUOTE` | `DATA_EXIT` | `MISSING_HELD_QUOTE` |
| legacy tags that are a run/strategy name (`top1-…`, `strangle_1dte`, `iron_condor_0dte`) or leg strings (`-C…`) | `TIME_EXIT` **only if** every exit is at the same clock time ±1 min; otherwise `UNKNOWN` | |

`S/R audited` runs already have an `exit_reason` column. Map its values with the same table
and fall back to the uppercase of the value.

---

## 4. API contract v2 (served by `lib/stolgo/ui/server.py`)

All responses are JSON. Numbers may be `null`. Timestamps are **epoch seconds (UTC)**, and
session dates are `YYYY-MM-DD` strings. The UI formats everything in IST.

### 4.1 `GET /api/runs` → `{ "items": RunSummary[], "warnings": int }`

```json
{
  "id": "nifty-0dte-strangle-benchmark",
  "name": "NIFTY 0-DTE Strangle Benchmark",
  "status": "ok",
  "status_reasons": [],
  "markets": ["NIFTY"],
  "structure": "short_strangle",
  "dte": [0],
  "group": {"id": null, "label": null, "axes": {}},
  "window": {"start": "2023-09-14", "end": "2026-09-08", "sessions": 740},
  "capital": 180000.0,
  "metrics": {
    "net_pnl": 30330.69, "total_return": 0.168504, "cagr": 0.053554, "sharpe": 0.733541,
    "max_drawdown": -0.095192, "profit_factor": 1.312331, "hit_rate": 0.350318,
    "num_trades": 157, "expectancy": 193.19, "annualised_from_short_window": false
  },
  "robustness": {"p_net_positive": 0.88075, "net_without_top5": -6013.77},
  "data_quality": {"trades_with_missing_data": 0, "trades_total": 157},
  "has": {"ohlcv": true, "legs": true, "intraday_equity": false, "audit": true},
  "created_at": "2026-09-26T12:31:32.576192+00:00"
}
```

### 4.2 `GET /api/runs/{id}` → `RunDetail`

`RunSummary` fields **plus** `instrument`, `config`, the full `metrics`, the full `robustness`,
`diagnostics` (exactly as in the manifest), and `metric_defs` (below).

`metric_defs` is the registry from D1, serialised as a list:
`[{"key":"sharpe","label":"Sharpe","unit":"ratio","decimals":2,"better":"higher","help":"Annualised mean/stdev of daily returns over every session (√252)."}, …]`

### 4.3 `GET /api/runs/{id}/daily` → `{ "rows": [{"session":"2023-09-14","pnl":-991.9,"equity":179008.1,"drawdown":-0.0055,"trades_closed":1}, …] }`

### 4.4 `GET /api/runs/{id}/monthly` → `{ "rows": [{"month":"2023-09","pnl":-2530.0,"return_pct":-0.01406,"trades":3}, …] }`
Computed from `daily.parquet`. `return_pct = pnl / capital`.

### 4.5 `GET /api/runs/{id}/trades` → `{ "rows": TradeV2[], "columns": ["trade_id", …] }`
`TradeV2` = the trades.parquet row with timestamps as epoch seconds and NaN → `null`.

### 4.6 `GET /api/runs/{id}/trades/{trade_id}` → `{ "trade": TradeV2, "legs": Leg[], "bars": Candle[] }`
`bars` = the `ohlcv.parquet` rows from 09:15 to 15:30 IST of `session_date` (empty list if there is no ohlcv).
`Candle = {"time": epoch_s, "open":…, "high":…, "low":…, "close":…}`.

### 4.7 `GET /api/runs/{id}/candles?tf=1D|1H|15m&from=YYYY-MM-DD&to=YYYY-MM-DD` → `{ "rows": Candle[], "tf": "1D" }`
Resample `ohlcv.parquet` in IST (`1D` = session OHLC, `1H` anchored at 09:15, `15m` = raw if
the source is 15m). **Default when `from`/`to` are omitted:** last 180 sessions for `1D`,
last 20 sessions for `1H`, last 5 sessions for `15m`. Return `409 {"detail":"no_ohlcv"}` if the file is missing.

### 4.8 `GET /api/runs/{id}/equity` → `{ "rows": [{"time":…, "equity":…}] }`
From `equity.parquet` only if `has.intraday_equity`, else `404`.

### 4.9 `GET /api/groups` and `GET /api/groups/{group_id}`
Groups replace the empty "sweeps" concept for runs saved individually.

```json
{"items":[{"id":"validated-timing-3y","label":"3-year timing sweep","runs":99,
  "axes":{"market":["NIFTY","SENSEX"],"dte":[0,1],"family":["A","B","C","D","CUT","EXIT_TOUCH","ONE_CONV","STATIC","LEG100"]}}]}
```

`/api/groups/{id}` → `{"id":…, "label":…, "axes":{…}, "runs": RunSummary[]}` (every run with `group.id == id`).

Legacy `kind:"sweep"` manifests (none exist in `runs/` today) keep `/api/sweeps` unchanged.

### 4.10 `GET /api/migration-report` → `text/markdown`
Serves `runs/_migration_report.md`. Returns `404` if it is missing.

### 4.11 Unchanged: `GET /api/runs/{id}/audit`

### 4.12 Removed
`/api/runs/{id}/series` is removed after the UI migrates (UI plan step U12). Keep it until then,
unchanged.

---

## 5. Tasks

Every task lists **files**, **exact changes**, **tests**, and **done when**. Run
`PYTHONPATH=lib python -m pytest -q` after every task. It must stay green.

> **Prerequisite (P0):** fix the local venv. It points to a missing uv Python.
> `uv venv --python 3.11 .venv && uv pip install -e ".[ui,dev]"`. Then confirm the baseline
> `PYTHONPATH=lib .venv/bin/python -m pytest -q` passes **before** any change. Record the pass count in
> the PR description.

### D1 — Metric registry `lib/stolgo/report/metric_registry.py` (new)

```python
from dataclasses import dataclass, asdict
from typing import Literal

Unit = Literal["inr", "fraction", "ratio", "count", "sessions", "r"]

@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    unit: Unit
    decimals: int
    better: Literal["higher", "lower", "none"]
    help: str

METRICS: tuple[MetricDef, ...] = (
    MetricDef("net_pnl", "Net P&L", "inr", 0, "higher", "Sum of net trade P&L after fees and slippage."),
    MetricDef("gross_pnl", "Gross P&L", "inr", 0, "higher", "Sum of trade P&L before fees and slippage."),
    MetricDef("fees", "Fees", "inr", 0, "lower", "Brokerage + statutory charges."),
    MetricDef("slippage", "Slippage", "inr", 0, "lower", "Modelled execution slippage."),
    MetricDef("total_return", "Total return", "fraction", 1, "higher", "Net P&L ÷ capital."),
    MetricDef("cagr", "CAGR", "fraction", 1, "higher", "Annualised over elapsed calendar time of the window."),
    MetricDef("sharpe", "Sharpe", "ratio", 2, "higher", "Mean/stdev of daily returns over every session × √252. Risk-free = 0."),
    MetricDef("sortino", "Sortino", "ratio", 2, "higher", "Mean daily return ÷ downside RMS × √252."),
    MetricDef("calmar", "Calmar", "ratio", 2, "higher", "CAGR ÷ |max drawdown|."),
    MetricDef("max_drawdown", "Max drawdown", "fraction", 1, "higher", "Worst peak-to-trough of daily equity incl. initial capital."),
    MetricDef("max_drawdown_duration", "Longest drawdown", "sessions", 0, "lower", "Sessions spent below a prior peak."),
    MetricDef("intraday_max_drawdown", "Intraday max DD", "fraction", 1, "higher", "From mark-to-market path, when available."),
    MetricDef("volatility", "Volatility", "fraction", 1, "lower", "Annualised stdev of daily returns."),
    MetricDef("worst_day", "Worst day", "inr", 0, "higher", "Lowest daily P&L."),
    MetricDef("expected_shortfall_95", "ES 95%", "inr", 0, "higher", "Mean of the worst 5% daily P&L."),
    MetricDef("num_trades", "Trades", "count", 0, "none", "Closed position lifecycles."),
    MetricDef("hit_rate", "Hit rate", "fraction", 1, "higher", "Share of trades with net P&L > 0."),
    MetricDef("profit_factor", "Profit factor", "ratio", 2, "higher", "Gross wins ÷ gross losses. Null when no losses."),
    MetricDef("payoff", "Payoff", "ratio", 2, "higher", "Average win ÷ |average loss|."),
    MetricDef("avg_win", "Avg win", "inr", 0, "higher", ""),
    MetricDef("avg_loss", "Avg loss", "inr", 0, "higher", ""),
    MetricDef("expectancy", "Expectancy", "inr", 0, "higher", "Mean net P&L per trade (₹, not R)."),
    MetricDef("avg_r", "Avg R", "r", 2, "higher", "Mean r_multiple over trades where R is known."),
    MetricDef("final_equity", "Final equity", "inr", 0, "higher", "Capital + net P&L."),
)

def metric_defs() -> list[dict]:
    return [asdict(m) for m in METRICS]
```

**Tests:** `tests/test_metric_registry.py`. Keys are unique. No `unit == "r"` except `avg_r`.
`expectancy.unit == "inr"`.
**Done when:** the tests pass and the module is importable.

### D2 — Fix `lib/stolgo/report/metrics.py`

1. Sortino: replace the block with
   ```python
   downside_rms = float(np.sqrt(np.mean(np.minimum(rets.to_numpy(), 0.0) ** 2))) if len(rets) > 1 else 0.0
   sortino = float(rets.mean() / downside_rms * math.sqrt(TRADING_DAYS_PER_YEAR)) if downside_rms > 0 else float("nan")
   ```
2. `profit_factor`: `gross_profit / gross_loss if gross_loss > 0 else float("nan")`.
   `payoff`: `nan` when there are no losses or no wins.
3. `turnover`: keep the formula but return `float("nan")` when `trades` has a `structure`
   column whose values are not in `{"long","short"}`.
4. Add a docstring line: *"Assumes one equity point per trading day. For sparse or per-trade
   equity use `stolgo.report.run_metrics.compute_run_metrics`."*
5. Do **not** change the signature. `Backtest` still calls it for bar-based strategies whose equity is per bar.

**Tests:** update `tests/test_report_metrics.py`. Add a case where returns `[0.01, -0.02, 0.01, 0.0]`
give Sortino `mean / sqrt(mean(min(r,0)^2)) * sqrt(252)`. Add a case with no losses: PF is NaN.
**Done when:** the full suite is green.

### D3 — Session calendar + daily P&L `lib/stolgo/report/daily.py` (new)

```python
IST = "Asia/Kolkata"

def sessions_from_ohlcv(ohlcv: pd.DataFrame) -> pd.DatetimeIndex:
    """Unique IST dates (tz-naive, normalized) that have at least one bar."""

def load_calendar(runs_dir: Path, exchange: str) -> pd.DatetimeIndex:
    """Read runs/_calendars/{exchange}.parquet column 'session'. Raise FileNotFoundError if absent."""

def build_calendar_files(runs_dir: Path) -> dict[str, int]:
    """Union of sessions_from_ohlcv over every runs/*/parquet/ohlcv.parquet grouped by exchange
    (NIFTY→NSE, SENSEX→BSE; exchange read from manifest instrument/params.index or run_id prefix).
    Writes runs/_calendars/NSE.parquet and BSE.parquet. Returns {exchange: n_sessions}."""

def build_daily(trades: pd.DataFrame, capital: float, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Return the daily.parquet frame (§3.4).
    - window = [IST date of min(entry_ts), IST date of max(exit_ts)]
    - sessions restricted to the window; if an exit date is not in `sessions`, raise ValueError
      naming the date (do NOT silently add it)
    - pnl = groupby(IST exit date).net_pnl.sum(); missing sessions → 0.0
    - if any trade has net_pnl NaN → that session's pnl = NaN
    """
```

**Tests:** `tests/test_daily.py`. (a) Two trades on the same session sum up. (b) Idle sessions are 0.
(c) An exit on a non-session date raises. (d) Drawdown includes the initial capital: a first-day
loss of 10 on capital 100 gives drawdown −0.10.
**Done when:** the tests pass.

### D4 — One entry point for run metrics `lib/stolgo/report/run_metrics.py` (new)

```python
def compute_run_metrics(trades: pd.DataFrame, capital: float, daily: pd.DataFrame,
                        *, intraday_equity: pd.Series | None = None) -> dict:
    """Return the manifest v2 `metrics` dict (§3.1), all keys present, NaN→None applied last."""
```

Steps (exactly):
1. `daily_pnl = pd.Series(daily.pnl.values, index=pd.DatetimeIndex(daily.session).tz_localize(IST) + pd.Timedelta(hours=15, minutes=30)).tz_convert("UTC")`
2. `m, _ = calendar_metrics(daily_pnl, capital, trades_for_legacy, intraday_equity=intraday_equity)`, where
   `trades_for_legacy = trades.rename(columns={"fees":"commission"})` (calendar_metrics → compute_metrics
   reads `net_pnl`, `qty`, `entry_price`, `exit_price`; pass `entry_price = premium_entry` when present, otherwise drop
   those columns so turnover is removed).
3. Overwrite `total_return = trades.net_pnl.sum() / capital` (must equal `m["total_return"]` within 1e-9. Assert it.)
4. Add `net_pnl`, `gross_pnl`, `fees`, `slippage` (sum; `None` if all NaN), `avg_r` (mean of non-NaN `r_multiple`, else None),
   `basis = "calendar_daily"`, `annualised_from_short_window = len(daily) < 252`.
5. Remove the keys `mar`, `exposure_pct`, `turnover`.
6. Replace every NaN/±inf with `None`.

**Tests:** `tests/test_run_metrics.py`. Use the fixture below (a copy of the real benchmark trades). Put
`tests/fixtures/nifty_0dte_benchmark_trades.parquet` and `tests/fixtures/nse_sessions_2023_2026.parquet`
in place by copying from `runs/` during the task. Assert against
`docs/plans/fixtures/expected_after_migration.json["runs"]["nifty-0dte-strangle-benchmark"]["expected"]`
with `abs=1e-3` for ratios and `rel=1e-6` for `total_return`.
**Done when:** the benchmark gives total_return 0.168504, cagr 0.053554, sharpe 0.733541, and
sortino 1.558107 (±1e-3).

### D5 — Timestamp policy + validator `lib/stolgo/report/validate.py` (new)

```python
MARKET_HOURS_UTC = {"NSE": (dt.time(3, 30), dt.time(10, 15)), "BSE": (dt.time(3, 30), dt.time(10, 15))}

class RunValidationError(ValueError): ...

def assert_utc(series: pd.Series, name: str) -> None       # tz must be UTC
def looks_like_ist_labelled_utc(ts: pd.Series, exchange: str) -> bool:
    """True if > 50% of timestamps fall outside MARKET_HOURS_UTC but inside the same window shifted by +5:30."""
def fix_ist_labelled_utc(ts: pd.Series) -> pd.Series:
    """ts.dt.tz_localize(None).dt.tz_localize('Asia/Kolkata').dt.tz_convert('UTC')"""
def validate_run_frames(trades, daily, legs=None, exchange="NSE") -> list[str]:
    """Return list of problems. Checks: UTC tz on entry/exit; every entry/exit inside market hours;
    exit_ts >= entry_ts; net_pnl == gross_pnl − fees − slippage (±0.05) where slippage not NaN;
    daily sessions unique+sorted; daily.pnl.sum() == trades.net_pnl.sum() (±0.01)."""
```

`export_all` (D9) raises `RunValidationError` when the list is non-empty.
**Tests:** `tests/test_validate.py`. Use a synthetic 09:21Z/14:30Z frame. `looks_like_ist_labelled_utc`
returns True and after the fix the times are 03:51Z/09:00Z. A correct 04:00Z/09:15Z frame returns False.

### D6 — Trade schema v2 normaliser `lib/stolgo/report/trade_schema.py` (new)

```python
TRADE_V2_REQUIRED = ["trade_id","session_date","entry_ts","exit_ts","side","structure","market","qty",
                     "gross_pnl","fees","slippage","net_pnl","exit_reason","data_flag"]
TRADE_V2_OPTIONAL = ["dte","expiry","lots","underlying_entry","underlying_exit","premium_entry","premium_exit",
                     "r_multiple","risk_inr","legs_label","source_tag"]
LEG_TAG_RE = re.compile(r"([+-])([CP])(\d+)(?:\(([\d.]+)->([\d.]+)\))?")

@dataclass(frozen=True)
class SourceMapping:
    price_columns: Literal["underlying", "premium", "none"]   # meaning of entry_price/exit_price
    structure: str
    market: str | None             # None → take from row column "market"/"index"
    lot_size: int | None
    side: Literal["SHORT", "LONG", "from_column"]

def normalize_trades(df: pd.DataFrame, mapping: SourceMapping) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Return (trades_v2, legs_v2 or None). Never mutates df."""
```

Rules inside `normalize_trades`:
1. `trade_id`: keep if present, else `range(1, n+1)` after sorting by `entry_ts`.
2. `fees` ← `commission` (or `fees` if both exist and are equal; if they differ, keep `fees` and add a warning).
3. `slippage` ← `slippage` column if present, else the §3.2 rule.
4. `entry_price/exit_price` → `underlying_*` or `premium_*` per `mapping.price_columns`. Then **drop** `entry_price/exit_price`.
   Sanity assert: underlying values > 5,000; premium values < 5,000 (NIFTY/SENSEX only). Raise on violation.
5. `r_multiple`: keep. If the column is absent → NaN. **Never fill with 0.**
6. `exit_reason` and `data_flag` from §3.5. Source priority: `exit_reason` column > `tag`.
7. Legs: if `source_tag` matches `LEG_TAG_RE` at least once → build `legs_v2` (`-` → `SELL`, `+` → `BUY`;
   `C` → `CE`, `P` → `PE`; missing premiums → NaN) and set `legs_label` = the matched tokens without the premiums, joined by space.
8. `lots` = `qty / lot_size` if `lot_size` and the division is an exact integer, else `<NA>`.
9. Column order: REQUIRED, then OPTIONAL present, then any remaining source columns.

**Tests:** `tests/test_trade_schema.py` with 4 cases taken verbatim from the real data:
- `'-C24150(17.1->34.1) -P23950(8.9->4.2)'`, price=underlying → 2 legs, both SELL, premiums parsed. `underlying_entry=24063.5`.
- `'-C20200(16.4->0.4) -P20100(28.1->30.6) +C20400 +P19900'` → 4 legs, wings BUY with NaN premiums.
- validated row (`tag='MISSING_SPOT'`, entry_price NaN, has `slippage`) → `exit_reason='DATA_EXIT'`, `data_flag='MISSING_SPOT'`, `r_multiple` NaN, `underlying_entry` NaN.
- a G1 row (`tag='top1-sensex-1dte-strangle'`, entry_price 391.29, price=premium) → `premium_entry=391.29`, `legs=None`.

### D7 — Robustness `lib/stolgo/report/robustness.py` (new) — use this code verbatim

```python
import numpy as np

def robustness(net_pnl, *, resamples: int = 4000, seed: int = 7) -> dict:
    p = np.asarray(net_pnl, dtype=float)
    p = p[np.isfinite(p)]
    k = len(p)
    if k < 2:
        return {"method": "bootstrap_trade_pnl", "seed": seed, "resamples": resamples, "p_net_positive": None,
                "pf_p05": None, "pf_p95": None, "net_p05": None, "net_p95": None,
                "net_without_top5": None, "net_without_top10": None, "longest_losing_streak": None}
    rng = np.random.default_rng(seed)
    s = p[rng.integers(0, k, (resamples, k))]
    net = s.sum(1)
    wins = np.where(s > 0, s, 0).sum(1)
    losses = -np.where(s < 0, s, 0).sum(1)
    pf = np.where(losses > 0, wins / np.where(losses > 0, losses, 1), np.nan)
    srt = np.sort(p)[::-1]
    streak = longest = 0
    for v in p:
        streak = streak + 1 if v < 0 else 0
        longest = max(longest, streak)
    return {"method": "bootstrap_trade_pnl", "seed": seed, "resamples": resamples,
            "p_net_positive": float((net > 0).mean()),
            "pf_p05": float(np.nanpercentile(pf, 5)), "pf_p95": float(np.nanpercentile(pf, 95)),
            "net_p05": float(np.percentile(net, 5)), "net_p95": float(np.percentile(net, 95)),
            "net_without_top5": float(p.sum() - srt[:5].sum()) if k > 5 else None,
            "net_without_top10": float(p.sum() - srt[:10].sum()) if k > 10 else None,
            "longest_losing_streak": int(longest)}
```

`net_pnl` must be passed **in `trade_id` order**. The streak depends on the order.
**Tests:** `tests/test_robustness.py`. Compare with `expected_robustness` in the fixture for the benchmark
(abs 1e-9 for the deterministic fields, 1e-6 for the bootstrap fields).

### D8 — Diagnostics + quality `lib/stolgo/report/diagnostics.py` and `lib/stolgo/report/quality.py` (new)

`diagnostics.build_diagnostics(trades_v2, daily, capital, source_manifest: dict) -> dict` returns
the §3.1 `diagnostics` block:

- `exit_reasons`: `trades_v2.exit_reason.value_counts()` as a dict ordered by count desc.
- `data_quality.trades_with_missing_data` = `(trades_v2.data_flag != "").sum()`. `missing_reasons` = counts per flag.
  `unresolved_sessions`/`skipped_sessions`/`eligible_sessions` ← source metrics keys `unresolved`/`skipped`/`eligible`
  (or `params.eligible_sessions`), otherwise `0`/`0`/`null`.
- `stability`: split trades by `trade_id` into the first `ceil(n/2)` and the rest. For each half: trades, net_pnl, hit_rate, start/end session.
- `monthly`: from `daily`, group by `session[:7]`. `months`, `profitable_months` (pnl > 0),
  `mean_monthly_pct` and `median_monthly_pct` = mean/median of `pnl / capital`.
- `extremes`: `best_trade`/`worst_trade` from net_pnl. `worst_mtm`/`max_stop_overshoot` ← source metrics if present, else `null`.
- `decision_counts` ← `source_manifest.params.decision_counts` or `null`.
- `validation` ← `params.validation_status`, `params.audit_summary`, `params.model_limitations` (list),
  `caveats` = `[params.caveat]` if present, `params.ledger_audit`, `params.report_available` or `audit.html` exists.

`quality.py` defines the module constants `MIN_TRADES_OK = 100`, `MIN_SESSIONS_OK = 252` and `DATA_ISSUE_THRESHOLD = 0.05`, and uses only these names.
`quality.run_status(name, metrics, diagnostics, sessions) -> tuple[str, list[str]]` implements the §3.1 precedence.
Expected with today's runs: 8 `ok`, 15 `low_sample`, 99 `data_issues`, 2 `superseded`, 4 `empty`.
Reason strings exactly:
`"0 trades"`, `"marked superseded"`, `"{x} of {n} trades exited on missing data"`, `"{u} unresolved sessions"`,
`"{n} trades < 100"`, `"{s} sessions < 252"`.

**Tests:** `tests/test_diagnostics.py`, `tests/test_quality.py`. Use one synthetic frame per status value.

### D9 — Exporter v2 `lib/stolgo/report/exporters.py`

1. Add `export_run_v2(directory, *, run_id, name, trades_v2, legs_v2, daily, instrument, group, config,
   metrics, robustness, diagnostics, ohlcv=None, intraday_equity=None, extra_files: dict[str, Path] | None = None)`.
   It writes the §2 layout atomically (tmp dir + `_replace_directory`), calls `validate.validate_run_frames` first,
   writes `manifest.json` with `schema_version: 2`, `json.dumps(..., allow_nan=False)` (this fails loudly if a NaN slipped through),
   and upserts the index.
2. Change `export_all(result, directory, *, strategy_name=None, capital=None, instrument=None)` so that it builds v2 frames:
   `normalize_trades(result.trades, SourceMapping(price_columns="underlying" if bar-based else …))`.
   For bar-based `Backtest` results, use `structure="long"`/`"short"` from the trade side, and
   `sessions = sessions_from_ohlcv(result.ohlcv)` (UTC dates for non-IST markets).
   Keep writing `summary.json`, `trades.csv`, `tearsheet.html`.
3. Stop writing `drawdown.parquet`.
4. `config.code_version` = the output of `git rev-parse --short HEAD` if available, else `null`. Never fail on it.

**Tests:** update `tests/test_report_exporters.py`. After `export_all` on the existing synthetic backtest,
`manifest.json` has `schema_version == 2`, `metrics.basis == "calendar_daily"`, and `daily.parquet` exists.
`json.loads` of the manifest contains no NaN.

### D10 — Migration `scripts/migrate_runs_v2.py` (new, idempotent)

CLI: `PYTHONPATH=lib python scripts/migrate_runs_v2.py --runs-dir runs [--dry-run] [--only RUN_ID ...]`

Algorithm:
1. If `runs/_backup_v1/` does not exist, copy every `runs/<id>/` (not `_*`) there first. **Never modify a backup.**
2. `build_calendar_files(runs_dir)` → print the session counts (expected with today’s runs: NSE 917 sessions 2023-01-02→2026-09-11, BSE 829 sessions 2023-05-15→2026-09-11).
3. For each run dir with `manifest.json` where `schema_version != 2`, pick its **group rule** (§5.1). Load the frames
   from **`runs/_backup_v1/<id>`** (source of truth, so re-runs are idempotent). Normalise. Build daily with the run's own
   ohlcv sessions if `ohlcv.parquet` exists, else `load_calendar(exchange)`. Compute metrics, robustness, diagnostics and status.
   Then `export_run_v2`, copying `tearsheet.html`, `summary.json`, `audit.html` (if present), `ohlcv.parquet`, `equity.parquet` (validated
   runs only, as the intraday equity) unchanged.
4. Validated runs (group G5) **keep their source metrics** for `cagr, sharpe, sortino, calmar, max_drawdown,
   max_drawdown_duration, intraday_max_drawdown, worst_day, expected_shortfall_95` (already calendar-based). Recompute
   everything else. Then assert the recomputed `sharpe` matches the source within 0.02. If not, log it and keep the source values.
5. Write `runs/_migration_report.md`. It has one table row per run: id, group, status, old→new total_return/CAGR/Sharpe,
   and the warnings.
6. Compare the result with `docs/plans/fixtures/expected_after_migration.json` for the 22 legacy runs. Exit code 1 on a mismatch
   beyond the tolerance stated in that file.

#### 5.1 Group rules (exact)

| group | how to detect (on `run_id`) | runs | timestamps | `price_columns` | structure | markets / dte | extra |
|---|---|---|---|---|---|---|---|
| **G1** weekly legacy | `^(NIFTY|SENSEX)-(strangle|iron-condor)-(0|1)dte$`, `^top[123]-`, `^combined-top3-` | 12 | **fix IST-labelled** (D5) | `premium` | from name: strangle→`short_strangle`, iron-condor→`iron_condor` | from name. **Overrides:** `top1-sensex-1dte-strangle`→SENSEX,[1]. `top2-nifty-pre-expiry-strangle`→NIFTY,[1,2]. `top3-nifty-0dte-strangle`→NIFTY,[0]. `combined-top3-weekly-calendar`→["NIFTY","SENSEX"],[0,1,2], structure `short_strangle` | lot_size: NIFTY 65, SENSEX 20 |
| **G2** 3y legacy | `^(nifty|sensex)-(0|1)dte-(strangle-benchmark|iron-condor-otm1-w4|iron-fly-atm-w5)$` | 8 | already UTC | `underlying` | strangle-benchmark→`short_strangle`, iron-condor→`iron_condor`, iron-fly→`iron_fly` | from name | legs from tag. lot_size = the trade `qty` (varies across years; do not assume) |
| **G3** S/R audited | `^nifty-sr-audited-` | 6 | already UTC | `premium` (`filled_entry_credit` wins if present) | from `side` + strikes: bear call / bull put → `bear_call_spread`/`bull_put_spread`; unknown → `unknown` | NIFTY, dte from column | keep every extra column. 3 runs have 0 trades → status `empty` |
| **G4** premium spike | `^nifty-sr-premium-spike-` | 3 | already UTC | `premium` | from tag prefix (`…bear_call…`→`bear_call_spread`) | NIFTY | set `raw_params.superseded = true` (names start with INVALID) |
| **G5** validated timing | `^validated-timing-3y-(nifty|sensex)-(0|1)dte-(.+)$` | 99 | already UTC | `none` | `short_strangle` | from regex | `group = {"id":"validated-timing-3y","label":"3-year timing sweep","axes":{"market":M,"dte":D,"family":F,"cap":C,"d":Dv,"w":W}}`. Variant parse: `(a|b|c|d)-cap(\d+)-d(\d)(?:-w(\d))?` → family A–D; `cut-d(\d)` → CUT; `static` → STATIC; `static-leg100-close-all` → LEG100; `exit-touch` → EXIT_TOUCH; `one-conversion` → ONE_CONV. Missing axes = `null`. Copy `params.execution` → `config.execution`, `params.caveat` → diagnostics.validation.caveats, `params.window` → check against the computed window |

Any run matching **no** rule: skip it, log `UNMAPPED`, exit code 2 at the end (after processing the rest).

**Done when:**
- `--dry-run` prints 128 runs mapped, 0 unmapped.
- A real run produces 128 v2 manifests, and a second run is a no-op (the same files byte for byte except `migrated_at`).
- The fixture comparison passes.
- `runs/_migration_report.md` exists.

### D11 — Index, adapters, server

1. `lib/stolgo/ui/index.py`: `SCHEMA_VERSION = 2`. Add the columns `name VARCHAR, status VARCHAR, group_id VARCHAR,
   summary JSON` (the §4.1 object). `reconcile()` re-reads every manifest whose mtime changed. If the table is v1, drop and rebuild it.
2. `lib/stolgo/ui/adapters.py`: replace the module with pure functions:
   `run_summary_v2(manifest) -> dict` (§4.1), `run_detail_v2(manifest) -> dict` (§4.2 incl. `metric_defs()`),
   `trades_v2_rows(df) -> dict` (§4.5), `daily_rows(df)`, `monthly_rows(daily_df, capital)`, `candles(ohlcv, tf, frm, to)`,
   `trade_detail(trades_df, legs_df, ohlcv, trade_id)`.
   Every function converts NaN/inf → `None` via one helper `_clean(obj)`.
3. `lib/stolgo/ui/server.py`: add the §4 endpoints. For manifests with `schema_version == 1`, return
   `409 {"detail":"run_not_migrated","hint":"python scripts/migrate_runs_v2.py"}` from detail endpoints, and exclude them from
   `/api/runs` with `warnings += 1`.
4. Remove the `side` keyword inference and the `pnlClass` field.

**Tests:** update `tests/test_ui_adapters.py` and `tests/test_ui_server.py` (FastAPI TestClient) against a temporary
runs dir with one v2 run built by `export_run_v2`. Assert every §4 endpoint's keys and the null handling.

### D12 — Docs

Update `docs/UI.md`: the artifacts list (§2), the migration command, and a short "metric basis" note.
Delete the stale references to `drawdown.parquet`.

---

## 6. Order, estimates, checkpoints

| step | tasks | checkpoint (must be true before moving on) |
|---|---|---|
| 1 | P0, D1, D2 | suite green |
| 2 | D3, D4, D5 | the benchmark fixture numbers match |
| 3 | D6, D7, D8 | the 4 verbatim tag cases pass. The robustness fixture matches |
| 4 | D9 | the exporter test writes v2 |
| 5 | D10 | `--dry-run` 128/0. The real run + idempotency + fixture comparison pass |
| 6 | D11, D12 | every endpoint test passes. `stolgo serve` starts. `curl /api/runs \| jq '.items \| length'` = 128 |

Commit after each step with message `data-v2: step N — <tasks>`.

## 7. Guardrails — do NOT

- Do not edit anything under `runs/_backup_v1/`.
- Do not fill unknown values with `0`. Use NaN in frames and `null` in JSON.
- Do not compute Sharpe/CAGR from per-trade or per-bar equity anywhere in the run pipeline. Only `compute_run_metrics` may do it.
- Do not change strategy logic or `lib/stolgo/options/replay.py`.
- Do not delete `summary.json`/`tearsheet.html`. Other tools read them.
- Do not add new Python dependencies.
- External generators (AlgoTrader research) are out of scope. Open a follow-up issue named
  "Adopt export_run_v2 in research generators" that links this plan.
