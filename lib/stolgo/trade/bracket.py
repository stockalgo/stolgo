# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Risk/reward bracket helpers for strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from stolgo.core.types import Side
from stolgo.strategy.context import Context

StopKind = Literal["candle_low", "candle_high", "entry"]


@dataclass
class Bracket:
    side: Side
    entry_price: float
    stop_price: float
    target_price: float
    qty: float
    tag: str | None = None


def _stop_price(ctx: Context, stop: StopKind, entry: float, side: Side) -> float:
    low = float(ctx.data.low[-1])
    high = float(ctx.data.high[-1])
    if stop == "candle_low":
        return low
    if stop == "candle_high":
        return high
    return entry


def _target(entry: float, stop: float, rr: tuple[int, int], side: Side) -> float:
    risk = abs(entry - stop)
    if risk <= 0:
        return entry
    reward = risk * (rr[1] / rr[0])
    if side == Side.BUY:
        return entry + reward
    return entry - reward


def _size(
    entry: float,
    stop: float,
    size_risk_pct: float,
    qty: float | None,
    cash: float,
) -> float:
    if qty is not None:
        return qty
    risk_per_unit = abs(entry - stop)
    if risk_per_unit <= 0:
        return 0.0
    dollar_risk = cash * size_risk_pct
    return dollar_risk / risk_per_unit


def long(
    ctx: Context,
    *,
    rr: tuple[int, int] = (1, 2),
    stop: StopKind = "candle_low",
    size_risk_pct: float = 0.01,
    qty: float | None = None,
    tag: str | None = "long",
    cash: float = 100_000.0,
) -> Bracket | None:
    entry = float(ctx.data.close[-1])
    stop_px = _stop_price(ctx, stop, entry, Side.BUY)
    if entry <= stop_px:
        return None
    q = _size(entry, stop_px, size_risk_pct, qty, cash)
    if q <= 0:
        return None
    target = _target(entry, stop_px, rr, Side.BUY)
    ctx.buy(qty=q, tag=tag)
    return Bracket(Side.BUY, entry, stop_px, target, q, tag)


def short(
    ctx: Context,
    *,
    rr: tuple[int, int] = (1, 2),
    stop: StopKind = "candle_high",
    size_risk_pct: float = 0.01,
    qty: float | None = None,
    tag: str | None = "short",
    cash: float = 100_000.0,
) -> Bracket | None:
    entry = float(ctx.data.close[-1])
    stop_px = _stop_price(ctx, stop, entry, Side.SELL)
    if entry >= stop_px:
        return None
    q = _size(entry, stop_px, size_risk_pct, qty, cash)
    if q <= 0:
        return None
    target = _target(entry, stop_px, rr, Side.SELL)
    ctx.sell(qty=q, tag=tag)
    return Bracket(Side.SELL, entry, stop_px, target, q, tag)


def close(ctx: Context, *, tag: str | None = None) -> None:
    ctx.close(tag=tag)


def bracket_hit(ctx: Context, bracket: Bracket | None) -> str | None:
    """Return ``stop``, ``target``, or None if bracket not hit on this bar."""
    if bracket is None:
        return None
    low = float(ctx.data.low[-1])
    high = float(ctx.data.high[-1])
    if bracket.side == Side.BUY:
        if low <= bracket.stop_price:
            return "stop"
        if high >= bracket.target_price:
            return "target"
    else:
        if high >= bracket.stop_price:
            return "stop"
        if low <= bracket.target_price:
            return "target"
    return None
