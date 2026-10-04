from stolgo.report.quality import (
    DATA_ISSUE_THRESHOLD,
    MIN_SESSIONS_OK,
    MIN_TRADES_OK,
    run_status,
)


def test_quality_empty():
    status, reasons = run_status(
        name="Test",
        metrics={"num_trades": 0},
        diagnostics={"data_quality": {"trades_total": 0, "trades_with_missing_data": 0}},
        sessions=300,
    )
    assert status == "empty"
    assert "0 trades" in reasons


def test_quality_superseded():
    status, reasons = run_status(
        name="INVALID Test Run",
        metrics={"num_trades": 150},
        diagnostics={"data_quality": {"trades_total": 150, "trades_with_missing_data": 0}},
        sessions=300,
    )
    assert status == "superseded"
    assert "marked superseded" in reasons


def test_quality_data_issues():
    # > 5% missing data
    status, reasons = run_status(
        name="Test Data Issues",
        metrics={"num_trades": 100},
        diagnostics={"data_quality": {"trades_total": 100, "trades_with_missing_data": 10}},
        sessions=300,
    )
    assert status == "data_issues"
    assert "10 of 100 trades exited on missing data" in reasons


def test_quality_low_sample():
    # < 100 trades
    status, reasons = run_status(
        name="Test Low Sample",
        metrics={"num_trades": 50},
        diagnostics={"data_quality": {"trades_total": 50, "trades_with_missing_data": 0}},
        sessions=300,
    )
    assert status == "low_sample"
    assert "50 trades < 100" in reasons


def test_quality_short_window():
    # < 252 sessions
    status, reasons = run_status(
        name="Test Short Window",
        metrics={"num_trades": 150},
        diagnostics={"data_quality": {"trades_total": 150, "trades_with_missing_data": 0}},
        sessions=200,
    )
    assert status == "short_window"
    assert "200 sessions < 252" in reasons


def test_quality_ok():
    status, reasons = run_status(
        name="Test OK",
        metrics={"num_trades": 150},
        diagnostics={"data_quality": {"trades_total": 150, "trades_with_missing_data": 0}},
        sessions=300,
    )
    assert status == "ok"
    assert reasons == []


def test_quality_pnl_unreconciled():
    status, reasons = run_status(
        name="Test PnL Unreconciled",
        metrics={"num_trades": 150},
        diagnostics={
            "data_quality": {
                "trades_total": 150,
                "trades_with_missing_data": 0,
                "pnl_reconciles": False,
                "pnl_unreconciled_inr": -17086.0,
            }
        },
        sessions=300,
    )
    assert status == "data_issues"
    assert "net P&L differs from gross − fees by ₹17,086" in reasons

