"""Causal multi-contract options research using Stolgo's simulated broker.

EXPERIMENTAL: this API may change without notice between releases. See the
"Known limitations" section of ``docs/OPTIONS_REPLAY.md``.
"""
from .replay import OptionSession, ReplayConfig, replay_session

__all__ = ["OptionSession", "ReplayConfig", "replay_session"]
