"""Risk/reward bracket helpers for strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from stolgo.core.types import OrderType, Side
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
    rr: tuple[int, int] = (1, 2)
    stop: StopKind | float = "candle_low"
    oco_group: str | None = None
    exit: Literal["bracket", "next_open"] = "bracket"
    filled: bool = False

    def on_fill(self, ctx: Context, fe: Any) -> bool:
        if self.filled or self.exit != "bracket":
            return False
        fill = getattr(fe, "fill", fe)
        if fill.side != self.side:
            return False

        self.filled = True
        fill_px = float(fill.price)
        qty = float(fill.qty)
        self.entry_price = fill_px
        self.qty = qty

        if isinstance(self.stop, (int, float)):
            stop_px = float(self.stop)
        elif self.stop == "entry":
            stop_px = fill_px
        else:
            stop_px = self.stop_price

        self.stop_price = stop_px
        self.target_price = _target(fill_px, stop_px, self.rr, self.side)

        exit_side = Side.SELL if self.side == Side.BUY else Side.BUY
        fill_id = getattr(fill, "fill_id", "1")
        oco = self.oco_group or f"oco-bracket-{fill_id}"

        # Submit resting STOP
        ctx.order(
            side=exit_side,
            order_type=OrderType.STOP,
            qty=qty,
            stop_price=self.stop_price,
            oco_group=oco,
            tag=f"{self.tag or 'bracket'}_stop",
            reduce_only=True,
        )
        # Submit resting LIMIT
        ctx.order(
            side=exit_side,
            order_type=OrderType.LIMIT,
            qty=qty,
            limit_price=self.target_price,
            oco_group=oco,
            tag=f"{self.tag or 'bracket'}_target",
            reduce_only=True,
        )
        return True


def _stop_price(ctx: Context, stop: StopKind | float, entry: float, side: Side) -> float:
    if isinstance(stop, (int, float)):
        return float(stop)
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
    stop: StopKind | float = "candle_low",
    size_risk_pct: float = 0.01,
    qty: float | None = None,
    tag: str | None = "long",
    cash: float | None = None,
    exit: Literal["bracket", "next_open"] = "bracket",
    oco_group: str | None = None,
) -> Bracket | None:
    entry = float(ctx.data.close[-1])
    stop_px = _stop_price(ctx, stop, entry, Side.BUY)
    if entry <= stop_px:
        return None
    equity = cash if cash is not None else ctx.equity
    q = _size(entry, stop_px, size_risk_pct, qty, equity)
    if q <= 0:
        return None
    target = _target(entry, stop_px, rr, Side.BUY)
    risk_per_unit = abs(entry - stop_px)
    ctx.buy(qty=q, tag=tag, risk_per_unit=risk_per_unit)
    b = Bracket(
        side=Side.BUY,
        entry_price=entry,
        stop_price=stop_px,
        target_price=target,
        qty=q,
        tag=tag,
        rr=rr,
        stop=stop,
        oco_group=oco_group,
        exit=exit,
    )
    ctx._active_brackets.append(b)
    return b


def short(
    ctx: Context,
    *,
    rr: tuple[int, int] = (1, 2),
    stop: StopKind | float = "candle_high",
    size_risk_pct: float = 0.01,
    qty: float | None = None,
    tag: str | None = "short",
    cash: float | None = None,
    exit: Literal["bracket", "next_open"] = "bracket",
    oco_group: str | None = None,
) -> Bracket | None:
    entry = float(ctx.data.close[-1])
    stop_px = _stop_price(ctx, stop, entry, Side.SELL)
    if entry >= stop_px:
        return None
    equity = cash if cash is not None else ctx.equity
    q = _size(entry, stop_px, size_risk_pct, qty, equity)
    if q <= 0:
        return None
    target = _target(entry, stop_px, rr, Side.SELL)
    risk_per_unit = abs(entry - stop_px)
    ctx.sell(qty=q, tag=tag, risk_per_unit=risk_per_unit)
    b = Bracket(
        side=Side.SELL,
        entry_price=entry,
        stop_price=stop_px,
        target_price=target,
        qty=q,
        tag=tag,
        rr=rr,
        stop=stop,
        oco_group=oco_group,
        exit=exit,
    )
    ctx._active_brackets.append(b)
    return b


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
