from stolgo.core.clock import SimClock
from stolgo.core.types import Bar


def test_clock_iter():
    bars = (Bar(ts=i, open=1, high=1, low=1, close=1, volume=1, symbol="X") for i in range(3))
    assert len(list(SimClock(tuple(bars)))) == 3
