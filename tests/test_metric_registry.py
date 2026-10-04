from stolgo.report.metric_registry import METRICS, metric_defs


def test_metric_registry_keys_unique():
    keys = [m.key for m in METRICS]
    assert len(keys) == len(set(keys))


def test_metric_registry_units():
    for m in METRICS:
        if m.unit == "r":
            assert m.key == "avg_r"
        if m.key == "expectancy":
            assert m.unit == "inr"


def test_metric_defs_as_dicts():
    defs = metric_defs()
    assert len(defs) == len(METRICS)
    assert all(isinstance(d, dict) for d in defs)
    assert any(d["key"] == "sharpe" for d in defs)
