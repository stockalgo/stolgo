"""Pure adapters from stolgo artifacts to frontend JSON contracts."""

from __future__ import annotations

import pandas as pd


def _to_secs(ts) -> int:
    return int(pd.Timestamp(ts).timestamp())


def run_summary(manifest: dict) -> dict:
    m = manifest.get("metrics", {})
    p = manifest.get("params", {})
    return {
        "id": manifest["run_id"],
        "strategy": manifest["strategy"],
        "market": p.get("symbol") or "-",
        "timeframe": p.get("interval") or "-",
        "return": m.get("total_return", 0.0),
        "sharpe": m.get("sharpe", 0.0),
        "drawdown": m.get("max_drawdown", 0.0),
        "trades": int(m.get("num_trades", 0)),
        "created_at": manifest.get("created_at"),
    }


def metric_cards(metrics: dict) -> list[dict]:
    order = [
        ("total_return", "Net return", "pct"),
        ("cagr", "CAGR", "pct"),
        ("sharpe", "Sharpe", "num"),
        ("max_drawdown", "Max drawdown", "pct"),
        ("profit_factor", "Profit factor", "num"),
        ("hit_rate", "Win rate", "pct"),
        ("expectancy", "Expectancy", "r"),
        ("num_trades", "Trades", "int"),
    ]
    return [
        {"key": key, "label": label, "value": metrics.get(key, 0.0), "fmt": fmt}
        for key, label, fmt in order
    ]


def series(ohlcv_df, equity_s, drawdown_s) -> dict:
    candles = [
        {
            "time": _to_secs(index),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
        }
        for index, row in ohlcv_df.iterrows()
    ]
    volume = [
        {
            "time": _to_secs(index),
            "value": float(row.volume),
            "color": "rgba(20,154,90,0.18)"
            if row.close >= row.open
            else "rgba(200,63,58,0.16)",
        }
        for index, row in ohlcv_df.iterrows()
    ]
    equity = [{"time": _to_secs(index), "value": float(value)} for index, value in equity_s.items()]
    drawdown = [
        {"time": _to_secs(index), "value": float(value)} for index, value in drawdown_s.items()
    ]
    return {"candles": candles, "volume": volume, "equity": equity, "drawdown": drawdown}


def trades(trades_df) -> list[dict]:
    out = []
    for index, row in trades_df.iterrows():
        pnl = float(row.get("net_pnl", 0.0))
        out.append(
            {
                "id": int(index) + 1,
                "entryTime": _to_secs(row["entry_ts"]),
                "exitTime": _to_secs(row["exit_ts"]),
                "entryPrice": float(row["entry_price"]),
                "exitPrice": float(row["exit_price"]),
                "qty": float(row["qty"]),
                "pnl": pnl,
                "r": round(float(row.get("r_multiple", 0.0)), 2),
                "side": "Long",
                "tag": row.get("tag") or "",
                "pnlClass": "positive" if pnl >= 0 else "negative",
            }
        )
    return out
