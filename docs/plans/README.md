# Stolgo — data fix + UI revamp plans (2026-09-28)

Read in this order:

1. **`01_DATA_CONTRACT_FIX_PLAN.md`**: fixes the wrong numbers (Sharpe/CAGR annualisation, the total-return base,
   Sortino, IST-labelled-as-UTC timestamps, mislabelled price columns). Defines run schema v2 and API contract v2,
   and migrates all 128 runs in `runs/`. **Do this first.** The UI depends on its §4.
2. **`02_UI_REVAMP_PLAN.md`**: rebuilds every frontend page in the "Cockpit" design against API v2.
3. **`../design/README.md`**: the visual contract (PNGs, HTML mockups, tokens, component CSS).

Supporting files:

| Path | Purpose |
|---|---|
| `fixtures/expected_after_migration.json` | Ground-truth metrics + robustness for the 22 legacy runs after migration. D4, D7 and D10 assert against it |
| `QUESTIONS.md` | Write every ambiguity or plan↔code conflict here instead of guessing |

Headline numbers the implementer should see change (old → new):

| Run | Sharpe | CAGR | Total return |
|---|---|---|---|
| nifty-0dte-strangle-benchmark | 1.66 → **0.73** | 29.5% → **5.4%** | 17.5% → **16.9%** |
| sensex-0dte-strangle-benchmark | 1.39 → **0.65** | 25.2% → **4.9%** | 15.0% → **15.3%** |
| top1-sensex-1dte-strangle | 12.20 → **4.78** | 385% → **44%** (65 sessions, flagged) | 9.2% → **9.6%** |
| combined-top3-weekly-calendar | 7.78 → **5.98** | 75% → **45%** (flagged) | 9.3% → **9.6%** |

Also new: every one of the 99 `validated-timing-3y-*` runs has 7–22% of trades that exited because market data
went missing. They get status `data_issues`.
