# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Canonical backtest result artifact (HLD §8.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from stolgo.report.metrics import compute_metrics
from stolgo.report.tearsheet import Report


@dataclass
class RunResult:
    params: dict[str, Any]
    trades: pd.DataFrame
    equity: pd.Series
    positions: pd.DataFrame
    signals: pd.DataFrame
    events: list[Any] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    report: Report | None = None
    ohlcv: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        position_qty = None
        if not self.positions.empty and "qty" in self.positions.columns:
            position_qty = self.positions["qty"]
        if not self.metrics:
            self.metrics = compute_metrics(self.equity, self.trades, position_qty=position_qty)
        if self.report is None:
            self.report = Report(
                self.equity,
                self.trades,
                ohlcv=self.ohlcv,
                metrics=self.metrics,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params,
            "metrics": self.metrics,
            "num_trades": int(len(self.trades)),
            "final_equity": self.metrics.get("final_equity", float(self.equity.iloc[-1]) if len(self.equity) else 0.0),
        }

    def to_json(self, path: Path | str) -> None:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    def summary(self) -> str:
        m = self.metrics
        lines = [
            f"total_return={m.get('total_return', 0):.4f}",
            f"cagr={m.get('cagr', 0):.4f}",
            f"sharpe={m.get('sharpe', 0):.4f}",
            f"sortino={m.get('sortino', 0):.4f}",
            f"max_drawdown={m.get('max_drawdown', 0):.4f}",
            f"num_trades={int(m.get('num_trades', 0))}",
            f"hit_rate={m.get('hit_rate', 0):.4f}",
            f"expectancy={m.get('expectancy', 0):.4f}",
            f"profit_factor={m.get('profit_factor', 0):.4f}",
        ]
        return "\n".join(lines)
