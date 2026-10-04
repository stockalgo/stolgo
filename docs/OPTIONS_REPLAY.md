# Multi-contract options research

`stolgo.options.replay` provides a specialized intraday options runner alongside
the single-symbol `Engine`. Every actual fill goes through Stolgo `SimBroker` and
`NextOpenFill`, with a separate broker per immutable contract. It is a simulator;
it does not submit live orders or authenticate vendor contract identities.

**Status: experimental.** The options replay API (`stolgo.options`) may change
without notice between releases. Read "Known limitations" below before relying
on its results.

`OptionSession` contains a continuous explicit minute grid, contract keys, spot
observations and NumPy OHLCV arrays. `ReplayConfig` selects a deterministic policy.
`replay_session` returns session P&L, explicit charges/slippage, fills, closed legs,
state decisions and optionally a minute liquidation-value path.

`ReplayConfig.target` (profit target as a fraction of the initial credit) and
`ReplayConfig.hard_loss` (whole-session loss limit in rupees) are `None` by
default, which switches that exit rule off. Pass them explicitly, for example
`ReplayConfig("name", target=0.75, hard_loss=2500.0)`. The dict returned by
`replay_session` includes the complete configuration under `config`, so saved
results show which rules were active.

Signals use completed minutes. An entry can fill only on a subsequent bar; an
adjustment closes old shorts before opening replacements on a later bar. Daily
risk, time and data failures take priority over opening new risk. Missing held
quotes never produce an entry-price fallback; unrecoverable exits return unknown
P&L and must not be aggregated into a purported complete return.

The Indian charge model has dated STT and disclosed exchange-charge proxies.
Historical SPAN/ELM, partial opening fills, actual spreads and order-book capacity
are not simulated. No production margin or capital feasibility is implied.

`stolgo.report.calendar_metrics.calendar_metrics` accepts a complete daily
exchange-session P&L series (idle days zero, unknown days NaN) and explicitly
includes initial equity. It uses elapsed calendar time for CAGR and all daily
observations for Sharpe. Optional intraday equity gives separately labeled
intraday drawdown. Unknown P&L is rejected for complete-performance metrics.

The prepared three-year experiment, all expiry/monthly reports and reproducible
scripts are documented in an external research report (not part of this repo).

Targeted checks:

```bash
PYTHONPATH=lib .venv/bin/python -m pytest tests/test_options_replay.py tests/test_calendar_metrics.py -q
```

The generic resting-stop matcher now uses a gap-aware trigger price, rather than
unconditionally returning the bar open after a later intrabar trigger. OHLC
ambiguity and stop-limit queue/fill behavior still require more detailed models
for strategies that depend on intrabar order ordering.

## Known limitations

- `STATIC` requires spot only for entry strike selection. Scenarios with
  spot-based adjustments still exit (`MISSING_SPOT`) on missing held-session
  spot observations.
- **One quiet minute can force an exit.** A held option with no usable trade
  price for a minute cannot be marked, so the replay queues an exit
  (`MISSING_HELD_QUOTE`). Entries and replacement legs also require
  `volume > 0` as a coarse liquidity check, which a thinly traded minute can
  fail even though trade prices alone say nothing about available depth.
- **Fixed rupee limits are not comparable across periods.** `hard_loss` is a
  fixed rupee amount for the whole position, and the entry premium floor is a
  fixed rupee-per-unit threshold. The contract lot size changed roughly
  threefold between 2024 and 2026, so the same limit is a different fraction of
  notional in different periods. Do not compare results from different periods
  directly.
