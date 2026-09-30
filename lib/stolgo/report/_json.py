"""JSON-clean normalization utility."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def clean(obj: Any) -> Any:
    """Recursively converts NaN/inf to None and normalizes numpy/pandas types for JSON serialization."""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return None if (np.isnan(obj) or np.isinf(obj)) else float(obj)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return int(obj.timestamp())
    if pd.isna(obj):
        return None
    return obj
