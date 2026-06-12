"""Tests for stolgo.report.result."""

from pathlib import Path

import pandas as pd

from stolgo.report import RunResult


def test_to_dict_and_json(tmp_path):
    equity = pd.Series([100.0, 105.0])
    result = RunResult(
        params={"seed": 42},
        trades=pd.DataFrame(),
        equity=equity,
        positions=pd.DataFrame(),
        signals=pd.DataFrame(),
    )
    d = result.to_dict()
    assert d["num_trades"] == 0
    assert "metrics" in d
    p = tmp_path / "out.json"
    result.to_json(p)
    assert p.exists()
    assert result.summary()
