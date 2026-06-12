"""Tests for stolgo.core.config."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from stolgo.core.config import RunConfig


def test_defaults() -> None:
    cfg = RunConfig()
    assert cfg.mode == "backtest"
    assert cfg.seed == 42
    assert cfg.cash == 100_000.0
    assert cfg.fill_on == "next_open"
    assert cfg.fast is False


def test_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        RunConfig(unknown=True)  # type: ignore[call-arg]


def test_params_hash_stable() -> None:
    a = RunConfig(seed=1)
    b = RunConfig(seed=1)
    assert a.params_hash() == b.params_hash()


def test_frozen() -> None:
    cfg = RunConfig()
    with pytest.raises(ValidationError):
        cfg.seed = 99  # type: ignore[misc]
