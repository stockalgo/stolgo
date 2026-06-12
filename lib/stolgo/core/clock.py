# stolgo agent mistake checklist — docs/IMPLEMENTATION_PLAN_BACKTEST.md §D

from __future__ import annotations

from collections.abc import Iterator, Sequence

from stolgo.core.types import Bar


class SimClock:
    def __init__(self, bars: Sequence[Bar]) -> None:
        self._bars = bars

    def __iter__(self) -> Iterator[tuple[int, Bar]]:
        for i, bar in enumerate(self._bars):
            yield i, bar
