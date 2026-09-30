from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Literal

import numpy as np
import pandas as pd

TRADE_V2_REQUIRED = [
    "trade_id",
    "session_date",
    "entry_ts",
    "exit_ts",
    "side",
    "structure",
    "market",
    "qty",
    "gross_pnl",
    "fees",
    "slippage",
    "net_pnl",
    "exit_reason",
    "data_flag",
]
TRADE_V2_OPTIONAL = [
    "dte",
    "expiry",
    "lots",
    "underlying_entry",
    "underlying_exit",
    "premium_entry",
    "premium_exit",
    "r_multiple",
    "risk_inr",
    "legs_label",
    "source_tag",
]

LEG_TAG_RE = re.compile(r"([+-])([CP])(\d+)(?:\(([\d.]+)->([\d.]+)\))?")

IST = "Asia/Kolkata"


@dataclass(frozen=True)
class SourceMapping:
    price_columns: Literal["underlying", "premium", "none"]  # meaning of entry_price/exit_price
    structure: str
    market: str | None  # None → take from row column "market"/"index"
    lot_size: int | None
    side: Literal["SHORT", "LONG", "from_column"]


def _map_exit_reason_and_flag(
    source_val: Any,
    exit_times_same: bool,
) -> tuple[str, str]:
    if source_val is None or pd.isna(source_val):
        return ("TIME_EXIT" if exit_times_same else "UNKNOWN", "")

    s = str(source_val).strip()
    s_upper = s.upper()
    s_lower = s.lower()

    if s_upper == "END_OF_DATA":
        return ("END_OF_DATA", "")
    if s_upper == "OPEN":
        return ("OPEN", "")
    if s_upper == "MISSING_SPOT":
        return ("DATA_EXIT", "MISSING_SPOT")
    if s_upper == "MISSING_HELD_QUOTE":
        return ("DATA_EXIT", "MISSING_HELD_QUOTE")
    if s_upper == "MISSING_DATA":
        return ("DATA_EXIT", "MISSING_DATA")
    if s_upper == "PORTFOLIO_TARGET" or s_lower.startswith("target"):
        return ("TARGET", "")
    if (
        s_upper == "DAILY_STOP"
        or s_lower.startswith("hard_loss")
        or s_lower.startswith("stop")
    ):
        return ("STOP", "")
    if s_upper == "TIME_EXIT" or s_lower.startswith("max_hold") or s_lower.startswith("eod"):
        return ("TIME_EXIT", "")
    if s_upper == "EXIT_TOUCH" or s_lower.startswith("touch"):
        return ("TOUCH_EXIT", "")
    if s_upper == "CONVERSION" or s_lower.startswith("adjust"):
        return ("ADJUSTMENT", "")

    # Legacy tags that are a run/strategy name or leg strings
    if exit_times_same:
        return ("TIME_EXIT", "")
    return ("UNKNOWN", "")


def _check_range(series: pd.Series, market: str, kind: Literal["underlying", "premium"]) -> None:
    if series.empty or market not in ("NIFTY", "SENSEX"):
        return
    valid = series.dropna()
    if valid.empty:
        return
    if kind == "underlying":
        bad = valid <= 5000
        if bad.any():
            violators = valid[bad].tolist()
            raise ValueError(f"Expected underlying price > 5000 for {market}, got {violators[:3]}")
    elif kind == "premium":
        bad = valid >= 5000
        if bad.any():
            violators = valid[bad].tolist()
            raise ValueError(f"Expected premium price < 5000 for {market}, got {violators[:3]}")


def normalize_trades(
    df: pd.DataFrame, mapping: SourceMapping, *, tz: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Return (trades_v2, legs_v2 or None). Never mutates df."""
    if df.empty:
        empty_trades = pd.DataFrame(columns=TRADE_V2_REQUIRED + TRADE_V2_OPTIONAL)
        return empty_trades, None

    res = df.copy()

    if "entry_ts" in res.columns:
        entry_ts = pd.to_datetime(res["entry_ts"])
        if entry_ts.dt.tz is None:
            entry_ts = entry_ts.dt.tz_localize("UTC")
        res["entry_ts"] = entry_ts

    if "exit_ts" in res.columns:
        exit_ts = pd.to_datetime(res["exit_ts"])
        if exit_ts.dt.tz is None:
            exit_ts = exit_ts.dt.tz_localize("UTC")
        res["exit_ts"] = exit_ts

    if "trade_id" not in res.columns:
        res = res.sort_values("entry_ts").reset_index(drop=True)
        res["trade_id"] = np.arange(1, len(res) + 1, dtype=np.int64)
    else:
        try:
            res["trade_id"] = res["trade_id"].astype(np.int64)
        except (ValueError, TypeError):
            res = res.sort_values("entry_ts").reset_index(drop=True)
            res["trade_id"] = np.arange(1, len(res) + 1, dtype=np.int64)

    # session_date: from entry_ts in target_tz YYYY-MM-DD
    if tz is not None:
        target_tz = tz
    elif mapping.market and any(k in str(mapping.market).upper() for k in ("NIFTY", "SENSEX", "BANKNIFTY")):
        target_tz = IST
    else:
        target_tz = "UTC"

    entry_in_tz = res["entry_ts"].dt.tz_convert(target_tz)
    res["session_date"] = entry_in_tz.dt.strftime("%Y-%m-%d")

    # Fees and commission
    if "fees" in res.columns and "commission" in res.columns:
        # keep fees
        pass
    elif "commission" in res.columns:
        res["fees"] = res["commission"].astype(float)
    elif "fees" not in res.columns:
        res["fees"] = 0.0
    else:
        res["fees"] = res["fees"].astype(float)

    # gross_pnl: ensure float
    if "gross_pnl" in res.columns:
        res["gross_pnl"] = res["gross_pnl"].astype(float)
    elif "net_pnl" in res.columns:
        res["gross_pnl"] = res["net_pnl"].astype(float) + res["fees"]

    # Slippage
    if "slippage" in res.columns:
        res["slippage"] = res["slippage"].astype(float)
    else:
        reconciles = (res["gross_pnl"] - res["fees"] - res["net_pnl"]).abs() <= 0.05
        res["slippage"] = np.where(reconciles, 0.0, np.nan)

    res["net_pnl"] = res["net_pnl"].astype(float)

    # Map prices per mapping.price_columns
    has_entry_price = "entry_price" in res.columns
    has_exit_price = "exit_price" in res.columns

    chk_mkt = (mapping.market or "").upper()
    if not chk_mkt and "market" in res.columns and not res["market"].empty:
        chk_mkt = str(res["market"].iloc[0]).upper()
    if not chk_mkt and "index" in res.columns and not res["index"].empty:
        chk_mkt = str(res["index"].iloc[0]).upper()

    if mapping.price_columns == "underlying":
        if has_entry_price:
            res["underlying_entry"] = res["entry_price"].astype(float)
            _check_range(res["underlying_entry"], chk_mkt, "underlying")
        if has_exit_price:
            res["underlying_exit"] = res["exit_price"].astype(float)
            _check_range(res["underlying_exit"], chk_mkt, "underlying")

    elif mapping.price_columns == "premium":
        if has_entry_price:
            res["premium_entry"] = res["entry_price"].astype(float)
            _check_range(res["premium_entry"], chk_mkt, "premium")
        if has_exit_price:
            res["premium_exit"] = res["exit_price"].astype(float)
            _check_range(res["premium_exit"], chk_mkt, "premium")

    # Drop entry_price and exit_price
    res = res.drop(columns=["entry_price", "exit_price"], errors="ignore")

    # Format r_multiple: keep if present, else NaN. Never fill with 0.
    if "r_multiple" in res.columns:
        res["r_multiple"] = res["r_multiple"].astype(float)
    else:
        res["r_multiple"] = np.nan

    # source_tag
    if "tag" in res.columns and "source_tag" not in res.columns:
        res["source_tag"] = res["tag"]
    elif "source_tag" not in res.columns:
        res["source_tag"] = ""

    # Exit reason and data flag
    # Check if every exit is at the same clock time +/- 1 min
    exit_times = res["exit_ts"].dropna()
    exit_times_same = False
    if len(exit_times) > 0:
        minutes_of_day = exit_times.dt.hour * 60 + exit_times.dt.minute
        exit_times_same = (minutes_of_day.max() - minutes_of_day.min()) <= 1

    if "exit_reason" in res.columns:
        source_val = res["exit_reason"].where(res["exit_reason"].notna(), res["source_tag"])
    else:
        source_val = res["source_tag"]

    mapped = source_val.map(lambda v: _map_exit_reason_and_flag(v, exit_times_same))
    res["exit_reason"] = mapped.str[0]
    res["data_flag"] = mapped.str[1]

    # side
    if mapping.side == "from_column" and "side" in res.columns:
        res["side"] = res["side"].astype(str).str.upper()
    else:
        res["side"] = mapping.side

    # structure
    res["structure"] = mapping.structure

    # market
    if mapping.market is not None:
        res["market"] = mapping.market
    elif "market" in res.columns:
        res["market"] = res["market"].astype(str)
    elif "index" in res.columns:
        res["market"] = res["index"].astype(str)
    else:
        res["market"] = "UNKNOWN"

    # qty
    if "qty" in res.columns:
        res["qty"] = res["qty"].astype(float)

    # Calculate lots from lot_size if exact integer
    if mapping.lot_size and "qty" in res.columns:
        lots_series = []
        for q in res["qty"]:
            if pd.notna(q) and mapping.lot_size > 0:
                divided = q / mapping.lot_size
                if math.isclose(divided, round(divided)):
                    lots_series.append(int(round(divided)))
                else:
                    lots_series.append(pd.NA)
            else:
                lots_series.append(pd.NA)
        res["lots"] = pd.Series(lots_series, dtype="Int64", index=res.index)

    # Parse legs from source_tag
    matches_series = res["source_tag"].astype(str).str.findall(LEG_TAG_RE.pattern)
    res["legs_label"] = matches_series.map(
        lambda ms: " ".join(f"{s}{c}{k}" for s, c, k, _, _ in ms) if ms else None
    )

    legs_df: pd.DataFrame | None = None
    if matches_series.map(len).sum() > 0:
        sub = res[["trade_id", "qty", "entry_ts", "exit_ts"]].copy()
        sub["match"] = matches_series
        sub = sub[sub["match"].map(len) > 0]
        exploded = sub.explode("match").reset_index(drop=True)
        exploded["leg_id"] = (exploded.groupby("trade_id").cumcount() + 1).astype(int)
        m = exploded["match"]
        exploded["option_type"] = m.map(lambda x: "CE" if x[1] == "C" else "PE")
        exploded["strike"] = m.map(lambda x: int(x[2]))
        exploded["action"] = m.map(lambda x: "BUY" if x[0] == "+" else "SELL")
        exploded["entry_premium"] = m.map(lambda x: float(x[3]) if x[3] else np.nan)
        exploded["exit_premium"] = m.map(lambda x: float(x[4]) if x[4] else np.nan)
        legs_df = exploded[
            [
                "trade_id",
                "leg_id",
                "option_type",
                "strike",
                "action",
                "qty",
                "entry_premium",
                "exit_premium",
                "entry_ts",
                "exit_ts",
            ]
        ]

    # Column order: REQUIRED, then OPTIONAL present, then any remaining source columns
    ordered_cols: list[str] = []
    for c in TRADE_V2_REQUIRED:
        if c in res.columns and c not in ordered_cols:
            ordered_cols.append(c)

    for c in TRADE_V2_OPTIONAL:
        if c in res.columns and c not in ordered_cols:
            ordered_cols.append(c)

    # Drop duplicate tag column if source_tag holds the exact same values
    if "tag" in res.columns and "source_tag" in res.columns:
        if (res["tag"].fillna("").astype(str) == res["source_tag"].fillna("").astype(str)).all():
            res = res.drop(columns=["tag"])

    for c in res.columns:
        if c not in ordered_cols and c != "commission":
            ordered_cols.append(c)

    res = res[ordered_cols]
    return res, legs_df


def assign_trade_markets_and_lots(trades_df: pd.DataFrame, markets: list[str]) -> pd.DataFrame:
    """Assign market and lots per trade based on lot sizes and markets list."""
    if trades_df.empty:
        return trades_df

    res = trades_df.copy()
    if len(markets) > 1:
        # Mixed-market run
        assigned_markets = []
        assigned_lots = []
        for q in res.get("qty", []):
            if pd.isna(q):
                assigned_markets.append("UNKNOWN")
                assigned_lots.append(pd.NA)
            elif q % 20 == 0 and q < 65:
                assigned_markets.append("SENSEX")
                assigned_lots.append(int(q // 20))
            elif q % 65 == 0:
                assigned_markets.append("NIFTY")
                assigned_lots.append(int(q // 65))
            else:
                assigned_markets.append("UNKNOWN")
                assigned_lots.append(pd.NA)
        res["market"] = assigned_markets
        res["lots"] = pd.Series(assigned_lots, dtype="Int64", index=res.index)
    elif len(markets) == 1:
        single_mkt = markets[0]
        res["market"] = single_mkt
        lot_sz = 20 if single_mkt == "SENSEX" else (65 if single_mkt == "NIFTY" else None)
        if lot_sz and "qty" in res.columns:
            lots = []
            for q in res["qty"]:
                if pd.notna(q) and lot_sz > 0 and math.isclose(q / lot_sz, round(q / lot_sz)):
                    lots.append(int(round(q / lot_sz)))
                else:
                    lots.append(pd.NA)
            res["lots"] = pd.Series(lots, dtype="Int64", index=res.index)
    return res
