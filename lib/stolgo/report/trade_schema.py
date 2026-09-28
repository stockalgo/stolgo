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


def normalize_trades(
    df: pd.DataFrame, mapping: SourceMapping
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Return (trades_v2, legs_v2 or None). Never mutates df."""
    if df.empty:
        empty_trades = pd.DataFrame(columns=TRADE_V2_REQUIRED + TRADE_V2_OPTIONAL)
        return empty_trades, None

    res = df.copy()

    # 1. trade_id: keep if present, else range(1, n+1) after sorting by entry_ts
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
        res["trade_id"] = res["trade_id"].astype(np.int64)

    # session_date: from entry_ts in IST YYYY-MM-DD
    ist_entry = res["entry_ts"].dt.tz_convert(IST)
    res["session_date"] = ist_entry.dt.strftime("%Y-%m-%d")

    # 2. fees ← commission (or fees if both exist and are equal)
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

    # 3. slippage: from slippage column if present, else 0.0 if gross - fees == net (+/-0.05), else NaN
    if "slippage" in res.columns:
        res["slippage"] = res["slippage"].astype(float)
    else:
        reconciles = (res["gross_pnl"] - res["fees"] - res["net_pnl"]).abs() <= 0.05
        res["slippage"] = np.where(reconciles, 0.0, np.nan)

    res["net_pnl"] = res["net_pnl"].astype(float)

    # 4. entry_price/exit_price -> underlying_* or premium_* per mapping.price_columns
    has_entry_price = "entry_price" in res.columns
    has_exit_price = "exit_price" in res.columns

    if mapping.price_columns == "underlying":
        if has_entry_price:
            res["underlying_entry"] = res["entry_price"].astype(float)
        if has_exit_price:
            res["underlying_exit"] = res["exit_price"].astype(float)

        # Sanity assert: underlying values > 5,000 for NIFTY/SENSEX
        chk_mkt = (mapping.market or "").upper()
        if not chk_mkt and "market" in res.columns:
            chk_mkt = str(res["market"].iloc[0]).upper()
        if not chk_mkt and "index" in res.columns:
            chk_mkt = str(res["index"].iloc[0]).upper()
        if chk_mkt in ("NIFTY", "SENSEX"):
            if "underlying_entry" in res.columns:
                valid = res["underlying_entry"].dropna()
                if not valid.empty and (valid <= 5000).any():
                    violators = valid[valid <= 5000].tolist()
                    raise ValueError(
                        f"Expected underlying price > 5000 for {chk_mkt}, got {violators[:3]}"
                    )
            if "underlying_exit" in res.columns:
                valid = res["underlying_exit"].dropna()
                if not valid.empty and (valid <= 5000).any():
                    violators = valid[valid <= 5000].tolist()
                    raise ValueError(
                        f"Expected underlying price > 5000 for {chk_mkt}, got {violators[:3]}"
                    )

    elif mapping.price_columns == "premium":
        if has_entry_price:
            res["premium_entry"] = res["entry_price"].astype(float)
        if has_exit_price:
            res["premium_exit"] = res["exit_price"].astype(float)

        # Sanity assert: premium values < 5,000 for NIFTY/SENSEX
        chk_mkt = (mapping.market or "").upper()
        if not chk_mkt and "market" in res.columns:
            chk_mkt = str(res["market"].iloc[0]).upper()
        if not chk_mkt and "index" in res.columns:
            chk_mkt = str(res["index"].iloc[0]).upper()
        if chk_mkt in ("NIFTY", "SENSEX"):
            if "premium_entry" in res.columns:
                valid = res["premium_entry"].dropna()
                if not valid.empty and (valid >= 5000).any():
                    violators = valid[valid >= 5000].tolist()
                    raise ValueError(
                        f"Expected premium price < 5000 for {chk_mkt}, got {violators[:3]}"
                    )
            if "premium_exit" in res.columns:
                valid = res["premium_exit"].dropna()
                if not valid.empty and (valid >= 5000).any():
                    violators = valid[valid >= 5000].tolist()
                    raise ValueError(
                        f"Expected premium price < 5000 for {chk_mkt}, got {violators[:3]}"
                    )

    # Drop entry_price and exit_price
    res = res.drop(columns=["entry_price", "exit_price"], errors="ignore")

    # 5. r_multiple: keep if present, else NaN. Never fill with 0.
    if "r_multiple" in res.columns:
        res["r_multiple"] = res["r_multiple"].astype(float)
    else:
        res["r_multiple"] = np.nan

    # source_tag
    if "tag" in res.columns and "source_tag" not in res.columns:
        res["source_tag"] = res["tag"]
    elif "source_tag" not in res.columns:
        res["source_tag"] = ""

    # 6. exit_reason and data_flag
    # Check if every exit is at the same clock time +/- 1 min
    exit_times = res["exit_ts"].dropna()
    exit_times_same = False
    if len(exit_times) > 0:
        minutes_of_day = exit_times.dt.hour * 60 + exit_times.dt.minute
        exit_times_same = (minutes_of_day.max() - minutes_of_day.min()) <= 1

    exit_reasons = []
    data_flags = []
    has_source_exit_reason = "exit_reason" in res.columns

    for _, row in res.iterrows():
        val = row["exit_reason"] if has_source_exit_reason and pd.notna(row["exit_reason"]) else row.get("source_tag")
        r_reason, r_flag = _map_exit_reason_and_flag(val, exit_times_same)
        exit_reasons.append(r_reason)
        data_flags.append(r_flag)

    res["exit_reason"] = exit_reasons
    res["data_flag"] = data_flags

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

    # 8. lots = qty / lot_size if exact integer
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

    # 7. Legs parsing from source_tag
    legs_list: list[dict[str, Any]] = []
    legs_labels: list[str | None] = []

    for _, row in res.iterrows():
        t_id = row["trade_id"]
        t_qty = row["qty"]
        t_entry_ts = row["entry_ts"]
        t_exit_ts = row["exit_ts"]
        tag_str = str(row.get("source_tag", ""))

        matches = LEG_TAG_RE.findall(tag_str)
        if matches:
            label_tokens = []
            for leg_idx, (sign, opt_char, strike_str, p_entry, p_exit) in enumerate(matches, 1):
                action = "BUY" if sign == "+" else "SELL"
                opt_type = "CE" if opt_char == "C" else "PE"
                strike = int(strike_str)
                label_tokens.append(f"{sign}{opt_char}{strike_str}")
                entry_p = float(p_entry) if p_entry else np.nan
                exit_p = float(p_exit) if p_exit else np.nan
                legs_list.append(
                    {
                        "trade_id": t_id,
                        "leg_id": leg_idx,
                        "option_type": opt_type,
                        "strike": strike,
                        "action": action,
                        "qty": t_qty,
                        "entry_premium": entry_p,
                        "exit_premium": exit_p,
                        "entry_ts": t_entry_ts,
                        "exit_ts": t_exit_ts,
                    }
                )
            legs_labels.append(" ".join(label_tokens))
        else:
            legs_labels.append(None)

    res["legs_label"] = legs_labels

    legs_df: pd.DataFrame | None = None
    if legs_list:
        legs_df = pd.DataFrame(legs_list)

    # 9. Column order: REQUIRED, then OPTIONAL present, then any remaining source columns
    ordered_cols: list[str] = []
    for c in TRADE_V2_REQUIRED:
        if c in res.columns and c not in ordered_cols:
            ordered_cols.append(c)

    for c in TRADE_V2_OPTIONAL:
        if c in res.columns and c not in ordered_cols:
            ordered_cols.append(c)

    for c in res.columns:
        if c not in ordered_cols and c != "commission":
            ordered_cols.append(c)

    res = res[ordered_cols]
    return res, legs_df
