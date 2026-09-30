# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

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


def build_trades_from_fills(fills: list[FillEvent]) -> pd.DataFrame:
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
                    "tag": f.tag or f.order_id,
                    "exit_reason": f.tag if f.tag else "UNKNOWN",
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
                )
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
