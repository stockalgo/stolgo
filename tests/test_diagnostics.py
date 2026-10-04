import pandas as pd

from stolgo.report.diagnostics import build_diagnostics


def test_build_diagnostics():
    trades = pd.DataFrame({
        "trade_id": [1, 2, 3],
        "session_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "net_pnl": [100.0, -50.0, 200.0],
        "exit_reason": ["TIME_EXIT", "STOP", "TIME_EXIT"],
        "data_flag": ["", "", "MISSING_SPOT"],
    })
    daily = pd.DataFrame({
        "session": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "pnl": [100.0, -50.0, 200.0],
    })
    capital = 10000.0
    diag = build_diagnostics(trades, daily, capital)

    assert diag["exit_reasons"] == {"TIME_EXIT": 2, "STOP": 1}
    assert diag["data_quality"]["trades_total"] == 3
    assert diag["data_quality"]["trades_with_missing_data"] == 1
    assert diag["data_quality"]["missing_reasons"] == {"MISSING_SPOT": 1}
    assert diag["stability"]["early"]["trades"] == 2
    assert diag["stability"]["recent"]["trades"] == 1
    assert diag["monthly"]["months"] == 1
    assert diag["monthly"]["profitable_months"] == 1
    assert diag["extremes"]["best_trade"] == 200.0
    assert diag["extremes"]["worst_trade"] == -50.0
