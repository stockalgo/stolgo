# Execution model

How the backtest `Engine` turns strategy orders into fills. Everything here
describes the simulator in `lib/stolgo/core/engine.py` and `lib/stolgo/oms/`; it
is deterministic and uses only the OHLCV bars you give it (no bid/ask, queue
position, volume limits or partial fills).

## Bar loop

For every bar `t` the engine does, in this order:

1. Match orders that are already waiting against bar `t`.
2. Apply any orders created by those fills (for example bracket stop/target
   orders) and match them against bar `t` where the mode allows it (see below).
3. Mark the portfolio to market at bar `t`'s close.
4. Call `Strategy.on_bar(ctx)`; orders it creates are submitted.

Fills are applied **one at a time**, in order. After each fill the portfolio
(cash and position) is updated before the next order is checked, so the cash
check and `size_pct` sizing of a later fill in the same bar see the effect of
earlier fills.

Before `on_bar`, fill callbacks see only previously completed candles through
`ctx.data`; the full vector view supplied to `on_start` is restricted before
runtime callbacks. Signal-close callbacks run after `on_bar` and can see that
bar's completed candle.

## Fill timing by `fill_on`

| `fill_on` | Market order created in `on_bar` at bar `t` fills at |
|---|---|
| `"next_open"` (default) | open of bar `t+1` |
| `"next_close"` | close of bar `t+1` |
| `"signal_close"` | close of bar `t` itself, right after `on_bar` |

`"close"` is a deprecated alias of `"next_close"` and emits a
`DeprecationWarning`.

`ctx.order(active_from=t)` can defer any order type until bar index `t`.
The engine uses the later of this explicit index and the earliest bar permitted
by the fill mode. Deferred signal-close markets still execute at the close.

Limit and stop orders created in `on_bar` at bar `t` become active on bar
`t+1` in every mode. Orders created as a reaction to a fill (a bracket's stop
and target after its entry fills):

- `next_open`: active on the same bar as the entry fill. An entry at the open
  can therefore be stopped out, or hit its target, within that same bar.
- `next_close` and `signal_close`: active from the following bar.

## Order types and gaps

Prices below are before slippage and commission.

| Order | Triggers when | Fills at |
|---|---|---|
| Market | per `fill_on` above | the open or close given above |
| Limit buy | `low <= limit` | `min(open, limit)` |
| Limit sell | `high >= limit` | `max(open, limit)` |
| Stop buy | `high >= stop` | `max(open, stop)` |
| Stop sell | `low <= stop` | `min(open, stop)` |

So a gap through a limit fills at the (better) open, and a gap through a stop
fills at the (worse) open rather than at the stop price.

**Limits fill on a touch.** A limit order fills as soon as the bar's range
touches its price, even if only by one tick. There is no queue position or
volume check, so limit fills are optimistic.

## Stop and target pairs (one-cancels-other)

When both legs of an OCO group (such as a bracket's stop and target) are
triggered within one bar, the bar's open decides, because OHLC data does not
say which was hit first:

1. If the open has already crossed exactly one leg's trigger, that leg fills,
   at the open if the bar gapped through it. A bar that gaps up through a
   long's target fills the target at the open, not the stop.
2. If the open has crossed neither leg (both were reached later in the bar),
   the **stop** fills (adverse-first).
3. If the open has crossed both, the stop fills.

The other leg is cancelled. If only one leg is triggered in the bar, that leg
fills.

Exit orders from brackets are `reduce_only`: they never open or flip a
position, their size is capped at the open position, and they are cancelled
when the position is already flat.

A bracket entry that would fill at or beyond its own stop price (a gap through
the stop) is rejected with an `OrderRejectedEvent` (`gap_through_stop`) and its
exit orders are never placed.

## Slippage and commission

Both are configured on `RunConfig` and apply to every fill, including limit and
stop fills and the end-of-data close.

- `slippage_bps` (default `0.0`): the fill price moves against you by that many
  basis points, up for buys and down for sells. Because it is applied after the
  fill price is chosen, a limit buy can fill slightly above its limit when
  `slippage_bps > 0`.
- `commission` (default `0.0`): a proportional fee, `price * qty * commission`,
  charged on each fill on both sides.

## Cash check and shorting

For buys, when `allow_leverage=False` (default), a fill is rejected with an
`OrderRejectedEvent` (`insufficient_cash`) if `price * qty + commission` (price after
slippage) exceeds available cash at fill time. A rejected order is dropped, not retried. This
check also applies to ordinary buy orders that cover shorts.

Reduce-only exits (`ctx.close`, bracket exits and the end-of-data close) are
exempt from this cash check: covering a losing short reduces exposure even
when the loss exceeds cash. Such a liquidation can leave negative cash; CAGR
is undefined once final equity is non-positive. Repeated `ctx.close` calls
cannot reverse a position.

Sells are **not** checked: there is no margin model for short positions yet.
You can open a short of any size, so size shorts yourself and do not read short
results as margin-constrained.

`size_pct` and `size_risk_pct` orders are sized at fill time from the cash and
equity available then.

## End of data

- With `close_at_end=True` (default) an open position is closed with a market
  order at the **last bar's close** (tag `END_OF_DATA`), with slippage and
  commission applied.
- With `close_at_end=False` the position stays open. The trade log gets one row
  with `exit_reason == "OPEN"`, marked at the last close.
- Every order still pending or resting is cancelled; none can fill after the
  last bar. Brackets whose entry never filled are dropped before
  `Strategy.on_end` runs.

## Client order ids

`ctx.buy`, `ctx.sell` and `ctx.order` take an optional `client_order_id`. The
engine generates ids with the reserved `_auto-` prefix when you do not pass one.
Passing an id you have already used in the run, or one starting with `_auto-`,
raises `ValueError`. The id is carried on the order and its fills, which is how
brackets recognise their own entry fill.
