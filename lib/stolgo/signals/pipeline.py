# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Cross-sectional factor pipeline (HLD §4.3, §6.3) — v0.2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from stolgo.core.config import RunConfig
from stolgo.data.base import DataSource
from stolgo.data.normalize import normalize_ohlcv
from stolgo.report.result import RunResult


class Factor(ABC):
    @abstractmethod
    def compute(self, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Return panel (date index × symbol columns)."""


@dataclass
class _MomentumFactor(Factor):
    period: int

    def compute(self, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        out: dict[str, pd.Series] = {}
        for sym, df in frames.items():
            close = df["close"]
            mom = close / close.shift(self.period) - 1.0
            out[sym] = mom
        return pd.DataFrame(out)


@dataclass
class _VolatilityFactor(Factor):
    period: int

    def compute(self, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        out: dict[str, pd.Series] = {}
        for sym, df in frames.items():
            ret = df["close"].pct_change()
            out[sym] = ret.rolling(self.period).std()
        return pd.DataFrame(out)


def momentum(period: int) -> Factor:
    return _MomentumFactor(period)


def volatility(period: int) -> Factor:
    return _VolatilityFactor(period)


@dataclass
class Pipeline:
    universe: list[str] | str
    _factors: list[tuple[str, Factor]] = field(default_factory=list)
    _filters: list[pd.DataFrame] = field(default_factory=list)
    _rank: tuple[str, int] | None = None
    _rebalance_rule: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.universe, str):
            self.universe = [self.universe]

    def add(self, factor: Factor, *, name: str) -> Pipeline:
        self._factors.append((name, factor))
        return self

    def filter(self, mask: pd.DataFrame | pd.Series) -> Pipeline:
        if isinstance(mask, pd.Series):
            mask = mask.to_frame("filter")
        self._filters.append(mask)
        return self

    def rank(self, column: str, *, top: int) -> Pipeline:
        self._rank = (column, top)
        return self

    def rebalance(self, rule: str) -> Pipeline:
        self._rebalance_rule = rule
        return self

    def run_frames(self, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Build target weights (date × symbol) from aligned OHLCV frames."""
        normalized = {sym: normalize_ohlcv(df, symbol=sym) for sym, df in frames.items()}
        closes: dict[str, pd.Series] = {}
        for sym, df in normalized.items():
            if "timestamp" in df.columns:
                closes[sym] = df.set_index("timestamp")["close"]
            else:
                closes[sym] = df["close"]
        close_panel = pd.DataFrame(closes).sort_index()

        factor_panels: dict[str, pd.DataFrame] = {}
        for name, factor in self._factors:
            factor_panels[name] = factor.compute(normalized)

        if self._rebalance_rule:
            rebal_dates = close_panel.resample(self._rebalance_rule).last().index
        else:
            rebal_dates = close_panel.index

        rebal_weights: dict[pd.Timestamp, pd.Series] = {}
        for dt in rebal_dates:
            if dt not in close_panel.index:
                continue
            eligible = pd.Series(True, index=close_panel.columns)
            for filt in self._filters:
                panel = filt
                if isinstance(filt, pd.DataFrame) and filt.shape[1] == 1:
                    panel = filt.iloc[:, 0].to_frame("filter")
                panel = panel.reindex(index=close_panel.index, columns=close_panel.columns)
                if dt in panel.index:
                    row = panel.loc[dt]
                    eligible &= row.fillna(False).astype(bool)

            if self._rank is not None:
                col, top_n = self._rank
                scores = factor_panels[col].loc[dt].where(eligible)
                picks = scores.nlargest(top_n).dropna().index.tolist()
            else:
                picks = list(eligible[eligible].index)

            w = pd.Series(0.0, index=close_panel.columns)
            if picks:
                w.loc[picks] = 1.0 / len(picks)
            rebal_weights[dt] = w

        if not rebal_weights:
            return pd.DataFrame(0.0, index=close_panel.index, columns=close_panel.columns)

        weights = pd.DataFrame(rebal_weights).T.sort_index()
        weights = weights.reindex(close_panel.index).ffill().fillna(0.0)
        weights.columns = close_panel.columns
        return weights

    def _equity_from_weights(
        self, close_panel: pd.DataFrame, weights: pd.DataFrame, cash: float
    ) -> pd.Series:
        rets = close_panel.pct_change().fillna(0.0)
        w_lag = weights.shift(1).fillna(0.0)
        port_ret = (w_lag * rets).sum(axis=1)
        equity = cash * (1 + port_ret).cumprod()
        equity.index = pd.DatetimeIndex(equity.index, tz="UTC")
        return equity

    def run(self, data: DataSource, config: RunConfig) -> RunResult:
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        end = datetime(2099, 1, 1, tzinfo=timezone.utc)
        interval = config.interval or "1d"
        frames: dict[str, pd.DataFrame] = {}
        for sym in self.universe:
            frames[sym] = data.history(sym, interval, start, end)

        weights = self.run_frames(frames)
        close_panel = pd.DataFrame(
            {sym: normalize_ohlcv(df, symbol=sym).set_index("timestamp")["close"] for sym, df in frames.items()}
        ).sort_index()
        equity = self._equity_from_weights(close_panel, weights, config.cash)

        return RunResult(
            params=config.model_dump(),
            trades=pd.DataFrame(),
            equity=equity,
            positions=weights,
            signals=weights,
            events=[],
            ohlcv=close_panel,
        )
