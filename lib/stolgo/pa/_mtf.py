# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Multi-timeframe resample and alignment (no look-ahead)."""

from __future__ import annotations

import pandas as pd

from stolgo.data.normalize import normalize_ohlcv


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample OHLCV to a higher timeframe (e.g. ``1D``, ``1h``)."""
    work = normalize_ohlcv(df) if "open" not in df.columns else df
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    return work.resample(rule).agg(agg).dropna()


def align_to_base(higher_tf: pd.Series, base_index: pd.DatetimeIndex) -> pd.Series:
    """Forward-fill higher-TF values onto ``base_index`` (values only after HTF bar closes)."""
    combined = higher_tf.reindex(higher_tf.index.union(base_index)).sort_index()
    aligned = combined.ffill()
    return aligned.reindex(base_index)


def apply_tf(ohlcv: pd.DataFrame, tf: str) -> pd.DataFrame:
    """If ``tf`` set, resample; caller aligns back when needed."""
    return resample_ohlcv(ohlcv, tf)


def level_on_base(
    ohlcv: pd.DataFrame,
    tf: str | None,
    compute_on: pd.DataFrame,
    values: pd.Series,
) -> pd.Series:
    """Compute level on ``compute_on`` and align to ``ohlcv`` index."""
    if tf is None:
        return values.reindex(ohlcv.index)
    return align_to_base(values, ohlcv.index)
