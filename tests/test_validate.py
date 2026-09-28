import datetime as dt
import pandas as pd
import pytest

from stolgo.report.validate import (
    RunValidationError,
    assert_utc,
    fix_ist_labelled_utc,
    looks_like_ist_labelled_utc,
    validate_run_frames,
)


def test_looks_like_ist_labelled_utc_and_fix():
    # Synthetic frame with 09:21Z and 14:30Z
    df = pd.DataFrame({
        "entry_ts": [pd.Timestamp("2024-01-01 09:21:00+00:00")],
        "exit_ts": [pd.Timestamp("2024-01-01 14:30:00+00:00")],
    })
    assert looks_like_ist_labelled_utc(df, exchange="NSE") is True

    fixed_entry = fix_ist_labelled_utc(df["entry_ts"])
    fixed_exit = fix_ist_labelled_utc(df["exit_ts"])
    assert fixed_entry.iloc[0] == pd.Timestamp("2024-01-01 03:51:00+00:00")
    assert fixed_exit.iloc[0] == pd.Timestamp("2024-01-01 09:00:00+00:00")

    fixed_df = pd.DataFrame({"entry_ts": fixed_entry, "exit_ts": fixed_exit})
    assert looks_like_ist_labelled_utc(fixed_df, exchange="NSE") is False


def test_correct_utc_frame_returns_false():
    # Correct 04:00Z / 09:15Z frame
    df = pd.DataFrame({
        "entry_ts": [pd.Timestamp("2024-01-01 04:00:00+00:00")],
        "exit_ts": [pd.Timestamp("2024-01-01 09:15:00+00:00")],
    })
    assert looks_like_ist_labelled_utc(df, exchange="NSE") is False


def test_assert_utc():
    valid = pd.Series([pd.Timestamp("2024-01-01 04:00:00+00:00")])
    assert_utc(valid, "entry_ts")

    invalid = pd.Series([pd.Timestamp("2024-01-01 04:00:00")])
    with pytest.raises(RunValidationError):
        assert_utc(invalid, "entry_ts")


def test_validate_run_frames_ok():
    trades = pd.DataFrame({
        "entry_ts": [pd.Timestamp("2024-01-01 04:00:00+00:00")],
        "exit_ts": [pd.Timestamp("2024-01-01 09:00:00+00:00")],
        "gross_pnl": [120.0],
        "fees": [10.0],
        "slippage": [5.0],
        "net_pnl": [105.0],
    })
    daily = pd.DataFrame({
        "session": ["2024-01-01"],
        "pnl": [105.0],
    })
    problems = validate_run_frames(trades, daily)
    assert problems == []


def test_validate_run_frames_detects_problems():
    trades = pd.DataFrame({
        "entry_ts": [pd.Timestamp("2024-01-01 09:00:00+00:00")],
        "exit_ts": [pd.Timestamp("2024-01-01 04:00:00+00:00")],  # exit before entry
        "gross_pnl": [120.0],
        "fees": [10.0],
        "slippage": [5.0],
        "net_pnl": [50.0],  # wrong net_pnl
    })
    daily = pd.DataFrame({
        "session": ["2024-01-01"],
        "pnl": [100.0],  # mismatch with net_pnl
    })
    problems = validate_run_frames(trades, daily)
    assert len(problems) >= 2
