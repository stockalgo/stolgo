"""Smoke tests for the public import surface."""

from __future__ import annotations


def test_root_imports():
    import stolgo as sg

    assert sg.Backtest is not None
    assert sg.Strategy is not None
    assert sg.Context is not None
    assert sg.Bandl is sg.BandlDataSource
    assert callable(sg.load)


def test_from_stolgo_import():
    from stolgo import Backtest, Bandl, Context, Strategy, load

    assert Bandl.__name__ in ("Bandl", "BandlDataSource")
    assert callable(load)


def test_pa_import():
    import stolgo.pa as pa

    assert pa.resistance(20) is not None
    assert callable(pa.consolidation)


def test_trade_import():
    from stolgo import trade

    assert callable(trade.long)
    assert callable(trade.short)


def test_load_csv_fixture(fixture_dir):
    from stolgo import load

    path = fixture_dir / "synthetic_100bars.csv"
    df = load(path, symbol="TEST")
    assert len(df) == 100
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert str(df.attrs.get("symbol")) == "TEST"
