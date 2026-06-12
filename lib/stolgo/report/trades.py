# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Build round-trip trade log from fill events (cold path)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stolgo.core.events import FillEvent
from stolgo.core.types import Side


@dataclass
class _Lot:
    entry_ts: pd.Timestamp
    entry_price: float
    qty: float
    entry_commission: float


def build_trades_from_fills(fills: list[FillEvent]) -> pd.DataFrame:
    """FIFO match sells to buys (long-only v0.1)."""
    lots: list[_Lot] = []
    rows: list[dict] = []

    for fe in fills:
        f = fe.fill
        ts = pd.Timestamp(f.ts, unit="ns", tz="UTC")
        if f.side == Side.BUY:
            lots.append(
                _Lot(
                    entry_ts=ts,
                    entry_price=f.price,
                    qty=f.qty,
                    entry_commission=f.commission,
                )
            )
            continue

        remaining = f.qty
        exit_commission = f.commission
        exit_commission_per_unit = exit_commission / f.qty if f.qty else 0.0

        while remaining > 1e-12 and lots:
            lot = lots[0]
            match_qty = min(remaining, lot.qty)
            entry_comm_part = lot.entry_commission * (match_qty / lot.qty) if lot.qty else 0.0
            exit_comm_part = exit_commission_per_unit * match_qty
            gross = (f.price - lot.entry_price) * match_qty
            net = gross - entry_comm_part - exit_comm_part
            risk = lot.entry_price * match_qty
            r_multiple = net / risk if risk > 0 else 0.0

            rows.append(
                {
                    "entry_ts": lot.entry_ts,
                    "exit_ts": ts,
                    "entry_price": lot.entry_price,
                    "exit_price": f.price,
                    "qty": match_qty,
                    "gross_pnl": gross,
                    "net_pnl": net,
                    "commission": entry_comm_part + exit_comm_part,
                    "r_multiple": r_multiple,
                    "tag": f.order_id,
                }
            )

            lot.qty -= match_qty
            lot.entry_commission -= entry_comm_part
            remaining -= match_qty
            if lot.qty <= 1e-12:
                lots.pop(0)

    if not rows:
        return pd.DataFrame(
            columns=[
                "entry_ts",
                "exit_ts",
                "entry_price",
                "exit_price",
                "qty",
                "gross_pnl",
                "net_pnl",
                "commission",
                "r_multiple",
                "tag",
            ]
        )
    return pd.DataFrame(rows)
