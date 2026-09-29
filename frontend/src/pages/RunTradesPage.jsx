import React, { useMemo, useCallback } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { getTrades } from "../api/endpoints.js";
import { TradesFilterBar } from "../components/trades/TradesFilterBar.jsx";
import { TradesTable } from "../components/trades/TradesTable.jsx";

const CSV_COLUMNS = [
  "trade_id",
  "session_date",
  "structure",
  "legs_label",
  "underlying_entry",
  "underlying_exit",
  "premium_entry",
  "premium_exit",
  "qty",
  "lots",
  "gross_pnl",
  "fees",
  "slippage",
  "net_pnl",
  "r_multiple",
  "exit_reason",
  "data_flag",
  "entry_ts",
  "exit_ts",
];

function downloadCsv(trades, filename = "trades.csv") {
  const header = CSV_COLUMNS.join(",");
  const rows = trades.map((t) =>
    CSV_COLUMNS.map((col) => {
      const val = t[col];
      if (val === null || val === undefined) return "";
      if (typeof val === "string") {
        if (val.includes(",") || val.includes('"') || val.includes("\n")) {
          return `"${val.replace(/"/g, '""')}"`;
        }
        return val;
      }
      return String(val);
    }).join(",")
  );
  const csvContent = [header, ...rows].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function RunTradesPage() {
  const { run } = useOutletContext();
  const [searchParams, setSearchParams] = useSearchParams();

  const fetchTrades = useCallback(
    () => (run?.id ? getTrades(run.id) : Promise.resolve([])),
    [run?.id]
  );
  const { data: rawTrades, loading } = useApi(fetchTrades);
  const trades = useMemo(
    () => (Array.isArray(rawTrades) ? rawTrades : rawTrades?.rows || []),
    [rawTrades]
  );

  // Read filter state from URL
  const filterResult = searchParams.get("result") || "all";
  const selectedReason = searchParams.get("reason") || "any";
  const selectedFlag = searchParams.get("flag") || "any";
  const fromDate = searchParams.get("from") || "";
  const toDate = searchParams.get("to") || "";
  const tradeParam = searchParams.get("trade");
  const expandedTradeId = tradeParam ? Number(tradeParam) : null;
  const pageParam = parseInt(searchParams.get("page") || "1", 10);
  const page = Number.isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;

  // Distinct options
  const exitReasons = useMemo(() => {
    const set = new Set();
    trades.forEach((t) => {
      if (t.exit_reason) set.add(t.exit_reason);
    });
    return Array.from(set).sort();
  }, [trades]);

  const dataFlags = useMemo(() => {
    const set = new Set();
    trades.forEach((t) => {
      if (t.data_flag) set.add(t.data_flag);
    });
    return Array.from(set).sort();
  }, [trades]);

  // Filter trades
  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      // Result filter
      if (filterResult === "win" && (t.net_pnl ?? 0) < 0) return false;
      if (filterResult === "loss" && (t.net_pnl ?? 0) >= 0) return false;

      // Reason filter
      if (selectedReason !== "any" && t.exit_reason !== selectedReason)
        return false;

      // Flag filter
      if (selectedFlag === "none" && t.data_flag) return false;
      if (
        selectedFlag !== "any" &&
        selectedFlag !== "none" &&
        t.data_flag !== selectedFlag
      )
        return false;

      // Date range filter
      if (fromDate && t.session_date < fromDate) return false;
      if (toDate && t.session_date > toDate) return false;

      return true;
    });
  }, [trades, filterResult, selectedReason, selectedFlag, fromDate, toDate]);

  // Sort descending by session date/trade id
  const sortedTrades = useMemo(() => {
    return [...filteredTrades].sort((a, b) => {
      if (a.session_date !== b.session_date) {
        return b.session_date.localeCompare(a.session_date);
      }
      return (b.trade_id ?? 0) - (a.trade_id ?? 0);
    });
  }, [filteredTrades]);

  // Counts for filter bar Seg
  const totalCount = trades.length;
  const winCount = trades.filter((t) => (t.net_pnl ?? 0) >= 0).length;
  const lossCount = totalCount - winCount;

  // Filter description for footer
  const filterDesc = useMemo(() => {
    const parts = [];
    if (filterResult !== "all") parts.push(filterResult);
    if (selectedReason !== "any") parts.push(selectedReason);
    if (selectedFlag !== "any") parts.push(`flag:${selectedFlag}`);
    if (fromDate || toDate) parts.push(`${fromDate || "start"}..${toDate || "end"}`);
    return parts.length > 0 ? parts.join(", ") : "all";
  }, [filterResult, selectedReason, selectedFlag, fromDate, toDate]);

  // Mutators for URL search params
  const updateParams = useCallback(
    (updates) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        Object.entries(updates).forEach(([k, v]) => {
          if (v === null || v === undefined || v === "" || v === "any" || (k === "page" && v === 1)) {
            next.delete(k);
          } else {
            next.set(k, String(v));
          }
        });
        return next;
      });
    },
    [setSearchParams]
  );

  const handleFilterResultChange = (res) => {
    updateParams({ result: res === "all" ? null : res, page: 1 });
  };

  const handleReasonChange = (reason) => {
    updateParams({ reason: reason === "any" ? null : reason, page: 1 });
  };

  const handleFlagChange = (flag) => {
    updateParams({ flag: flag === "any" ? null : flag, page: 1 });
  };

  const handleFromDateChange = (date) => {
    updateParams({ from: date || null, page: 1 });
  };

  const handleToDateChange = (date) => {
    updateParams({ to: date || null, page: 1 });
  };

  const handleToggleExpand = (tradeId) => {
    if (expandedTradeId === tradeId) {
      updateParams({ trade: null });
    } else {
      updateParams({ trade: tradeId });
    }
  };

  const handleExportCsv = () => {
    downloadCsv(sortedTrades, `${run?.id || "run"}_trades_filtered.csv`);
  };

  const pageSize = 50;
  const totalPages = Math.max(1, Math.ceil(sortedTrades.length / pageSize));
  const currentPage = Math.min(page, totalPages);

  const startIdx = (currentPage - 1) * pageSize;
  const endIdx = Math.min(currentPage * pageSize, sortedTrades.length);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {/* Filter Bar */}
      <TradesFilterBar
        totalCount={totalCount}
        winCount={winCount}
        lossCount={lossCount}
        filterResult={filterResult}
        onFilterResultChange={handleFilterResultChange}
        exitReasons={exitReasons}
        selectedReason={selectedReason}
        onReasonChange={handleReasonChange}
        dataFlags={dataFlags}
        selectedFlag={selectedFlag}
        onFlagChange={handleFlagChange}
        fromDate={fromDate}
        toDate={toDate}
        onFromDateChange={handleFromDateChange}
        onToDateChange={handleToDateChange}
        onExportCsv={handleExportCsv}
      />

      {/* Trades Table */}
      <TradesTable
        runId={run?.id}
        trades={trades}
        filteredTrades={sortedTrades}
        expandedTradeId={expandedTradeId}
        onToggleExpand={handleToggleExpand}
        page={currentPage}
        pageSize={pageSize}
        filterDesc={filterDesc}
      />

      {/* Pagination Controls */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
        className="muted"
      >
        <span style={{ fontSize: "12px" }}>
          Showing {sortedTrades.length > 0 ? startIdx + 1 : 0}&ndash;{endIdx} of{" "}
          {sortedTrades.length} &middot; newest first
        </span>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            className="btn btn--sm"
            disabled={currentPage <= 1}
            onClick={() => updateParams({ page: currentPage - 1 })}
          >
            Prev
          </button>
          <button
            type="button"
            className="btn btn--sm"
            disabled={currentPage >= totalPages}
            onClick={() => updateParams({ page: currentPage + 1 })}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
