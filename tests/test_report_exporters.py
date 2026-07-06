"""Tests for report artifact exporters."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from stolgo.report.exporters import export_all, export_parquet, export_sweep
from stolgo.report.result import RunResult


def _result() -> RunResult:
    index = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    equity = pd.Series([100.0, 110.0, 99.0], index=index)
    ohlcv = pd.DataFrame(
        {
            "open": [100.0, 105.0, 108.0],
            "high": [106.0, 111.0, 109.0],
            "low": [99.0, 104.0, 98.0],
            "close": [105.0, 108.0, 100.0],
            "volume": [1000.0, 1200.0, 900.0],
        },
        index=index,
    )
    positions = pd.DataFrame({"qty": [0.0, 1.0, 0.0], "equity": equity}, index=index)
    return RunResult(
        params={},
        trades=pd.DataFrame(),
        equity=equity,
        positions=positions,
        signals=pd.DataFrame(),
        ohlcv=ohlcv,
    )


def test_export_parquet_persists_ohlcv_and_drawdown_by_default(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STOLGO_PERSIST_SERIES", raising=False)

    export_parquet(_result(), tmp_path)

    assert (tmp_path / "ohlcv.parquet").exists()
    assert (tmp_path / "drawdown.parquet").exists()
    drawdown = pd.read_parquet(tmp_path / "drawdown.parquet")["drawdown"]
    assert drawdown.to_list() == pytest.approx([0.0, 0.0, -10.0])


@pytest.mark.parametrize("flag", ["0", "false", "no", "off"])
def test_export_parquet_skips_series_when_disabled(
    tmp_path, monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    monkeypatch.setenv("STOLGO_PERSIST_SERIES", flag)

    export_parquet(_result(), tmp_path)

    assert (tmp_path / "trades.parquet").exists()
    assert (tmp_path / "equity.parquet").exists()
    assert not (tmp_path / "ohlcv.parquet").exists()
    assert not (tmp_path / "drawdown.parquet").exists()


def test_export_all_writes_manifest_last_and_publishes_atomically(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _result()
    out = tmp_path / "runs" / "run-1"

    def checked_export_parquet(exported_result: RunResult, directory) -> None:
        assert exported_result is result
        assert directory == out.with_name("run-1.tmp") / "parquet"
        assert out.with_name("run-1.tmp").exists()
        assert not out.exists()
        export_parquet(exported_result, directory)
        assert not (out.with_name("run-1.tmp") / "manifest.json").exists()

    monkeypatch.setattr("stolgo.report.exporters.export_parquet", checked_export_parquet)

    export_all(result, out, strategy_name="TrendBreakout")

    assert out.exists()
    assert not out.with_name("run-1.tmp").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["kind"] == "run"
    assert manifest["run_id"] == "run-1"
    assert manifest["strategy"] == "TrendBreakout"
    assert manifest["path"] == str(out)
    assert "metrics" in manifest


def test_export_sweep_writes_results_and_manifest_atomically(tmp_path) -> None:
    out = tmp_path / "sweeps" / "sweep-1"
    df = pd.DataFrame({"lookback": [10, 20], "sharpe": [1.2, 1.5]})

    export_sweep(df, out, param_grid={"lookback": [10, 20]}, strategy_name="Momentum")

    assert (out / "results.parquet").exists()
    assert not out.with_name("sweep-1.tmp").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["kind"] == "sweep"
    assert manifest["run_id"] == "sweep-1"
    assert manifest["strategy"] == "Momentum"
    assert manifest["param_grid"] == {"lookback": [10, 20]}


def test_exports_upsert_parent_index(tmp_path) -> None:
    run_out = tmp_path / "runs" / "run-1"
    sweep_out = tmp_path / "runs" / "sweep-1"

    export_all(_result(), run_out, strategy_name="TrendBreakout")
    export_sweep(
        pd.DataFrame({"period": [10], "sharpe": [1.2]}),
        sweep_out,
        param_grid={"period": [10]},
        strategy_name="SmaTrend",
    )

    import duckdb

    con = duckdb.connect(str(tmp_path / "runs" / "_index.duckdb"), read_only=True)
    try:
        counts = dict(con.execute("SELECT kind, count(*) FROM runs_index GROUP BY kind").fetchall())
    finally:
        con.close()
    assert counts == {"run": 1, "sweep": 1}
