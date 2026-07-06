"""CLI entrypoint — build step 11."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from stolgo import Backtest, Strategy, load
from stolgo.report.exporters import export_all


def _load_strategy(path: Path, class_name: str) -> Strategy:
    spec = importlib.util.spec_from_file_location("user_strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load strategy from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None or not isinstance(cls, type) or not issubclass(cls, Strategy):
        raise RuntimeError(f"{class_name} must be a stolgo Strategy subclass in {path}")
    return cls()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "serve":
        parser = argparse.ArgumentParser(description="stolgo local UI server")
        parser.add_argument("command", choices=["serve"])
        parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
        parser.add_argument("--port", type=int, default=8000)
        parser.add_argument("--host", default="127.0.0.1")
        args = parser.parse_args(argv)

        import uvicorn

        from stolgo.ui.server import create_app

        app = create_app(args.runs_dir)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    parser = argparse.ArgumentParser(description="stolgo backtest runner (v0.1)")
    parser.add_argument("strategy", type=Path, help="Path to strategy .py file")
    parser.add_argument("--class", dest="class_name", default="Strategy", help="Strategy class name")
    parser.add_argument("--data", type=Path, required=True, help="OHLCV CSV path")
    parser.add_argument("--cash", type=float, default=100_000.0)
    parser.add_argument("--commission", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=Path("stolgo_output"), help="Output directory")
    args = parser.parse_args(argv)

    df = load(args.data)

    strategy = _load_strategy(args.strategy, args.class_name)
    result = Backtest(strategy, df, cash=args.cash, commission=args.commission).run()
    print(result.summary())
    export_all(result, args.output, strategy_name=args.class_name)
    print(f"Wrote tearsheet to {args.output / 'tearsheet.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
