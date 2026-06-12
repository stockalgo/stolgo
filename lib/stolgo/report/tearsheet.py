# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Plotly tearsheet builder (HLD §8.3)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class Report:
    def __init__(
        self,
        equity: pd.Series,
        trades: pd.DataFrame,
        *,
        ohlcv: pd.DataFrame | None = None,
        metrics: dict[str, float] | None = None,
    ) -> None:
        self._equity = equity
        self._trades = trades
        self._ohlcv = ohlcv
        self._metrics = metrics or {}

    def to_html(self, path: Path) -> None:
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.45, 0.25, 0.3],
            vertical_spacing=0.06,
            subplot_titles=("Price & trades", "Equity", "Drawdown"),
        )

        if self._ohlcv is not None and not self._ohlcv.empty:
            fig.add_trace(
                go.Candlestick(
                    x=self._ohlcv.index,
                    open=self._ohlcv["open"],
                    high=self._ohlcv["high"],
                    low=self._ohlcv["low"],
                    close=self._ohlcv["close"],
                    name="price",
                ),
                row=1,
                col=1,
            )
        else:
            fig.add_trace(
                go.Scatter(x=self._equity.index, y=self._equity.values, name="equity_proxy"),
                row=1,
                col=1,
            )

        if not self._trades.empty:
            entries = self._trades
            fig.add_trace(
                go.Scatter(
                    x=entries["entry_ts"],
                    y=entries["entry_price"],
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=10, color="green"),
                    name="entry",
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=entries["exit_ts"],
                    y=entries["exit_price"],
                    mode="markers",
                    marker=dict(symbol="x", size=10, color="red"),
                    name="exit",
                ),
                row=1,
                col=1,
            )

        fig.add_trace(
            go.Scatter(x=self._equity.index, y=self._equity.values, name="equity", line=dict(color="royalblue")),
            row=2,
            col=1,
        )

        peak = self._equity.cummax()
        dd = (self._equity - peak) / peak
        fig.add_trace(
            go.Scatter(x=dd.index, y=dd.values, name="drawdown", fill="tozeroy", line=dict(color="firebrick")),
            row=3,
            col=1,
        )

        title = "stolgo backtest tearsheet"
        if self._metrics:
            title += (
                f" | return={self._metrics.get('total_return', 0):.2%}"
                f" sharpe={self._metrics.get('sharpe', 0):.2f}"
                f" max_dd={self._metrics.get('max_drawdown', 0):.2%}"
            )
        fig.update_layout(title=title, xaxis_rangeslider_visible=False)
        path.write_text(fig.to_html(include_plotlyjs="cdn"))

    def show(self) -> None:
        tmp = Path("stolgo_tearsheet.html")
        self.to_html(tmp)
        import webbrowser

        webbrowser.open(tmp.resolve().as_uri())

    def to_html_string(self) -> str:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            path = Path(tmp.name)
        self.to_html(path)
        html = path.read_text()
        path.unlink(missing_ok=True)
        return html
