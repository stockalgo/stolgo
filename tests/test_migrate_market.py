import pandas as pd
from stolgo.report.trade_schema import assign_trade_markets_and_lots


def test_migrate_market_qty_20_sensex():
    trades = pd.DataFrame({
        "trade_id": [1, 2],
        "qty": [20.0, 40.0],
    })
    res = assign_trade_markets_and_lots(trades, ["NIFTY", "SENSEX"])
    assert res["market"].tolist() == ["SENSEX", "SENSEX"]
    assert res["lots"].tolist() == [1, 2]


def test_migrate_market_qty_65_nifty():
    trades = pd.DataFrame({
        "trade_id": [1, 2],
        "qty": [65.0, 130.0],
    })
    res = assign_trade_markets_and_lots(trades, ["NIFTY", "SENSEX"])
    assert res["market"].tolist() == ["NIFTY", "NIFTY"]
    assert res["lots"].tolist() == [1, 2]


def test_migrate_market_single_market():
    trades = pd.DataFrame({
        "trade_id": [1],
        "qty": [20.0],
    })
    res = assign_trade_markets_and_lots(trades, ["SENSEX"])
    assert res["market"].tolist() == ["SENSEX"]
    assert res["lots"].tolist() == [1]

    trades_nifty = pd.DataFrame({
        "trade_id": [1],
        "qty": [65.0],
    })
    res_nifty = assign_trade_markets_and_lots(trades_nifty, ["NIFTY"])
    assert res_nifty["market"].tolist() == ["NIFTY"]
    assert res_nifty["lots"].tolist() == [1]
