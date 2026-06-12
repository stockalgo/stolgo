"""Tests for stolgo.core.exceptions."""

from __future__ import annotations

from stolgo.core.exceptions import (
    DataError,
    LookaheadError,
    ModeNotSupportedError,
    StolgoError,
)


def test_inheritance_chain() -> None:
    err = DataError("bad data for RELIANCE 1d")
    assert isinstance(err, StolgoError)
    assert err.message == "bad data for RELIANCE 1d"


def test_mode_not_supported() -> None:
    err = ModeNotSupportedError("live/paper mode not implemented until v0.3")
    assert isinstance(err, StolgoError)


def test_lookahead_error() -> None:
    assert issubclass(LookaheadError, StolgoError)
