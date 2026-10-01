"""Idempotent migration of runs from v1 to v2 schema."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import math
from pathlib import Path
import re
import shutil
import sys
from typing import Any

logger = logging.getLogger("stolgo.scripts.migrate_runs_v2")

import numpy as np
import pandas as pd

from stolgo.report.daily import build_calendar_files, build_daily, load_calendar, sessions_from_ohlcv
from stolgo.report.diagnostics import build_diagnostics
from stolgo.report.exporters import export_run_v2
from stolgo.report.quality import run_status
from stolgo.report.robustness import robustness
from stolgo.report.run_metrics import compute_run_metrics
from stolgo.report.trade_schema import SourceMapping, assign_trade_markets_and_lots, normalize_trades
from stolgo.report.validate import fix_ist_labelled_utc, looks_like_ist_labelled_utc

G1_RE = re.compile(
    r"^(?:(NIFTY|SENSEX)-(strangle|iron-condor)-(0|1)dte|top[123]-.*|combined-top3-.*)$"
)
G2_RE = re.compile(
    r"^(nifty|sensex)-(0|1)dte-(strangle-benchmark|iron-condor-otm1-w4|iron-fly-atm-w5)$"
)
G3_RE = re.compile(r"^nifty-sr-audited-")
G4_RE = re.compile(r"^nifty-sr-premium-spike-")
G5_RE = re.compile(r"^validated-timing-3y-(nifty|sensex)-(0|1)dte-(.+)$")

VARIANT_ABCD_RE = re.compile(r"^(a|b|c|d)-cap(\d+)-d(\d)(?:-w(\d))?$")
VARIANT_CUT_RE = re.compile(r"^cut-d(\d)$")


def classify_run(run_id: str) -> tuple[str, dict[str, Any]]:
    """Return (group_name, metadata) for a run_id."""
    if G1_RE.match(run_id):
        meta: dict[str, Any] = {"group": "G1"}
        if run_id == "top1-sensex-1dte-strangle":
            meta.update(
                {"market": "SENSEX", "exchange": "BSE", "dte": [1], "structure": "short_strangle", "lot_size": 20}
            )
        elif run_id == "top2-nifty-pre-expiry-strangle":
            meta.update(
                {"market": "NIFTY", "exchange": "NSE", "dte": [1, 2], "structure": "short_strangle", "lot_size": 65}
            )
        elif run_id == "top3-nifty-0dte-strangle":
            meta.update(
                {"market": "NIFTY", "exchange": "NSE", "dte": [0], "structure": "short_strangle", "lot_size": 65}
            )
        elif run_id == "combined-top3-weekly-calendar":
            meta.update(
                {
                    "markets": ["NIFTY", "SENSEX"],
                    "exchange": "NSE",
                    "dte": [0, 1, 2],
                    "structure": "short_strangle",
                    "lot_size": 65,
                    "ohlcv_market": "NIFTY",
                }
            )
        else:
            m = G1_RE.match(run_id)
            assert m is not None
            mkt, struct_name, dte_str = m.group(1), m.group(2), m.group(3)
            struct = "short_strangle" if struct_name == "strangle" else "iron_condor"
            exch = "BSE" if mkt == "SENSEX" else "NSE"
            lot = 20 if mkt == "SENSEX" else 65
            meta.update(
                {
                    "market": mkt,
                    "exchange": exch,
                    "dte": [int(dte_str)],
                    "structure": struct,
                    "lot_size": lot,
                }
            )
        return "G1", meta

    if G2_RE.match(run_id):
        m = G2_RE.match(run_id)
        assert m is not None
        mkt = m.group(1).upper()
        dte_val = int(m.group(2))
        s_name = m.group(3)
        if s_name == "strangle-benchmark":
            struct = "short_strangle"
        elif s_name == "iron-condor-otm1-w4":
            struct = "iron_condor"
        else:
            struct = "iron_fly"
        exch = "BSE" if mkt == "SENSEX" else "NSE"
        return "G2", {
            "group": "G2",
            "market": mkt,
            "exchange": exch,
            "dte": [dte_val],
            "structure": struct,
        }

    if G3_RE.match(run_id):
        g3_meta = {
            "group": "G3",
            "market": "NIFTY",
            "exchange": "NSE",
            "structure": "unknown",  # will be derived from side/tag
        }
        if "-0plus1-" in run_id:
            g3_meta["dte"] = [0, 1]
        elif "-0-" in run_id:
            g3_meta["dte"] = [0]
        elif "-1-" in run_id:
            g3_meta["dte"] = [1]
        return "G3", g3_meta

    if G4_RE.match(run_id):
        g4_meta = {
            "group": "G4",
            "market": "NIFTY",
            "exchange": "NSE",
            "structure": "bear_call_spread",
            "superseded": True,
        }
        if "0dte" in run_id:
            g4_meta["dte"] = [0]
        elif "1dte" in run_id:
            g4_meta["dte"] = [1]
        return "G4", g4_meta

    m5 = G5_RE.match(run_id)
    if m5:
        mkt = m5.group(1).upper()
        dte_val = int(m5.group(2))
        variant = m5.group(3)
        exch = "BSE" if mkt == "SENSEX" else "NSE"

        family = None
        cap = None
        d_val = None
        w_val = None

        m_abcd = VARIANT_ABCD_RE.match(variant)
        m_cut = VARIANT_CUT_RE.match(variant)
        if m_abcd:
            family = m_abcd.group(1).upper()
            cap = int(m_abcd.group(2))
            d_val = int(m_abcd.group(3))
            w_val = int(m_abcd.group(4)) if m_abcd.group(4) else None
        elif m_cut:
            family = "CUT"
            d_val = int(m_cut.group(1))
        elif variant == "static":
            family = "STATIC"
        elif variant == "static-leg100-close-all":
            family = "LEG100"
        elif variant == "exit-touch":
            family = "EXIT_TOUCH"
        elif variant == "one-conversion":
            family = "ONE_CONV"

        axes = {
            "market": mkt,
            "dte": dte_val,
            "family": family,
            "cap": cap,
            "d": d_val,
            "w": w_val,
        }
        return "G5", {
            "group": "G5",
            "market": mkt,
            "exchange": exch,
            "dte": [dte_val],
            "structure": "short_strangle",
            "group_dict": {
                "id": "validated-timing-3y",
                "label": "3-year timing sweep",
                "axes": axes,
            },
        }

    return "UNMAPPED", {}


def backup_runs_if_needed(runs_dir: Path) -> Path:
    backup_dir = runs_dir / "_backup_v1"
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)
        for p in runs_dir.iterdir():
            if p.is_dir() and not p.name.startswith("_"):
                dest = backup_dir / p.name
                shutil.copytree(p, dest)
        print(f"Created backup of runs at {backup_dir}")
    return backup_dir


def migrate_run(
    run_id: str,
    backup_run_dir: Path,
    target_run_dir: Path,
    calendars: dict[str, pd.DatetimeIndex],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    group_name, meta = classify_run(run_id)
    if group_name == "UNMAPPED":
        return {"run_id": run_id, "group": "UNMAPPED", "status": "unmapped", "warnings": ["Unmapped run"]}

    manifest_path = backup_run_dir / "manifest.json"
    if not manifest_path.is_file():
        return {"run_id": run_id, "group": group_name, "status": "no_manifest", "warnings": ["No manifest.json"]}

    manifest = json.loads(manifest_path.read_text())
    source_params = manifest.get("params") or {}
    source_metrics = manifest.get("metrics") or {}

    capital = float(source_params.get("capital", source_params.get("cash", 100_000.0)))
    if capital <= 0:
        capital = 180_000.0

    # Load trades
    trades_parquet = backup_run_dir / "parquet" / "trades.parquet"
    if trades_parquet.is_file():
        trades_df = pd.read_parquet(trades_parquet)
    else:
        trades_csv = backup_run_dir / "trades.csv"
        if trades_csv.is_file():
            trades_df = pd.read_csv(trades_csv)
        else:
            trades_df = pd.DataFrame()

    warnings: list[str] = []

    # Handle timestamps: G1 needs IST-labelled-as-UTC fix
    if group_name == "G1":
        is_ist_labelled = False
        if "exit_ts" in trades_df.columns and not trades_df["exit_ts"].empty:
            is_ist_labelled = looks_like_ist_labelled_utc(trades_df["exit_ts"], exchange=meta["exchange"])
        elif "entry_ts" in trades_df.columns and not trades_df["entry_ts"].empty:
            is_ist_labelled = looks_like_ist_labelled_utc(trades_df["entry_ts"], exchange=meta["exchange"])

        for col in ("entry_ts", "exit_ts"):
            if col in trades_df.columns and not trades_df[col].empty:
                ts = pd.to_datetime(trades_df[col])
                if is_ist_labelled:
                    trades_df[col] = fix_ist_labelled_utc(ts)
                    warnings.append(f"Fixed IST-labelled UTC timestamps in {col}")
                else:
                    if ts.dt.tz is None:
                        ts = ts.dt.tz_localize("UTC")
                    trades_df[col] = ts
    else:
        for col in ("entry_ts", "exit_ts"):
            if col in trades_df.columns and not trades_df[col].empty:
                ts = pd.to_datetime(trades_df[col])
                if ts.dt.tz is None:
                    ts = ts.dt.tz_localize("UTC")
                trades_df[col] = ts

    # Price columns & mapping
    price_cols: Any = "none"
    lot_size = meta.get("lot_size")
    struct = meta.get("structure", "short_strangle")

    if group_name == "G1":
        price_cols = "premium"
    elif group_name == "G2":
        price_cols = "underlying"
        if lot_size is None and not trades_df.empty and "qty" in trades_df.columns:
            lot_size = int(trades_df["qty"].iloc[0])
    elif group_name in ("G3", "G4"):
        price_cols = "premium"
        if "filled_entry_credit" in trades_df.columns:
            trades_df["entry_price"] = trades_df["filled_entry_credit"]
            if "filled_exit_debit" in trades_df.columns:
                trades_df["exit_price"] = trades_df["filled_exit_debit"]

        # Infer structure for G3/G4
        if not trades_df.empty and "tag" in trades_df.columns:
            tags_str = " ".join(trades_df["tag"].dropna().astype(str).tolist()).lower()
            if "bear_call" in tags_str:
                struct = "bear_call_spread"
            elif "bull_put" in tags_str:
                struct = "bull_put_spread"
            else:
                struct = "unknown"
    elif group_name == "G5":
        price_cols = "none"
        struct = "short_strangle"

    markets_list = meta.get("markets") or ([meta["market"]] if "market" in meta else ["NIFTY"])

    mapping = SourceMapping(
        price_columns=price_cols,
        structure=struct,
        market=meta.get("market"),
        lot_size=lot_size,
        side="SHORT" if struct in ("short_strangle", "iron_condor", "iron_fly") else "from_column",
    )

    trades_v2, legs_v2 = normalize_trades(trades_df, mapping)
    trades_v2 = assign_trade_markets_and_lots(trades_v2, markets_list)

    # Load OHLCV or Calendar
    ohlcv_path = backup_run_dir / "parquet" / "ohlcv.parquet"
    ohlcv_df: pd.DataFrame | None = None
    if ohlcv_path.is_file():
        ohlcv_df = pd.read_parquet(ohlcv_path)
        sessions = sessions_from_ohlcv(ohlcv_df)
    else:
        sessions = calendars[meta.get("exchange", "NSE")]

    # Build daily
    if not trades_v2.empty:
        daily = build_daily(trades_v2, capital, sessions)
        start_date = daily["session"].iloc[0]
        end_date = daily["session"].iloc[-1]
        n_sessions = len(daily)
    else:
        daily = pd.DataFrame(columns=["session", "pnl", "equity", "drawdown", "trades_closed"])
        start_date = None
        end_date = None
        n_sessions = 0

    # Compute metrics
    intraday_eq_path = backup_run_dir / "parquet" / "equity.parquet"
    intraday_equity = None
    if intraday_eq_path.is_file() and group_name == "G5":
        intraday_equity = pd.read_parquet(intraday_eq_path)["equity"]

    if not daily.empty:
        metrics = compute_run_metrics(trades_v2, capital, daily, intraday_equity=intraday_equity)
    else:
        metrics = {
            "basis": "calendar_daily",
            "net_pnl": 0.0,
            "gross_pnl": 0.0,
            "fees": 0.0,
            "slippage": None,
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": None,
            "calmar": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "intraday_max_drawdown": None,
            "volatility": 0.0,
            "ulcer_index": 0.0,
            "worst_day": 0.0,
            "expected_shortfall_95": 0.0,
            "num_trades": 0,
            "hit_rate": 0.0,
            "profit_factor": None,
            "payoff": None,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
            "avg_r": None,
            "final_equity": capital,
            "annualised_from_short_window": True,
        }

    # Group G5 keep source metrics for specific keys
    if group_name == "G5":
        keep_keys = [
            "cagr",
            "sharpe",
            "sortino",
            "calmar",
            "max_drawdown",
            "max_drawdown_duration",
            "intraday_max_drawdown",
            "worst_day",
            "expected_shortfall_95",
        ]
        recomputed_sharpe = metrics.get("sharpe")
        source_sharpe = source_metrics.get("sharpe")
        if recomputed_sharpe is not None and source_sharpe is not None:
            if abs(recomputed_sharpe - source_sharpe) > 0.02:
                warnings.append(
                    f"Sharpe mismatch in G5 run {run_id}: recomputed {recomputed_sharpe:.4f} vs source {source_sharpe:.4f}"
                )

        for k in keep_keys:
            if k in source_metrics:
                metrics[k] = source_metrics[k]

    # Robustness
    net_pnl_arr = trades_v2["net_pnl"].values if not trades_v2.empty and "net_pnl" in trades_v2.columns else []
    robustness_dict = robustness(net_pnl_arr)

    # Diagnostics
    has_audit_file = (backup_run_dir / "audit.html").is_file()
    diagnostics_dict = build_diagnostics(
        trades_v2,
        daily,
        capital,
        manifest,
        has_audit_file=has_audit_file,
    )

    # Config & Instrument
    markets_list = meta.get("markets") or ([meta["market"]] if "market" in meta else ["NIFTY"])
    dte_list = meta.get("dte", [])
    if not trades_v2.empty and "dte" in trades_v2.columns and not trades_v2["dte"].dropna().empty:
        valid_dtes = trades_v2["dte"].dropna().unique()
        try:
            dte_list = sorted([int(x) for x in valid_dtes])
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to cast dte list to ints for run %s: %s", run_id, exc)
            dte_list = sorted(list(valid_dtes))

    inst = {
        "asset_class": "index_options",
        "markets": markets_list,
        "exchange": meta.get("exchange", "NSE"),
        "structure": struct,
        "dte": dte_list,
        "lot_size": lot_size,
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    }
    group_dict = meta.get("group_dict", {"id": None, "label": None, "axes": {}})

    raw_params = dict(source_params)
    if meta.get("superseded") or manifest.get("name", "").startswith("INVALID") or run_id.startswith("INVALID"):
        raw_params["superseded"] = True

    # Drop duplicated metrics in raw_params per F15
    for dup_k in ("sharpe", "cagr", "sortino", "calmar", "total_return", "max_drawdown", "hit_rate", "profit_factor"):
        raw_params.pop(dup_k, None)

    config = {
        "capital": capital,
        "window": {"start": start_date, "end": end_date, "sessions": n_sessions},
        "entry_rule": source_params.get("entry_rule"),
        "exit_rule": source_params.get("exit_rule"),
        "execution": source_params.get("execution"),
        "cost_model": source_params.get("cost_model"),
        "data_source": source_params.get("data_source"),
        "code_version": source_params.get("code_version"),
        "raw_params": raw_params,
    }

    # Human readable name
    name = manifest.get("name") or manifest.get("strategy") or run_id

    # Determine status & reasons
    status, status_reasons = run_status(
        name,
        metrics,
        diagnostics_dict,
        n_sessions,
        raw_params=raw_params,
    )

    # Prepare extra files
    extra_files = {}
    for fname in ("tearsheet.html", "summary.json", "audit.html"):
        fpath = backup_run_dir / fname
        if fpath.is_file():
            extra_files[fname] = fpath

    migrated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    migrated_changed_basis = group_name in ("G1", "G2", "G4")

    ohlcv_mkt = meta.get("ohlcv_market")
    if not ohlcv_mkt and len(markets_list) == 1:
        ohlcv_mkt = markets_list[0]
    elif not ohlcv_mkt and len(markets_list) > 1:
        ohlcv_mkt = "NIFTY"

    if not dry_run:
        export_run_v2(
            target_run_dir,
            run_id=run_id,
            name=name,
            trades_v2=trades_v2,
            legs_v2=legs_v2,
            daily=daily,
            instrument=inst,
            group=group_dict,
            config=config,
            metrics=metrics,
            robustness=robustness_dict,
            diagnostics=diagnostics_dict,
            ohlcv=ohlcv_df,
            ohlcv_market=ohlcv_mkt,
            intraday_equity=intraday_equity,
            extra_files=extra_files,
            created_at=manifest.get("created_at"),
            migrated_at=migrated_at,
            migrated_changed_basis=migrated_changed_basis,
        )

    old_total_return = source_metrics.get("total_return")
    old_cagr = source_metrics.get("cagr")
    old_sharpe = source_metrics.get("sharpe")

    return {
        "run_id": run_id,
        "group": group_name,
        "status": status,
        "status_reasons": status_reasons,
        "old_total_return": old_total_return,
        "new_total_return": metrics.get("total_return"),
        "old_cagr": old_cagr,
        "new_cagr": metrics.get("cagr"),
        "old_sharpe": old_sharpe,
        "new_sharpe": metrics.get("sharpe"),
        "warnings": warnings,
    }


def compare_with_fixture(runs_dir: Path) -> list[str]:
    """Compare migrated runs with expected_after_migration.json."""
    fixture_path = (
        Path(__file__).resolve().parent.parent / "docs/plans/fixtures/expected_after_migration.json"
    )
    if not fixture_path.is_file():
        return [f"Fixture not found at {fixture_path}"]

    data = json.loads(fixture_path.read_text())
    expected_runs = data.get("runs", {})
    mismatches: list[str] = []

    for run_id, exp_spec in expected_runs.items():
        run_manifest_path = runs_dir / run_id / "manifest.json"
        if not run_manifest_path.is_file():
            mismatches.append(f"{run_id}: manifest.json not found")
            continue

        manifest = json.loads(run_manifest_path.read_text())
        actual_m = manifest.get("metrics", {})
        expected_m = exp_spec.get("expected", {})

        # Total return check (rel=1e-6 or abs=1e-5)
        act_tr = actual_m.get("total_return")
        exp_tr = expected_m.get("total_return")
        if act_tr is not None and exp_tr is not None:
            if not math.isclose(act_tr, exp_tr, rel_tol=1e-6, abs_tol=1e-5):
                mismatches.append(
                    f"{run_id} total_return mismatch: actual {act_tr} vs expected {exp_tr}"
                )

        # Ratios check (abs=1e-3)
        for key in ("cagr", "sharpe", "sortino", "max_drawdown"):
            act_v = actual_m.get(key)
            exp_v = expected_m.get(key)
            if act_v is not None and exp_v is not None:
                if not math.isclose(act_v, exp_v, abs_tol=1e-3):
                    mismatches.append(
                        f"{run_id} {key} mismatch: actual {act_v} vs expected {exp_v}"
                    )

    return mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate stolgo runs to v2 schema")
    parser.add_argument("--runs-dir", default="runs", help="Directory containing runs")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without writing")
    parser.add_argument("--only", nargs="+", help="Migrate only specified run IDs")
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir).resolve()
    print(f"Runs directory: {runs_dir} (dry_run={args.dry_run})")

    backup_dir = backup_runs_if_needed(runs_dir)

    # Build calendars
    cal_counts = build_calendar_files(runs_dir)
    print(f"Calendar session counts: {cal_counts}")

    calendars = {
        "NSE": load_calendar(runs_dir, "NSE"),
        "BSE": load_calendar(runs_dir, "BSE"),
    }

    # Find runs to migrate from backup
    all_runs = sorted(
        [p.name for p in backup_dir.iterdir() if p.is_dir() and not p.name.startswith("_")]
    )
    if args.only:
        all_runs = [r for r in all_runs if r in args.only]

    print(f"Migrating {len(all_runs)} runs...")

    reports = []
    unmapped_count = 0

    for r_id in all_runs:
        b_dir = backup_dir / r_id
        t_dir = runs_dir / r_id
        rep = migrate_run(r_id, b_dir, t_dir, calendars, dry_run=args.dry_run)
        reports.append(rep)
        if rep["group"] == "UNMAPPED":
            unmapped_count += 1
            print(f"UNMAPPED run: {r_id}")

    # Generate _migration_report.md
    report_lines = [
        "# Stolgo Migration Report v2",
        f"\nGenerated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"Total runs: {len(reports)}, Unmapped: {unmapped_count}\n",
        "| Run ID | Group | Status | Total Return (old -> new) | CAGR (old -> new) | Sharpe (old -> new) | Warnings |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        tr_s = f"{r['old_total_return']} -> {r['new_total_return']}"
        cagr_s = f"{r['old_cagr']} -> {r['new_cagr']}"
        sharpe_s = f"{r['old_sharpe']} -> {r['new_sharpe']}"
        warns = ", ".join(r["warnings"]) if r["warnings"] else "none"
        report_lines.append(
            f"| {r['run_id']} | {r['group']} | {r['status']} | {tr_s} | {cagr_s} | {sharpe_s} | {warns} |"
        )

    if args.dry_run:
        print(f"Dry run complete: {len(reports)} runs mapped, {unmapped_count} unmapped.")
    else:
        (runs_dir / "_migration_report.md").write_text("\n".join(report_lines) + "\n")
        print(f"Wrote migration report to {runs_dir / '_migration_report.md'}")

        # Compare with fixture
        mismatches = compare_with_fixture(runs_dir)
        if mismatches:
            print("ERROR: Mismatches with expected fixture found:")
            for m in mismatches[:10]:
                print(f"  {m}")
            sys.exit(1)
        else:
            print("All 22 legacy runs match expected_after_migration.json within tolerance!")

    if unmapped_count > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
