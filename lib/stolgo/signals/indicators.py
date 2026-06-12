# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Vectorized indicators (HLD §4.3)."""

from __future__ import annotations

import numpy as np


def sma(close: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(close, np.nan, dtype=np.float64)
    if period <= 0 or len(close) < period:
        return out
    kernel = np.ones(period) / period
    out[period - 1 :] = np.convolve(close, kernel, mode="valid")
    return out


def ema(close: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(close, np.nan, dtype=np.float64)
    if period <= 0 or len(close) == 0:
        return out
    alpha = 2.0 / (period + 1)
    out[0] = close[0]
    for i in range(1, len(close)):
        out[i] = alpha * close[i] + (1 - alpha) * out[i - 1]
    return out


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    return sma(tr, period)


def donchian(high: np.ndarray, low: np.ndarray, period: int) -> tuple[np.ndarray, np.ndarray]:
    upper = np.full_like(high, np.nan)
    lower = np.full_like(low, np.nan)
    for i in range(period - 1, len(high)):
        upper[i] = np.max(high[i - period + 1 : i + 1])
        lower[i] = np.min(low[i - period + 1 : i + 1])
    return upper, lower


def rsi(close: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < period + 1:
        return out
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])
    for i in range(period, len(delta)):
        avg_gain = (avg_gain * (period - 1) + gain[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else np.inf
        out[i + 1] = 100 - (100 / (1 + rs))
    return out
