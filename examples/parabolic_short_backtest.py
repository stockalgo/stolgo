"""Parabolic Short Setup backtest across Binance USDT-M perpetual futures.

Usage
-----
    python examples/parabolic_short_backtest.py \\
        --start 2024-07-04 --end 2026-07-04 \\
        --min-quote-volume-usd 5000000 \\
        --lookback-days 5 --min-gain-pct 2.0 \\
        --r-multiple-target 4.0 \\
        --output-dir parabolic_short_output

Requires real network access to Binance (this repo's dev sandbox may not
have it — see README/AGENTS notes). All data comes from `bandl`'s Binance
adapter (public REST, no API key needed): `fapi.binance.com` for USDT-M
perpetual OHLCV + 24h tickers, `list_symbols` for the tradable universe.

For each qualifying symbol/setup this scans daily candles for:
  1. a >= `--min-gain-pct` parabolic move within a trailing
     `--lookback-days` window (relatively uninterrupted),
  2. the first red day after the peak with volume >= `--volume-multiplier`x
     the trailing average,
and simulates a short entered at that red day's close, stopped at its high,
targeting `--r-multiple-target` R, recording MFE/MAE and the realized
R-multiple for every trade.

Outputs (under --output-dir):
  trades.csv        - full trade log (see strategy.builtins.parabolic_short)
  metrics.json       - aggregate + per-symbol performance metrics
  tearsheet.html      - equity curve (cumulative R), R distribution, trade table
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from stolgo.data.bandl_source import BandlDataSource
from stolgo.data.binance_universe import get_binance_perp_universe
from stolgo.report.rmultiple_metrics import compute_rmultiple_metrics
from stolgo.strategy.builtins.parabolic_short import (
    ParabolicShortConfig,
    backtest_symbol,
    trades_to_dataframe,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=str, default=None, help="ISO date, default = 2 years before --end")
    p.add_argument("--end", type=str, default=None, help="ISO date, default = today (UTC)")
    p.add_argument("--interval", type=str, default="1d", help="bandl interval string, default 1d")
    p.add_argument("--lookback-days", type=int, default=5)
    p.add_argument("--min-gain-pct", type=float, default=2.0, help="2.0 == 200%%")
    p.add_argument("--max-interrupt-red-days", type=int, default=1)
    p.add_argument("--max-single-day-retrace-pct", type=float, default=0.30)
    p.add_argument("--volume-multiplier", type=float, default=1.5)
    p.add_argument("--volume-avg-window", type=int, default=20)
    p.add_argument("--r-multiple-target", type=float, default=4.0)
    p.add_argument("--entry-mode", choices=["close", "next_open"], default="close")
    p.add_argument("--max-days-to-find-red", type=int, default=5)
    p.add_argument("--max-holding-days", type=int, default=30)
    p.add_argument(
        "--min-quote-volume-usd",
        type=float,
        default=5_000_000.0,
        help="liquidity filter for the scanned universe (24h quote volume)",
    )
    p.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="comma-separated symbol override, skips the universe scan (e.g. BTCUSDT,ETHUSDT)",
    )
    p.add_argument("--max-symbols", type=int, default=None, help="cap universe size (fastest N by liquidity)")
    p.add_argument("--output-dir", type=str, default="parabolic_short_output")
    p.add_argument("--cache-dir", type=str, default=None, help="parquet cache root, default ~/.stolgo/cache")
    return p.parse_args(argv)


def _resolve_dates(args: argparse.Namespace) -> tuple[datetime, datetime]:
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc) if args.end else datetime.now(timezone.utc)
    start = (
        datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        if args.start
        else end - timedelta(days=365 * 2)
    )
    return start, end


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    start, end = _resolve_dates(args)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = ParabolicShortConfig(
        lookback_days=args.lookback_days,
        min_gain_pct=args.min_gain_pct,
        max_interrupt_red_days=args.max_interrupt_red_days,
        max_single_day_retrace_pct=args.max_single_day_retrace_pct,
        volume_multiplier=args.volume_multiplier,
        volume_avg_window=args.volume_avg_window,
        r_multiple_target=args.r_multiple_target,
        entry_mode=args.entry_mode,
        max_days_to_find_red=args.max_days_to_find_red,
        max_holding_days=args.max_holding_days,
    )

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        universe = get_binance_perp_universe(
            min_quote_volume_usd=args.min_quote_volume_usd,
            limit=args.max_symbols,
        )
        symbols = [p.symbol for p in universe]
        print(f"Scanning {len(symbols)} Binance USDT-M perpetuals "
              f"(min 24h quote volume ${args.min_quote_volume_usd:,.0f})")

    from stolgo.data.cache import ParquetCache

    cache = ParquetCache(root=Path(args.cache_dir)) if args.cache_dir else None
    source = BandlDataSource(source="binance", asset_type="crypto_perp", cache=cache)

    all_trades = []
    failures: dict[str, str] = {}
    for i, symbol in enumerate(symbols, start=1):
        try:
            df = source.history(symbol, args.interval, start, end)
        except Exception as exc:  # noqa: BLE001 - continue scanning other symbols
            failures[symbol] = str(exc)
            continue
        if len(df) < config.lookback_days + config.max_days_to_find_red + 2:
            continue
        trades = backtest_symbol(df, config, symbol=symbol)
        all_trades.extend(trades)
        print(f"[{i}/{len(symbols)}] {symbol}: {len(df)} bars, {len(trades)} setup(s)")

    trades_df = trades_to_dataframe(all_trades)
    trades_df.to_csv(out_dir / "trades.csv", index=False)

    metrics = compute_rmultiple_metrics(trades_df)
    equity_curve = metrics.pop("equity_curve_r")
    by_regime = metrics.get("by_regime")

    metrics_out = {k: v for k, v in metrics.items() if k != "by_regime"}
    if by_regime:
        metrics_out["by_regime"] = by_regime
    metrics_out["failures"] = failures
    metrics_out["universe_size"] = len(symbols)
    metrics_out["date_range"] = {"start": start.isoformat(), "end": end.isoformat()}
    (out_dir / "metrics.json").write_text(json.dumps(metrics_out, indent=2, default=str))

    _write_tearsheet(out_dir / "tearsheet.html", trades_df, metrics, equity_curve)

    print("\n=== Parabolic Short Backtest Summary ===")
    print(f"Total trades:        {metrics['total_trades']}")
    print(f"Closed trades:       {metrics['closed_trades']}")
    print(f"Win rate:            {metrics['win_rate']:.1%}")
    print(f"Avg R multiple:      {metrics['avg_r_multiple']:.2f}")
    print(f"Expectancy (R):      {metrics['expectancy_r']:.2f}")
    print(f"Profit factor:       {metrics['profit_factor']:.2f}")
    print(f"Max drawdown (R):    {metrics['max_drawdown_r']:.2f}")
    print(f"Avg holding (days):  {metrics['avg_holding_period_days']:.1f}")
    print(f"Best trade (R):      {metrics['best_trade_r']:.2f} ({metrics['best_trade_symbol']})")
    print(f"Worst trade (R):     {metrics['worst_trade_r']:.2f} ({metrics['worst_trade_symbol']})")
    if failures:
        print(f"Symbols with fetch errors: {len(failures)} (see metrics.json)")
    print(f"\nTrade log:  {(out_dir / 'trades.csv').resolve()}")
    print(f"Metrics:    {(out_dir / 'metrics.json').resolve()}")
    print(f"Tearsheet:  {(out_dir / 'tearsheet.html').resolve()}")
    return 0


def _write_tearsheet(
    path: Path,
    trades_df: pd.DataFrame,
    metrics: dict,
    equity_curve_r: pd.Series,
) -> None:
    """Minimal self-contained Plotly HTML tearsheet (equity curve, R histogram, trade table)."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        path.write_text("<html><body><p>plotly not installed; run `pip install plotly` "
                         "for the HTML tearsheet. See trades.csv / metrics.json instead.</p></body></html>")
        return

    closed = trades_df[trades_df["outcome"] != "open"] if not trades_df.empty else trades_df

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Cumulative R (equity curve)", "R-multiple distribution"),
        row_heights=[0.6, 0.4],
    )
    if len(equity_curve_r):
        fig.add_trace(
            go.Scatter(x=equity_curve_r.index, y=equity_curve_r.to_numpy(), mode="lines", name="equity"),
            row=1,
            col=1,
        )
    if len(closed):
        fig.add_trace(go.Histogram(x=closed["r_multiple"], name="R multiple", nbinsx=30), row=2, col=1)

    summary_lines = [
        f"Total trades: {metrics['total_trades']}",
        f"Win rate: {metrics['win_rate']:.1%}",
        f"Avg R: {metrics['avg_r_multiple']:.2f}",
        f"Expectancy (R): {metrics['expectancy_r']:.2f}",
        f"Profit factor: {metrics['profit_factor']:.2f}",
        f"Max drawdown (R): {metrics['max_drawdown_r']:.2f}",
        f"Avg holding (days): {metrics['avg_holding_period_days']:.1f}",
    ]
    fig.update_layout(
        title="Parabolic Short Setup — Backtest Tearsheet<br><sup>"
        + " | ".join(summary_lines)
        + "</sup>",
        height=800,
        showlegend=False,
    )

    table_html = closed.sort_values("exit_date").to_html(index=False) if len(closed) else "<p>No closed trades.</p>"
    html = (
        fig.to_html(full_html=False, include_plotlyjs="cdn")
        + "<h2>Trade log</h2>"
        + table_html
    )
    path.write_text(f"<html><head><title>Parabolic Short Tearsheet</title></head><body>{html}</body></html>")


if __name__ == "__main__":
    raise SystemExit(main())
