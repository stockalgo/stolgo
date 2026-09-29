import React from "react";
import { Button } from "../ui/Button.jsx";

export function TradesFilterBar({
  totalCount,
  winCount,
  lossCount,
  filterResult = "all",
  onFilterResultChange,
  exitReasons = [],
  selectedReason = "any",
  onReasonChange,
  dataFlags = [],
  selectedFlag = "any",
  onFlagChange,
  fromDate = "",
  toDate = "",
  onFromDateChange,
  onToDateChange,
  onExportCsv,
}) {
  return (
    <section
      style={{
        display: "flex",
        gap: "8px",
        alignItems: "center",
        flexWrap: "wrap",
      }}
    >
      {/* Result Seg [All N | Winners W | Losers L] */}
      <div className="seg">
        <button
          type="button"
          className={`seg__item ${filterResult === "all" ? "seg__item--active" : ""}`}
          aria-selected={filterResult === "all"}
          onClick={() => onFilterResultChange?.("all")}
        >
          All {totalCount}
        </button>
        <button
          type="button"
          className={`seg__item ${filterResult === "win" ? "seg__item--active" : ""}`}
          aria-selected={filterResult === "win"}
          onClick={() => onFilterResultChange?.("win")}
        >
          Winners {winCount}
        </button>
        <button
          type="button"
          className={`seg__item ${filterResult === "loss" ? "seg__item--active" : ""}`}
          aria-selected={filterResult === "loss"}
          onClick={() => onFilterResultChange?.("loss")}
        >
          Losers {lossCount}
        </button>
      </div>

      {/* Exit reason select */}
      <select
        className="select"
        style={{ width: "170px" }}
        value={selectedReason}
        aria-label="Filter by exit reason"
        onChange={(e) => onReasonChange?.(e.target.value)}
      >
        <option value="any">Exit reason: any</option>
        {exitReasons.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>

      {/* Data flag select */}
      <select
        className="select"
        style={{ width: "170px" }}
        value={selectedFlag}
        aria-label="Filter by data flag"
        onChange={(e) => onFlagChange?.(e.target.value)}
      >
        <option value="any">Data flag: any</option>
        <option value="none">none</option>
        {dataFlags.map((f) => (
          <option key={f} value={f}>
            {f}
          </option>
        ))}
      </select>

      {/* Date range filter */}
      <div
        className="field"
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: "8px",
          margin: 0,
        }}
      >
        <input
          type="date"
          className="input mono"
          style={{ width: "135px" }}
          aria-label="Filter from date"
          value={fromDate}
          onChange={(e) => onFromDateChange?.(e.target.value)}
        />
        <span aria-hidden="true">&rarr;</span>
        <input
          type="date"
          className="input mono"
          style={{ width: "135px" }}
          aria-label="Filter to date"
          value={toDate}
          onChange={(e) => onToDateChange?.(e.target.value)}
        />
      </div>

      <div style={{ flex: 1 }} />

      <span className="muted" style={{ fontSize: "12px" }}>
        Times in IST · amounts in ₹ · premium per unit
      </span>

      <Button
        size="sm"
        onClick={onExportCsv}
        aria-label="Export CSV"
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
        CSV (v2 columns)
      </Button>
    </section>
  );
}
