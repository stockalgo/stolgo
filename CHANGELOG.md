# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

The fill model and order handling were tightened. Backtest results can change
for strategies that hit any of the cases under "Fixed" and "Changed". The rules
the engine now follows are written down in
[docs/EXECUTION_MODEL.md](docs/EXECUTION_MODEL.md).

### Fixed

- Explicit `active_from` indices defer all order types, including market
  orders in `signal_close` mode. Runtime fill callbacks no longer inherit
  future candles from `on_start`.
- Percentage-sized reduce-only exits and repeated `ctx.close` calls cannot
  reverse a position. Reduce-only short covers can liquidate losses that
  exceed available cash; CAGR is undefined for non-positive final equity.
- Parabolic next-open entries evaluate exits on their entry day, and target
  gaps receive the open price before any later intrabar stop touch.
- STATIC options replay uses spot only for entry strike selection.
- Trade export preserves engine and replay exit reasons. Shared exit clock
  times no longer turn unknown reasons into inferred time exits.
- Library collections refresh edited manifests and remove deleted exports.
  Frontend file serving rejects paths and symlinks outside the build directory.
- Switching runs invalidates older API requests and clears the previous run's
  data while the selected run loads.
- A market exit and a bracket stop that fill in the same bar no longer open an
  unintended reverse position.
- Fills are applied one at a time within a bar. The buy-side cash check and
  `size_pct` sizing of a later fill now see the cash and position left by
  earlier fills, instead of the state from the start of the bar. Two buys in the
  same bar can no longer both pass a cash check that only one can afford.
- A bracket whose entry order was rejected or never filled no longer captures
  a later, unrelated fill and attaches its stop and target to it.
- Short positions report the correct average entry price (it was `0`), and the
  `OPEN` row in the trade log now shows the real entry price and P&L for an open
  short. Average entry price is also correct when a position flips side.
- When a stop and a target (one-cancels-other) are both hit within one bar, the
  leg the bar's open already crossed fills, at the open if the bar gapped
  through it. Otherwise the stop fills. Previously the stop always won, even
  when the bar gapped up through a long's target.

### Changed

- Frontend tests use patched Vitest 4.1.11. CI checks Python 3.10--3.12,
  frontend tests and builds, lint, and the dependency audit with pinned actions.
- Orders still pending or resting at the end of the data are cancelled, and
  brackets whose entry never filled are dropped before `Strategy.on_end` runs,
  so `on_end` no longer sees a bracket that never got a bar to fill on.
- The `qty` column of the trade log is always `float64`, including when a
  strategy passes whole-number quantities.
- Options replay (`stolgo.options`, now documented as **experimental**):
  `ReplayConfig.target` and `ReplayConfig.hard_loss` default to `None`, which
  turns the profit-target and daily-stop exits off. They used to default to
  `0.75` and `2500.0`. Pass `target=0.75, hard_loss=2500.0` to keep the old
  behaviour. `replay_session` results now include the full `ReplayConfig` under
  `config`.
- Auto-generated client order ids use the reserved `_auto-` prefix (they were
  `cid-<n>`).

### Added

- `client_order_id` on `ctx.buy`, `ctx.sell` and `ctx.order`. The id is carried
  on the order and its fills. Reusing an id within a run, or passing one that
  starts with `_auto-`, raises `ValueError`.
- `docs/EXECUTION_MODEL.md`: fill timing per `fill_on` mode, gap behaviour for
  market, limit and stop orders, the stop/target tie rule, slippage and
  commission, the buy-side cash check and end-of-data behaviour.
- "Status: experimental" note and "Known limitations" section in
  `docs/OPTIONS_REPLAY.md`.
