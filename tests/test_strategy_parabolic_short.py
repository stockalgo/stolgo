"""Tests for stolgo.strategy.builtins.parabolic_short (deterministic, no network)."""

from __future__ import annotations

import pandas as pd
import pytest
from dataclasses import replace

from stolgo.strategy.builtins.parabolic_short import (
    ParabolicShortConfig,
    backtest_symbol,
    detect_setups,
    simulate_trade,
    trades_to_dataframe,
)

# columns: open, high, low, close, volume
_BASE_ROWS = [
    (10.0, 10.5, 9.8, 10.0, 1000),
    (10.0, 10.5, 9.9, 10.1, 1000),
    (10.1, 10.6, 10.0, 10.2, 1000),
    (10.2, 10.7, 10.1, 10.3, 1000),
    (10.3, 10.8, 10.2, 10.4, 1000),
]

_RALLY_ROWS = [
    (10.4, 13.0, 10.3, 12.5, 1500),
    (12.5, 16.0, 12.4, 15.5, 1800),
    (15.5, 20.0, 15.4, 19.5, 2200),
    (19.5, 26.0, 19.4, 25.5, 2800),
    (25.5, 33.0, 25.4, 32.0, 3500),  # peak day (idx 9)
]

_RED_DAY = (32.0, 33.5, 27.0, 28.0, 6000)  # first red day (idx 10), volume spike


def _build_df(tail_rows: list[tuple[float, float, float, float, float]]) -> pd.DataFrame:
    rows = _BASE_ROWS + _RALLY_ROWS + tail_rows
    index = pd.date_range("2026-01-01", periods=len(rows), freq="D", tz="UTC")
    return pd.DataFrame(
        rows, columns=["open", "high", "low", "close", "volume"], index=index
    )


@pytest.fixture
def config() -> ParabolicShortConfig:
    return ParabolicShortConfig(
        lookback_days=5,
        min_gain_pct=2.0,
        volume_avg_window=10,
        volume_multiplier=1.5,
        r_multiple_target=4.0,
        max_holding_days=30,
    )


def test_detect_setups_finds_parabolic_run_and_red_day(config) -> None:
    df = _build_df([_RED_DAY])
    setups = detect_setups(df, config, symbol="TESTUSDT")
    assert len(setups) == 1
    s = setups[0]
    assert s.symbol == "TESTUSDT"
    assert s.peak_price == pytest.approx(32.0)
    assert s.pct_gain == pytest.approx(32.0 / 10.2 - 1.0, rel=1e-6)
    assert s.pct_gain >= 2.0  # 200%+ move
    assert s.red_day_date == df.index[10]
    assert s.entry_price == pytest.approx(28.0)  # entry_mode="close" default
    assert s.stop_price == pytest.approx(33.5)  # high of first red day
    assert s.r_value == pytest.approx(5.5)
    assert s.target_price == pytest.approx(28.0 - 4.0 * 5.5)


def test_simulate_trade_hits_target_computes_mfe_mae_and_r(config) -> None:
    tail = [
        _RED_DAY,
        (27.0, 29.0, 24.0, 25.0, 4000),
        (25.0, 26.0, 20.0, 21.0, 4000),
        (21.0, 22.0, 15.0, 16.0, 4000),
        (16.0, 17.0, 10.0, 11.0, 4000),
        (11.0, 12.0, 5.0, 6.0, 4000),  # low=5 <= target(6.0) -> target hit here
    ]
    df = _build_df(tail)
    setups = detect_setups(df, config, symbol="TESTUSDT")
    assert len(setups) == 1
    trade = simulate_trade(df, setups[0], config)
    assert trade is not None
    assert trade.exit_reason == "target"
    assert trade.exit_price == pytest.approx(setups[0].target_price)
    assert trade.r_multiple == pytest.approx(4.0, abs=1e-6)
    assert trade.outcome == "win"
    assert trade.holding_period_days == 5
    # mfe: best excursion is on the final day (entry=28.0, low=5.0) -> 23.0
    assert trade.mfe == pytest.approx(23.0)
    # mae: worst adverse excursion is day 1 after entry (high=29.0) -> 1.0
    assert trade.mae == pytest.approx(1.0)


def test_simulate_trade_hits_stop_is_a_loss(config) -> None:
    tail = [
        _RED_DAY,
        (28.0, 34.0, 27.0, 27.5, 4000),  # high=34 >= stop(33.5) -> stop hit
    ]
    df = _build_df(tail)
    setups = detect_setups(df, config, symbol="TESTUSDT")
    assert len(setups) == 1
    trade = simulate_trade(df, setups[0], config)
    assert trade is not None
    assert trade.exit_reason == "stop"
    assert trade.r_multiple == pytest.approx(-1.0, abs=1e-6)
    assert trade.outcome == "loss"
    assert trade.holding_period_days == 1


def test_backtest_symbol_end_to_end_and_trade_log_schema(config) -> None:
    tail = [
        _RED_DAY,
        (27.0, 29.0, 24.0, 25.0, 4000),
        (25.0, 26.0, 20.0, 21.0, 4000),
        (21.0, 22.0, 15.0, 16.0, 4000),
        (16.0, 17.0, 10.0, 11.0, 4000),
        (11.0, 12.0, 5.0, 6.0, 4000),
    ]
    df = _build_df(tail)
    trades = backtest_symbol(df, config, symbol="TESTUSDT")
    assert len(trades) == 1
    log = trades_to_dataframe(trades)
    for col in (
        "symbol",
        "parabolic_peak_date",
        "pct_gain",
        "red_day_date",
        "entry_price",
        "stop_price",
        "target_price",
        "mfe",
        "mae",
        "outcome",
        "r_multiple",
        "holding_period_days",
    ):
        assert col in log.columns
    assert log.loc[0, "symbol"] == "TESTUSDT"
    assert log.loc[0, "outcome"] == "win"


def test_no_setup_when_gain_below_threshold(config) -> None:
    # A mild ~20% rally should never trigger a 200% screen.
    tail_rows = [
        (10.4, 10.9, 10.3, 10.6, 1200),
        (10.6, 11.1, 10.5, 10.8, 1200),
        (10.8, 11.3, 10.7, 11.0, 1200),
        (11.0, 11.6, 10.9, 11.3, 1200),
        (11.3, 11.9, 11.2, 11.6, 1200),
    ]
    rows = _BASE_ROWS + tail_rows
    index = pd.date_range("2026-01-01", periods=len(rows), freq="D", tz="UTC")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=index)
    setups = detect_setups(df, config, symbol="TESTUSDT")
    assert setups == []


def test_low_volume_red_day_is_rejected(config) -> None:
    low_volume_red_day = (32.0, 33.5, 27.0, 28.0, 500)  # below 1.5x avg volume
    df = _build_df([low_volume_red_day])
    setups = detect_setups(df, config, symbol="TESTUSDT")
    assert setups == []


def test_config_validates_lookback_days_range() -> None:
    with pytest.raises(ValueError):
        ParabolicShortConfig(lookback_days=1)
    with pytest.raises(ValueError):
        ParabolicShortConfig(lookback_days=20)


def test_next_open_entry_can_stop_on_its_entry_day(config) -> None:
    cfg = replace(config, entry_mode="next_open")
    df = _build_df([_RED_DAY, (28.0, 34.0, 27.0, 29.0, 4000)])
    setup = detect_setups(df, cfg)[0]
    trade = simulate_trade(df, setup, cfg)
    assert trade.exit_reason == "stop"
    assert trade.exit_date == setup.entry_date
    assert trade.exit_price == 33.5


def test_target_gap_wins_over_later_stop(config) -> None:
    df = _build_df([_RED_DAY, (5.0, 35.0, 4.0, 28.0, 4000)])
    setup = detect_setups(df, config)[0]
    trade = simulate_trade(df, setup, config)
    assert trade.exit_reason == "target"
    assert trade.exit_price == 5.0


def test_target_gap_gets_open_price_improvement(config) -> None:
    df = _build_df([_RED_DAY, (5.0, 8.0, 4.0, 7.0, 4000)])
    setup = detect_setups(df, config)[0]
    trade = simulate_trade(df, setup, config)
    assert trade.exit_reason == "target"
    assert trade.exit_price == 5.0
