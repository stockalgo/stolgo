"""Build round-trip trade log from fill events (cold path)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stolgo.core.events import FillEvent
from stolgo.core.types import Side


@dataclass
class _Lot:
    side: Side
    entry_ts: pd.Timestamp
    entry_price: float
    qty: float
    entry_commission: float
    risk_per_unit: float | None = None
    tag: str | None = None


def build_trades_from_fills(
    fills: list[FillEvent],
    mark: tuple[int | pd.Timestamp, float] | None = None,
) -> pd.DataFrame:
    """FIFO match fills into round-trip trades (signed position matching)."""
    lots: list[_Lot] = []
    rows: list[dict] = []

    for fe in fills:
        f = fe.fill
        ts = pd.Timestamp(f.ts, unit="ns", tz="UTC")
        remaining = f.qty
        fill_commission_per_unit = f.commission / f.qty if f.qty else 0.0

        # Close existing opposite-side lots FIFO
        while remaining > 1e-12 and lots and lots[0].side != f.side:
            lot = lots[0]
            match_qty = min(remaining, lot.qty)
            entry_comm_part = lot.entry_commission * (match_qty / lot.qty) if lot.qty else 0.0
            exit_comm_part = fill_commission_per_unit * match_qty

            if lot.side == Side.BUY:
                side_str = "LONG"
                gross = (f.price - lot.entry_price) * match_qty
            else:
                side_str = "SHORT"
                gross = (lot.entry_price - f.price) * match_qty

            net = gross - entry_comm_part - exit_comm_part
            notional = lot.entry_price * match_qty
            return_on_notional = net / notional if notional > 0 else 0.0

            if lot.risk_per_unit is not None and lot.risk_per_unit > 0:
                r_multiple = net / (lot.risk_per_unit * match_qty)
            else:
                r_multiple = float("nan")

            rows.append(
                {
                    "entry_ts": lot.entry_ts,
                    "exit_ts": ts,
                    "side": side_str,
                    "entry_price": lot.entry_price,
                    "exit_price": f.price,
                    "qty": match_qty,
                    "gross_pnl": gross,
                    "net_pnl": net,
                    "commission": entry_comm_part + exit_comm_part,
                    "return_on_notional": return_on_notional,
                    "r_multiple": r_multiple,
                    "tag": lot.tag,
                    "exit_reason": f.tag if f.tag is not None else "SIGNAL",
                }
            )

            lot.qty -= match_qty
            lot.entry_commission -= entry_comm_part
            remaining -= match_qty
            if lot.qty <= 1e-12:
                lots.pop(0)

        # Any remaining quantity opens new lots on f.side
        if remaining > 1e-12:
            remaining_comm = fill_commission_per_unit * remaining
            risk_per_unit = getattr(f, "risk_per_unit", None)
            lots.append(
                _Lot(
                    side=f.side,
                    entry_ts=ts,
                    entry_price=f.price,
                    qty=remaining,
                    entry_commission=remaining_comm,
                    risk_per_unit=risk_per_unit,
                    tag=f.tag,
                )
            )

    if mark is not None and lots:
        mark_raw_ts, mark_px = mark
        mark_ts = (
            mark_raw_ts
            if isinstance(mark_raw_ts, pd.Timestamp)
            else pd.Timestamp(mark_raw_ts, unit="ns", tz="UTC")
        )
        total_qty = sum(l.qty for l in lots)
        if total_qty > 1e-12:
            side_str = "LONG" if lots[0].side == Side.BUY else "SHORT"
            entry_px = sum(l.entry_price * l.qty for l in lots) / total_qty
            earliest_ts = min(l.entry_ts for l in lots)
            total_comm = sum(l.entry_commission for l in lots)
            gross = (
                (mark_px - entry_px) * total_qty
                if side_str == "LONG"
                else (entry_px - mark_px) * total_qty
            )
            net = gross - total_comm
            notional = entry_px * total_qty
            return_on_notional = net / notional if notional > 0 else 0.0
            rows.append(
                {
                    "entry_ts": earliest_ts,
                    "exit_ts": mark_ts,
                    "side": side_str,
                    "entry_price": entry_px,
                    "exit_price": mark_px,
                    "qty": total_qty,
                    "gross_pnl": gross,
                    "net_pnl": net,
                    "commission": total_comm,
                    "return_on_notional": return_on_notional,
                    "r_multiple": float("nan"),
                    "tag": "OPEN",
                    "exit_reason": "OPEN",
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "entry_ts",
                "exit_ts",
                "side",
                "entry_price",
                "exit_price",
                "qty",
                "gross_pnl",
                "net_pnl",
                "commission",
                "return_on_notional",
                "r_multiple",
                "tag",
                "exit_reason",
            ]
        )
    return pd.DataFrame(rows)
