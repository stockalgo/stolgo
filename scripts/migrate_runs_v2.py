"""Deprecated shim forwarding to scripts/migrations/2026_09_v2.py."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "migrations" / "2026_09_v2.py"
    runpy.run_path(str(target), run_name="__main__")
