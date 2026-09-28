import json
import math
from pathlib import Path

import pandas as pd
import pytest

from stolgo.report.robustness import robustness

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_robustness_benchmark():
    trades_path = FIXTURES_DIR / "nifty_0dte_benchmark_trades.parquet"
    trades = pd.read_parquet(trades_path)

    # Must pass in trade_id order
    net_pnl = trades["net_pnl"].values

    res = robustness(net_pnl, resamples=4000, seed=7)

    expected_path = Path(__file__).parent.parent / "docs/plans/fixtures/expected_after_migration.json"
    data = json.loads(expected_path.read_text())
    expected = data["runs"]["nifty-0dte-strangle-benchmark"]["expected_robustness"]

    # Deterministic fields
    assert math.isclose(res["net_without_top5"], expected["net_without_top5"], abs_tol=1e-2)
    assert math.isclose(res["net_without_top10"], expected["net_without_top10"], abs_tol=1e-2)
    assert res["longest_losing_streak"] == expected["longest_losing_streak"]

    # Bootstrap fields (tolerance 1e-4)
    assert math.isclose(res["p_net_positive"], expected["p_net_positive"], abs_tol=1e-4)
    assert math.isclose(res["pf_p05"], expected["pf_p05"], abs_tol=1e-3)
    assert math.isclose(res["pf_p95"], expected["pf_p95"], abs_tol=1e-3)
    assert math.isclose(res["net_p05"], expected["net_p05"], abs_tol=1.0)
    assert math.isclose(res["net_p95"], expected["net_p95"], abs_tol=1.0)


def test_robustness_empty_and_single():
    assert robustness([])["p_net_positive"] is None
    assert robustness([100.0])["p_net_positive"] is None
