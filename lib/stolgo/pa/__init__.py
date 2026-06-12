# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

"""Price-action library — ``import stolgo.pa as pa`` (flat public API)."""

from stolgo.pa._core import Level, Rule, all_of, any_of
from stolgo.pa.levels import (
    cluster,
    donchian_high,
    donchian_low,
    level,
    level_from_series,
    range_high,
    range_low,
    resistance,
    support,
)
from stolgo.pa.levels.extended import (
    pivot_point,
    prev_day_high,
    prev_day_low,
    swing_high,
    swing_low,
    vwap,
)
from stolgo.pa.patterns import (
    bearish,
    bearish_engulfing,
    breakout_down,
    breakout_up,
    bullish,
    bullish_engulfing,
    consolidation,
    doji,
    first_green_day,
    first_red_day,
    giant_downtrend,
    giant_uptrend,
    green,
    hammer,
    inverted_hammer,
    parabolic_down,
    parabolic_up,
    range_bound,
    red,
    run_down,
    run_up,
    streak,
)
from stolgo.pa.relations import (
    above,
    below,
    bounced_off,
    breaks_above,
    breaks_below,
    crosses_above,
    crosses_below,
    failed_breakdown_below,
    failed_breakout_above,
    near,
    recovered_at,
    rejected_at,
    touched,
)

__all__ = [
    "Level",
    "Rule",
    "above",
    "all_of",
    "any_of",
    "bearish",
    "bearish_engulfing",
    "below",
    "bounced_off",
    "breakout_down",
    "breakout_up",
    "breaks_above",
    "breaks_below",
    "bullish",
    "bullish_engulfing",
    "cluster",
    "consolidation",
    "crosses_above",
    "crosses_below",
    "doji",
    "donchian_high",
    "donchian_low",
    "failed_breakdown_below",
    "failed_breakout_above",
    "first_green_day",
    "first_red_day",
    "giant_downtrend",
    "giant_uptrend",
    "green",
    "hammer",
    "inverted_hammer",
    "level",
    "level_from_series",
    "near",
    "parabolic_down",
    "parabolic_up",
    "pivot_point",
    "preset",
    "prev_day_high",
    "prev_day_low",
    "range_bound",
    "range_high",
    "range_low",
    "recovered_at",
    "red",
    "rejected_at",
    "resistance",
    "run_down",
    "run_up",
    "streak",
    "support",
    "swing_high",
    "swing_low",
    "touched",
    "vwap",
]

from stolgo.pa import preset as preset  # noqa: E402

__all__.append("preset")


def help(name: str | None = None) -> None:
    """Print grouped public API names or docstring for ``name``."""
    if name is None:
        groups = {
            "Levels": [
                "resistance",
                "support",
                "donchian_high",
                "donchian_low",
                "level",
                "level_from_series",
                "cluster",
                "range_high",
                "range_low",
            ],
            "Relations": [
                "above",
                "below",
                "crosses_above",
                "crosses_below",
                "rejected_at",
                "recovered_at",
                "near",
                "touched",
            ],
            "Patterns": [
                "consolidation",
                "breakout_up",
                "breakout_down",
                "bullish_engulfing",
                "bearish_engulfing",
                "streak",
                "run_up",
                "first_red_day",
            ],
            "Presets": [
                "preset.scalp_green_fade",
                "preset.breakout_intraday",
                "preset.failed_break_intraday",
                "preset.parabolic_short",
                "preset.consolidation_breakout",
            ],
        }
        for title, names in groups.items():
            print(f"\n{title}:")
            for n in names:
                print(f"  {n}")
        return
    obj = globals().get(name)
    if obj is None and name.startswith("preset."):
        obj = getattr(preset, name.split(".", 1)[1], None)
    print(getattr(obj, "__doc__", None) or f"unknown: {name}")
