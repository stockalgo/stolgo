import numpy as np
import pandas as pd
import pytest

from stolgo.report.trade_schema import SourceMapping, normalize_trades


def test_trade_schema_case1_two_sell_legs():
    # '-C24150(17.1->34.1) -P23950(8.9->4.2)', price=underlying → 2 legs, both SELL, premiums parsed. underlying_entry=24063.5.
    df = pd.DataFrame([
        {
            "entry_ts": "2024-01-01 04:00:00+00:00",
            "exit_ts": "2024-01-01 09:15:00+00:00",
            "entry_price": 24063.5,
            "exit_price": 24100.0,
            "qty": 50.0,
            "gross_pnl": 500.0,
            "net_pnl": 450.0,
            "fees": 50.0,
            "tag": "-C24150(17.1->34.1) -P23950(8.9->4.2)",
        }
    ])
    mapping = SourceMapping(
        price_columns="underlying",
        structure="short_strangle",
        market="NIFTY",
        lot_size=50,
        side="SHORT",
    )
    trades_v2, legs_v2 = normalize_trades(df, mapping)
    assert trades_v2.iloc[0]["underlying_entry"] == 24063.5
    assert "entry_price" not in trades_v2.columns
    assert trades_v2.iloc[0]["legs_label"] == "-C24150 -P23950"

    assert legs_v2 is not None
    assert len(legs_v2) == 2
    assert (legs_v2["action"] == "SELL").all()
    assert legs_v2.iloc[0]["strike"] == 24150
    assert legs_v2.iloc[0]["option_type"] == "CE"
    assert legs_v2.iloc[0]["entry_premium"] == 17.1
    assert legs_v2.iloc[0]["exit_premium"] == 34.1
    assert legs_v2.iloc[1]["strike"] == 23950
    assert legs_v2.iloc[1]["option_type"] == "PE"
    assert legs_v2.iloc[1]["entry_premium"] == 8.9
    assert legs_v2.iloc[1]["exit_premium"] == 4.2


def test_trade_schema_case2_four_legs_iron_condor():
    # '-C20200(16.4->0.4) -P20100(28.1->30.6) +C20400 +P19900' → 4 legs, wings BUY with NaN premiums.
    df = pd.DataFrame([
        {
            "entry_ts": "2024-01-01 04:00:00+00:00",
            "exit_ts": "2024-01-01 09:15:00+00:00",
            "entry_price": 20150.0,
            "exit_price": 20180.0,
            "qty": 50.0,
            "gross_pnl": 500.0,
            "net_pnl": 450.0,
            "fees": 50.0,
            "tag": "-C20200(16.4->0.4) -P20100(28.1->30.6) +C20400 +P19900",
        }
    ])
    mapping = SourceMapping(
        price_columns="underlying",
        structure="iron_condor",
        market="NIFTY",
        lot_size=50,
        side="SHORT",
    )
    trades_v2, legs_v2 = normalize_trades(df, mapping)
    assert legs_v2 is not None
    assert len(legs_v2) == 4
    assert legs_v2.iloc[0]["action"] == "SELL"
    assert legs_v2.iloc[1]["action"] == "SELL"
    assert legs_v2.iloc[2]["action"] == "BUY"
    assert legs_v2.iloc[3]["action"] == "BUY"
    assert np.isnan(legs_v2.iloc[2]["entry_premium"])
    assert np.isnan(legs_v2.iloc[3]["exit_premium"])


def test_trade_schema_case3_validated_row_missing_spot():
    # validated row (tag='MISSING_SPOT', entry_price NaN, has slippage) → exit_reason='DATA_EXIT', data_flag='MISSING_SPOT', r_multiple NaN, underlying_entry NaN.
    df = pd.DataFrame([
        {
            "entry_ts": "2024-01-01 04:00:00+00:00",
            "exit_ts": "2024-01-01 09:15:00+00:00",
            "entry_price": np.nan,
            "exit_price": np.nan,
            "qty": 50.0,
            "gross_pnl": -1000.0,
            "net_pnl": -1050.0,
            "fees": 40.0,
            "slippage": 10.0,
            "tag": "MISSING_SPOT",
        }
    ])
    mapping = SourceMapping(
        price_columns="underlying",
        structure="short_strangle",
        market="NIFTY",
        lot_size=50,
        side="SHORT",
    )
    trades_v2, legs_v2 = normalize_trades(df, mapping)
    assert trades_v2.iloc[0]["exit_reason"] == "DATA_EXIT"
    assert trades_v2.iloc[0]["data_flag"] == "MISSING_SPOT"
    assert np.isnan(trades_v2.iloc[0]["r_multiple"])
    assert np.isnan(trades_v2.iloc[0]["underlying_entry"])
    assert legs_v2 is None


def test_trade_schema_case4_g1_premium():
    # a G1 row (tag='top1-sensex-1dte-strangle', entry_price 391.29, price=premium) → premium_entry=391.29, legs=None.
    df = pd.DataFrame([
        {
            "entry_ts": "2024-01-01 04:00:00+00:00",
            "exit_ts": "2024-01-01 09:15:00+00:00",
            "entry_price": 391.29,
            "exit_price": 100.0,
            "qty": 20.0,
            "gross_pnl": 5825.8,
            "net_pnl": 5700.0,
            "fees": 125.8,
            "tag": "top1-sensex-1dte-strangle",
        }
    ])
    mapping = SourceMapping(
        price_columns="premium",
        structure="short_strangle",
        market="SENSEX",
        lot_size=20,
        side="SHORT",
    )
    trades_v2, legs_v2 = normalize_trades(df, mapping)
    assert trades_v2.iloc[0]["premium_entry"] == 391.29
    assert "entry_price" not in trades_v2.columns
    assert legs_v2 is None


def test_trade_schema_drops_duplicate_tag():
    df = pd.DataFrame([
        {
            "entry_ts": "2024-01-01 04:00:00+00:00",
            "exit_ts": "2024-01-01 09:15:00+00:00",
            "entry_price": 100.0,
            "exit_price": 50.0,
            "qty": 50.0,
            "gross_pnl": 2500.0,
            "net_pnl": 2450.0,
            "fees": 50.0,
            "tag": "my_tag",
        }
    ])
    mapping = SourceMapping(
        price_columns="premium",
        structure="short_strangle",
        market="NIFTY",
        lot_size=50,
        side="SHORT",
    )
    trades_v2, _ = normalize_trades(df, mapping)
    assert "source_tag" in trades_v2.columns
    assert trades_v2.iloc[0]["source_tag"] == "my_tag"
    assert "tag" not in trades_v2.columns


@pytest.mark.parametrize("source", [None, "my_strategy", "-C24150 -P23950"])
def test_unknown_exit_is_not_inferred_from_shared_clock_time(source):
    trades, _ = _normalized_exit(source)
    assert trades["exit_reason"].tolist() == ["UNKNOWN", "UNKNOWN"]


@pytest.mark.parametrize("source,expected", [
    ("LEG_THRESHOLD_CLOSE_ALL", ("STOP", "")),
    ("FIRST_TOUCH_EXIT", ("TOUCH_EXIT", "")),
    ("DEFENSE_CASH", ("ADJUSTMENT", "")),
    ("DEFENSE_A", ("ADJUSTMENT", "")),
    ("MISSING_CANDIDATE", ("DATA_EXIT", "MISSING_CANDIDATE")),
    ("SIGNAL", ("SIGNAL", "")),
    ("long_stop", ("STOP", "")),
    ("short_target", ("TARGET", "")),
])
def test_engine_and_replay_exit_reasons_survive_normalization(source, expected):
    trades, _ = _normalized_exit(source)
    assert trades["exit_reason"].tolist() == [expected[0], expected[0]]
    assert trades["data_flag"].tolist() == [expected[1], expected[1]]


def _normalized_exit(source):
    df = pd.DataFrame({
        "entry_ts": pd.to_datetime(["2024-01-01 04:00Z", "2024-01-02 04:00Z"]),
        "exit_ts": pd.to_datetime(["2024-01-01 09:15Z", "2024-01-02 09:15Z"]),
        "qty": [1.0, 1.0], "gross_pnl": [1.0, 1.0], "net_pnl": [1.0, 1.0],
        "exit_reason": [source, source],
    })
    return normalize_trades(df, SourceMapping("none", "short", "SYN", None, "SHORT"))
