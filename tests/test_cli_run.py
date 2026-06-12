"""Tests for stolgo.cli.main."""

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    repo = Path(__file__).resolve().parents[1]
    python = repo / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)
    proc = subprocess.run(
        [str(python), "-m", "stolgo.cli.main", "--help"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "backtest" in proc.stdout.lower()
