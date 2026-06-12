# stolgo.pa — Price action library

## Import (flat API)

```python
import stolgo.pa as pa
from stolgo import trade
```

Do not import `stolgo.pa.levels` in user code — all public names live on `pa`.

## Grammar

| Concept | Type | Example |
|---------|------|---------|
| Level | price series | `r = pa.resistance(20)` |
| Rule | bool series | `pa.crosses_above(r)` |
| Combine | `&` `\|` `~` | `pa.consolidation(7) & pa.crosses_above(r)` |
| Sequence | `.then()` | `pa.streak.green(3).then(pa.bearish_engulfing())` |
| Risk | `trade.*` | `trade.long(ctx, rr=(1,2), stop="candle_low")` |

## Levels

`resistance`, `support`, `donchian_high`, `donchian_low`, `level`, `level_from_series`, `cluster`, `range_high`, `range_low`

Multi-timeframe: `pa.resistance(7, tf="1d")` on intraday backtest data.

## Relations

`above`, `below`, `crosses_above`, `crosses_below`, `rejected_at`, `recovered_at`, `near`, `touched`

Aliases: `breaks_above`, `failed_breakout_above`, `bounced_off`, etc.

## Patterns

Candles: `bullish`, `bearish`, `doji`, `hammer`, `bullish_engulfing`, …

Streaks: `pa.streak.green(3)`, `pa.first_red_day()`

Structure: `consolidation`, `breakout_up`, `breakout_down`

Momentum: `run_up`, `parabolic_up`, `giant_uptrend`

## Presets

`pa.preset.scalp_green_fade()`, `breakout_intraday()`, `failed_break_intraday()`, `parabolic_short()`, `consolidation_breakout()`

## Strategy example

```python
import stolgo.pa as pa
from stolgo import Backtest, Context, Strategy
from stolgo import trade

class Bot(Strategy):
    def on_start(self, ctx):
        self.entry = pa.consolidation(7) & pa.crosses_above(pa.range_high(7))
        self._bracket = None

    def on_bar(self, ctx):
        if self._bracket and trade.bracket_hit(ctx, self._bracket):
            trade.close(ctx, tag=trade.bracket_hit(ctx, self._bracket))
            self._bracket = None
            return
        if ctx.position.flat and self.entry(ctx):
            self._bracket = trade.long(ctx, rr=(1, 4), stop="candle_low")
```

Options trading is out of scope for v1.
