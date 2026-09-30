"""Parabolic Short Setup screener + trade simulator (HLD §6.1 style, greenfield).

Strategy definition
-------------------
1. Parabolic move: price gains ``>= min_gain_pct`` (e.g. 2.0 == 200%) within a
   trailing ``lookback_days`` window, measured close-vs-trailing-low, with at
   most ``max_interrupt_red_days`` bearish days inside that window and no
   single red day retracing more than ``max_single_day_retrace_pct`` of the
   cumulative dollar gain (the "relatively uninterrupted" requirement).
2. First red day: the first bearish daily candle (``close < open`` and
   ``close`` below the prior close) after the parabolic peak, found by
   scanning forward up to ``max_days_to_find_red`` bars. Preference for
   "strong" reversals is enforced via the volume filter below.
3. Volume filter: the red day's volume must be >= ``volume_multiplier`` times
   the average volume of the ``volume_avg_window`` days preceding the peak.
4. Entry: short at the close of the first red day (``entry_mode="close"``,
   default) or at the next day's open (``entry_mode="next_open"``).
5. Risk: stop-loss = high of the first red day; take-profit = entry minus
   ``r_multiple_target`` times the initial risk (entry to stop distance).

This module is a pure, single-symbol, pandas-in/pandas-out screener — it is
deliberately NOT wired into ``stolgo.core.engine.Engine`` (HLD v0.1/v0.2 is
single-symbol event-driven only; this strategy is inherently a multi-symbol,
per-setup trade simulation, closer to a vectorized trade-log backtest). Use
:func:`backtest_symbol` per symbol and concatenate results across a universe
(see ``examples/parabolic_short_backtest.py``).

No look-ahead: at bar ``t`` only ``df.iloc[:t+1]`` is ever read when deciding
whether ``t`` qualifies; trade simulation only reads bars strictly after the
entry bar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class ParabolicShortConfig:
    """Tunable rules for the parabolic short screener."""

    lookback_days: int = 5  # configurable 3-10 per strategy spec
    min_gain_pct: float = 2.0  # 200% => close/base - 1 >= 2.0
    max_interrupt_red_days: int = 1
    max_single_day_retrace_pct: float = 0.30
    volume_multiplier: float = 1.5
    volume_avg_window: int = 20
    r_multiple_target: float = 4.0  # spec allows 4-5; expose as a single tunable
    entry_mode: Literal["close", "next_open"] = "close"
    max_days_to_find_red: int = 5
    max_holding_days: int = 30
    min_price: float = 0.0  # optional micro-price filter (penny-coin noise)
    cost_bps: float = 0.0  # transaction costs/slippage in bps

    def __post_init__(self) -> None:
        if not (3 <= self.lookback_days <= 10):
            raise ValueError("lookback_days should be within [3, 10] per strategy spec")
        if self.min_gain_pct <= 0:
            raise ValueError("min_gain_pct must be positive")
        if self.entry_mode not in ("close", "next_open"):
            raise ValueError("entry_mode must be 'close' or 'next_open'")


@dataclass(frozen=True, slots=True)
class ParabolicSetup:
    """A detected parabolic-run + first-red-day setup, prior to simulation."""

    symbol: str
    run_base_date: pd.Timestamp
    run_base_price: float
    peak_date: pd.Timestamp
    peak_price: float
    pct_gain: float
    red_day_date: pd.Timestamp
    red_day_open: float
    red_day_high: float
    red_day_low: float
    red_day_close: float
    red_day_volume: float
    avg_volume_before: float
    entry_date: pd.Timestamp
    entry_price: float
    stop_price: float
    target_price: float
    r_value: float  # dollars of risk per unit (stop - entry), > 0


@dataclass(frozen=True, slots=True)
class ParabolicTrade:
    """A simulated trade outcome for a :class:`ParabolicSetup`."""

    setup: ParabolicSetup
    exit_date: pd.Timestamp
    exit_price: float
    exit_reason: Literal["target", "stop", "time", "open"]
    mfe: float  # max favorable excursion, $ per unit
    mae: float  # max adverse excursion, $ per unit
    mfe_r: float
    mae_r: float
    r_multiple: float
    holding_period_days: int
    outcome: Literal["win", "loss", "breakeven", "open"]

    def to_dict(self) -> dict:
        s = self.setup
        return {
            "symbol": s.symbol,
            "run_base_date": s.run_base_date,
            "run_base_price": s.run_base_price,
            "parabolic_peak_date": s.peak_date,
            "peak_price": s.peak_price,
            "pct_gain": s.pct_gain,
            "red_day_date": s.red_day_date,
            "red_day_volume": s.red_day_volume,
            "avg_volume_before": s.avg_volume_before,
            "entry_date": s.entry_date,
            "entry_price": s.entry_price,
            "stop_price": s.stop_price,
            "target_price": s.target_price,
            "r_value": s.r_value,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "mfe": self.mfe,
            "mae": self.mae,
            "mfe_r": self.mfe_r,
            "mae_r": self.mae_r,
            "r_multiple": self.r_multiple,
            "holding_period_days": self.holding_period_days,
            "outcome": self.outcome,
        }


def _validate(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"df missing required OHLCV columns: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("df must have a DatetimeIndex (see stolgo.data.normalize_ohlcv)")
    if not df.index.is_monotonic_increasing:
        raise ValueError("df index must be sorted ascending")


def detect_setups(
    df: pd.DataFrame,
    config: ParabolicShortConfig | None = None,
    *,
    symbol: str = "UNKNOWN",
) -> list[ParabolicSetup]:
    """Scan a single symbol's daily OHLCV for parabolic-short setups.

    Single forward pass, O(n). At each candidate peak index ``i`` only
    ``df.iloc[:i+1]`` is consulted for the run/gain/volume checks; the first
    red day is found by scanning strictly forward from ``i`` (this is
    unavoidable — "first red day after the peak" is only knowable in
    hindsight — but the resulting setup is only ever used to open a trade at
    the red day itself or later, never before it).
    """
    config = config or ParabolicShortConfig()
    _validate(df)

    n = len(df)
    setups: list[ParabolicSetup] = []
    if n <= config.lookback_days + 1:
        return setups

    closes = df["close"].to_numpy()
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    volumes = df["volume"].to_numpy()
    idx = df.index

    i = config.lookback_days
    cooldown_until = -1
    while i < n:
        if i <= cooldown_until:
            i += 1
            continue

        window_start = max(0, i - config.lookback_days)
        base_price = float(lows[window_start:i].min()) if i > window_start else float(lows[i])
        if base_price <= 0 or closes[i] < config.min_price:
            i += 1
            continue

        gain = closes[i] / base_price - 1.0
        if gain < config.min_gain_pct:
            i += 1
            continue

        # "relatively uninterrupted" check over [window_start, i]
        w_opens = opens[window_start : i + 1]
        w_closes = closes[window_start : i + 1]
        red_mask = w_closes < w_opens
        red_count = int(red_mask.sum())
        if red_count > config.max_interrupt_red_days:
            i += 1
            continue

        cumulative_gain_dollars = closes[i] - base_price
        interrupted_too_much = False
        if cumulative_gain_dollars > 0:
            for j in range(len(w_opens)):
                if red_mask[j]:
                    body = w_opens[j] - w_closes[j]
                    if (body / cumulative_gain_dollars) > config.max_single_day_retrace_pct:
                        interrupted_too_much = True
                        break
        if interrupted_too_much:
            i += 1
            continue

        # forward scan for first red day; blow-off tops keep pushing peak_idx
        peak_idx = i
        peak_price = closes[i]
        red_idx: int | None = None
        upper_bound = min(i + 1 + config.max_days_to_find_red, n)
        for k in range(i + 1, upper_bound):
            if closes[k] < opens[k] and closes[k] < closes[k - 1]:
                red_idx = k
                break
            if closes[k] > peak_price:
                peak_price = closes[k]
                peak_idx = k
            # else: green/flat but not a new high — keep scanning, not yet a
            # reversal (ignore intraday pullbacks per spec)

        if red_idx is None:
            i += 1
            continue

        vol_start = max(0, peak_idx - config.volume_avg_window)
        avg_volume = float(volumes[vol_start:peak_idx].mean()) if peak_idx > vol_start else 0.0
        red_volume = float(volumes[red_idx])
        if avg_volume <= 0 or red_volume < avg_volume * config.volume_multiplier:
            cooldown_until = red_idx
            i = red_idx + 1
            continue

        if config.entry_mode == "close":
            entry_idx = red_idx
            entry_price = float(closes[red_idx])
        else:
            if red_idx + 1 >= n:
                cooldown_until = red_idx
                i = red_idx + 1
                continue
            entry_idx = red_idx + 1
            entry_price = float(opens[red_idx + 1])

        stop_price = float(highs[red_idx])
        if stop_price <= entry_price:
            cooldown_until = red_idx
            i = red_idx + 1
            continue

        r_value = stop_price - entry_price
        target_price = entry_price - config.r_multiple_target * r_value
        pct_gain = peak_price / base_price - 1.0

        setups.append(
            ParabolicSetup(
                symbol=symbol,
                run_base_date=idx[window_start],
                run_base_price=base_price,
                peak_date=idx[peak_idx],
                peak_price=float(peak_price),
                pct_gain=float(pct_gain),
                red_day_date=idx[red_idx],
                red_day_open=float(opens[red_idx]),
                red_day_high=float(highs[red_idx]),
                red_day_low=float(lows[red_idx]),
                red_day_close=float(closes[red_idx]),
                red_day_volume=red_volume,
                avg_volume_before=avg_volume,
                entry_date=idx[entry_idx],
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                r_value=r_value,
            )
        )
        cooldown_until = red_idx
        i = red_idx + 1

    return setups


def simulate_trade(
    df: pd.DataFrame,
    setup: ParabolicSetup,
    config: ParabolicShortConfig | None = None,
) -> ParabolicTrade | None:
    """Walk forward bar-by-bar from the entry bar to resolve stop/target/time exit.

    Returns ``None`` if the entry bar can't be located in ``df`` (defensive;
    should not happen when ``df`` is the same frame passed to
    :func:`detect_setups`).
    """
    config = config or ParabolicShortConfig()
    idx = df.index
    try:
        entry_pos = idx.get_loc(setup.entry_date)
    except KeyError:
        return None
    if isinstance(entry_pos, slice):
        entry_pos = entry_pos.start

    n = len(df)
    opens = df["open"].to_numpy() if "open" in df.columns else df["close"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()

    entry = setup.entry_price
    r_value = setup.r_value
    mfe = 0.0
    mae = 0.0

    # For an entry executed at the close of the entry bar, stop/target can
    # only be evaluated from the *next* bar onward (no same-bar re-use of a
    # bar's own high/low that already priced the entry fill).
    start_pos = entry_pos + 1
    last_pos = min(entry_pos + config.max_holding_days, n - 1)

    exit_date = idx[min(entry_pos, n - 1)]
    exit_price = entry
    exit_reason: Literal["target", "stop", "time", "open"] = "open"

    for pos in range(start_pos, last_pos + 1):
        day_high = float(highs[pos])
        day_low = float(lows[pos])
        favorable = entry - day_low
        adverse = day_high - entry
        mfe = max(mfe, favorable)
        mae = max(mae, adverse)

        hit_stop = day_high >= setup.stop_price
        hit_target = day_low <= setup.target_price
        if hit_stop and hit_target:
            # Conservative convention: assume the adverse (stop) level was
            # touched first when both are within the same day's range.
            exit_date = idx[pos]
            exit_price = max(float(opens[pos]), setup.stop_price)
            exit_reason = "stop"
            break
        if hit_stop:
            exit_date = idx[pos]
            exit_price = max(float(opens[pos]), setup.stop_price)
            exit_reason = "stop"
            break
        if hit_target:
            exit_date, exit_price, exit_reason = idx[pos], setup.target_price, "target"
            break
    else:
        if last_pos >= start_pos:
            exit_date = idx[last_pos]
            exit_price = float(closes[last_pos])
            exit_reason = "time" if last_pos < n - 1 or (entry_pos + config.max_holding_days) <= n - 1 else "open"
        else:
            # no bars available after entry (entry is the last bar in df)
            exit_date = idx[entry_pos]
            exit_price = entry
            exit_reason = "open"

    raw_pnl = entry - exit_price
    if config.cost_bps > 0:
        cost = (entry + exit_price) * (config.cost_bps / 10_000.0)
        raw_pnl -= cost
    r_multiple = raw_pnl / r_value if r_value else 0.0
    holding_period_days = max(0, idx.get_loc(exit_date) - entry_pos) if exit_date in idx else 0
    if r_multiple > 1e-9:
        outcome: Literal["win", "loss", "breakeven", "open"] = "win"
    elif r_multiple < -1e-9:
        outcome = "loss"
    else:
        outcome = "breakeven"
    if exit_reason == "open":
        outcome = "open"

    return ParabolicTrade(
        setup=setup,
        exit_date=exit_date,
        exit_price=exit_price,
        exit_reason=exit_reason,
        mfe=mfe,
        mae=mae,
        mfe_r=(mfe / r_value if r_value else 0.0),
        mae_r=(mae / r_value if r_value else 0.0),
        r_multiple=r_multiple,
        holding_period_days=holding_period_days,
        outcome=outcome,
    )


def backtest_symbol(
    df: pd.DataFrame,
    config: ParabolicShortConfig | None = None,
    *,
    symbol: str = "UNKNOWN",
) -> list[ParabolicTrade]:
    """Detect setups and simulate each to a trade outcome for one symbol."""
    config = config or ParabolicShortConfig()
    setups = detect_setups(df, config, symbol=symbol)
    trades: list[ParabolicTrade] = []
    for setup in setups:
        trade = simulate_trade(df, setup, config)
        if trade is not None:
            trades.append(trade)
    return trades


def trades_to_dataframe(trades: list[ParabolicTrade]) -> pd.DataFrame:
    """Flatten a list of :class:`ParabolicTrade` into the trade-log schema
    requested by the strategy spec (symbol, dates, prices, MFE/MAE, R, etc.)."""
    if not trades:
        return pd.DataFrame(
            columns=[
                "symbol",
                "run_base_date",
                "run_base_price",
                "parabolic_peak_date",
                "peak_price",
                "pct_gain",
                "red_day_date",
                "red_day_volume",
                "avg_volume_before",
                "entry_date",
                "entry_price",
                "stop_price",
                "target_price",
                "r_value",
                "exit_date",
                "exit_price",
                "exit_reason",
                "mfe",
                "mae",
                "mfe_r",
                "mae_r",
                "r_multiple",
                "holding_period_days",
                "outcome",
            ]
        )
    return pd.DataFrame([t.to_dict() for t in trades])
