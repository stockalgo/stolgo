import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { getTrades } from "../../api/endpoints.js";

const REQUIRED_V2_COLUMNS = [
  "trade_id",
  "session_date",
  "entry_ts",
  "exit_ts",
  "side",
  "structure",
  "market",
  "dte",
  "expiry",
  "qty",
  "lots",
  "underlying_entry",
  "underlying_exit",
  "premium_entry",
  "premium_exit",
  "gross_pnl",
  "fees",
  "slippage",
  "net_pnl",
  "r_multiple",
  "risk_inr",
  "exit_reason",
  "data_flag",
  "legs_label",
  "source_tag",
];

function escapeCsvCell(val) {
  if (val === null || val === undefined) return "";
  const str = String(val);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function RunTabs({ run, onToast }) {
  const [downloading, setDownloading] = useState(false);
  const location = useLocation();

  if (!run) return null;

  const numTrades = run.metrics?.num_trades ?? 0;
  const hasAudit = Boolean(run.has?.audit);

  const pathname = location.pathname;
  const isOverview = pathname === `/runs/${run.id}` || pathname === `/runs/${run.id}/`;
  const isTrades = pathname.startsWith(`/runs/${run.id}/trades`);
  const isDiagnostics = pathname.startsWith(`/runs/${run.id}/diagnostics`);

  const handleAddToCompare = () => {
    try {
      const stored = sessionStorage.getItem("stolgo.compare");
      const current = stored ? JSON.parse(stored) : [];
      if (current.includes(run.id)) {
        onToast?.("Already in compare");
        return;
      }
      if (current.length >= 4) {
        onToast?.("Compare holds 4 runs");
        return;
      }
      const updated = [...current, run.id];
      sessionStorage.setItem("stolgo.compare", JSON.stringify(updated));
      onToast?.(`Added ${run.id} to compare`);
    } catch {
      onToast?.("Failed to update compare list");
    }
  };

  const handleExportCsv = async () => {
    try {
      setDownloading(true);
      const rows = await getTrades(run.id);
      if (!rows || rows.length === 0) {
        onToast?.("No trades to export");
        return;
      }

      // Collect all keys, starting with REQUIRED_V2_COLUMNS
      const firstRow = rows[0] || {};
      const extraKeys = Object.keys(firstRow).filter(
        (k) => !REQUIRED_V2_COLUMNS.includes(k)
      );
      const allColumns = [...REQUIRED_V2_COLUMNS, ...extraKeys];

      const csvLines = [
        allColumns.join(","),
        ...rows.map((row) =>
          allColumns.map((col) => escapeCsvCell(row[col])).join(",")
        ),
      ];

      const csvContent = csvLines.join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${run.id}-trades.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      onToast?.("Downloaded trades CSV");
    } catch (err) {
      onToast?.(`Failed to export CSV: ${err.message || "Unknown error"}`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div
      className="tabs"
      role="tablist"
      style={{ display: "flex", alignItems: "flex-end", borderBottom: "1px solid var(--line)" }}
    >
      <div style={{ display: "flex", gap: "4px", flex: 1 }}>
        <NavLink
          to={`/runs/${run.id}`}
          end
          className="tab"
          aria-selected={isOverview}
          role="tab"
        >
          Overview
        </NavLink>

        <NavLink
          to={`/runs/${run.id}/trades`}
          className="tab"
          aria-selected={isTrades}
          role="tab"
        >
          Trades
          <span className="count">{numTrades}</span>
        </NavLink>

        <NavLink
          to={`/runs/${run.id}/diagnostics`}
          className="tab"
          aria-selected={isDiagnostics}
          role="tab"
        >
          Diagnostics
        </NavLink>
      </div>

      <div style={{ display: "flex", gap: "8px", paddingBottom: "6px" }}>
        <button className="btn btn--sm" onClick={handleAddToCompare}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="8" y1="4" x2="8" y2="20" />
            <line x1="16" y1="4" x2="16" y2="20" />
            <polyline points="4 8 8 4 12 8" />
            <polyline points="12 16 16 20 20 16" />
          </svg>
          Add to compare
        </button>

        {hasAudit && (
          <a
            href={`/api/runs/${run.id}/audit`}
            target="_blank"
            rel="noreferrer"
            className="btn btn--sm"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M14 4h6v6" />
              <line x1="20" y1="4" x2="11" y2="13" />
              <path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
            </svg>
            Audit report
          </a>
        )}

        <button
          className="btn btn--sm"
          onClick={handleExportCsv}
          disabled={downloading}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 4v11" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="5" y1="20" x2="19" y2="20" />
          </svg>
          {downloading ? "Exporting…" : "Trades CSV"}
        </button>
      </div>
    </div>
  );
}
