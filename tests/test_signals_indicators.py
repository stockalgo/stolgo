import numpy as np
import pytest

from stolgo.signals import rsi, sma


def test_sma_constant():
    close = np.ones(20)
    out = sma(close, 5)
    assert out[4] == pytest.approx(1.0)


def test_rsi_bounds():
    close = np.linspace(100, 110, 30)
    out = rsi(close, 14)
    valid = out[~np.isnan(out)]
    assert valid.max() <= 100
