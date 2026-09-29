import React from "react";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "../ui/StatusBadge.jsx";
import { marketColor } from "../../lib/colors.js";
import { pct, ratio, prob } from "../../lib/format.js";

export function RunsTable({
  runs = [],
  selectedIds = [],
  onToggleSelect,
  sortKey = "sharpe",
  sortDir = "desc",
  onSortChange,
  page = 1,
  pageSize = 25,
  onPageChange,
  onMaxSelectedNotice,
}) {
  const navigate = useNavigate();

  // Sorting columns
  const handleHeaderClick = (key) => {
    if (!onSortChange) return;
    if (sortKey === key) {
      onSortChange(key, sortDir === "desc" ? "asc" : "desc");
    } else {
      // Default to asc for 'name', desc for numeric metrics
      onSortChange(key, key === "name" ? "asc" : "desc");
    }
  };

  const getSortValue = (run, key) => {
    switch (key) {
      case "name":
        return (run.name || run.id || "").toLowerCase();
      case "trades":
        return run.metrics?.num_trades ?? -Infinity;
      case "return":
        return run.metrics?.total_return ?? -Infinity;
      case "cagr":
        return run.metrics?.cagr ?? -Infinity;
      case "sharpe":
        return run.metrics?.sharpe ?? -Infinity;
      case "max_dd":
        return run.metrics?.max_drawdown ?? -Infinity;
      case "pf":
        return run.metrics?.profit_factor ?? -Infinity;
      case "p_positive":
        return run.robustness?.p_net_positive ?? -Infinity;
      default:
        return 0;
    }
  };

  const sortedRuns = [...runs].sort((a, b) => {
    const valA = getSortValue(a, sortKey);
    const valB = getSortValue(b, sortKey);

    if (valA === valB) return 0;
    if (valA === -Infinity) return 1;
    if (valB === -Infinity) return -1;

    let res = 0;
    if (typeof valA === "string") {
      res = valA.localeCompare(valB);
    } else {
      res = valA < valB ? -1 : 1;
    }
    return sortDir === "desc" ? -res : res;
  });

  const total = sortedRuns.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(Math.max(1, page), totalPages);
  const startIdx = (currentPage - 1) * pageSize;
  const pagedRuns = sortedRuns.slice(startIdx, startIdx + pageSize);

  const startNum = total === 0 ? 0 : startIdx + 1;
  const endNum = Math.min(startIdx + pageSize, total);

  const sortLabels = {
    name: "Run",
    trades: "Trades",
    return: "Return",
    cagr: "CAGR",
    sharpe: "Sharpe",
    max_dd: "Max DD",
    pf: "PF",
    p_positive: "P(>0)",
  };

  const sortArrow = sortDir === "desc" ? "↓" : "↑";

  const renderSortableTh = (key, label, className = "num", title = undefined) => {
    const isSorted = sortKey === key;
    return (
      <th
        className={className}
        title={title}
        aria-sort={isSorted ? (sortDir === "desc" ? "descending" : "ascending") : undefined}
        onClick={() => handleHeaderClick(key)}
        style={{ cursor: "pointer", userSelect: "none" }}
      >
        {label}
        {isSorted && <span style={{ marginLeft: "4px" }}>{sortArrow}</span>}
      </th>
    );
  };

  return (
    <div>
      <div className="table-wrap">
        <table className="table table--dense">
          <thead>
            <tr>
              <th style={{ width: "34px" }}></th>
              {renderSortableTh("name", "Run", "")}
              <th>Market · DTE</th>
              <th>Status</th>
              {renderSortableTh("trades", "Trades")}
              {renderSortableTh("return", "Return")}
              {renderSortableTh("cagr", "CAGR")}
              {renderSortableTh("sharpe", "Sharpe")}
              {renderSortableTh("max_dd", "Max DD")}
              {renderSortableTh("pf", "PF")}
              {renderSortableTh(
                "p_positive",
                "P(>0)",
                "num",
                "Bootstrap probability that net P&L is positive"
              )}
            </tr>
          </thead>
          <tbody>
            {pagedRuns.map((run) => {
              const isSelected = selectedIds.includes(run.id);
              const numTrades = run.metrics?.num_trades ?? 0;
              const isLowTrades = numTrades < 100;
              const dotColor = marketColor(run.markets, run.dte);
              const marketStr = (run.markets || []).join("+");
              const dteStr = (run.dte || []).join(",") + "D";
              const retVal = run.metrics?.total_return;
              const retClass = retVal == null ? "num" : retVal >= 0 ? "num pos" : "num neg";
              const maxDdVal = run.metrics?.max_drawdown;
              const maxDdClass = maxDdVal == null ? "num" : "num neg";
              const isShortWindow = Boolean(run.metrics?.annualised_from_short_window);

              // Group label / chip
              const groupLabel = run.group?.label || (run.group?.id ? run.group.id.replace(/-/g, " ") : null);

              return (
                <tr
                  key={run.id}
                  aria-selected={isSelected ? "true" : undefined}
                  style={{
                    opacity: isLowTrades ? 0.78 : 1,
                    cursor: "pointer",
                  }}
                  onClick={() => navigate(`/runs/${run.id}`)}
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      aria-label={`Select ${run.name || run.id}`}
                      checked={isSelected}
                      style={{ accentColor: "var(--accent)" }}
                      onChange={() => {
                        if (!isSelected && selectedIds.length >= 4) {
                          if (onMaxSelectedNotice) {
                            onMaxSelectedNotice();
                          }
                          return;
                        }
                        if (onToggleSelect) {
                          onToggleSelect(run.id);
                        }
                      }}
                    />
                  </td>
                  <td>
                    <div style={{ maxWidth: "300px", overflow: "hidden" }}>
                      <div
                        className="name"
                        style={{ display: "flex", alignItems: "center", maxWidth: "300px" }}
                      >
                        <span
                          style={{
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                          title={run.name || run.id}
                        >
                          {run.name || run.id}
                        </span>
                        {groupLabel && (
                          <span
                            className="chip"
                            style={{
                              height: "18px",
                              fontSize: "10.5px",
                              marginLeft: "6px",
                              flexShrink: 0,
                            }}
                          >
                            {groupLabel}
                          </span>
                        )}
                      </div>
                      <span
                        className="sub"
                        style={{
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          display: "block",
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                        }}
                      >
                        {run.id}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        fontSize: "12px",
                        color: "var(--text-2)",
                      }}
                    >
                      <span
                        style={{
                          width: "8px",
                          height: "8px",
                          borderRadius: "50%",
                          background: dotColor,
                          flexShrink: 0,
                        }}
                      />
                      {marketStr ? `${marketStr} · ${dteStr}` : "—"}
                    </span>
                  </td>
                  <td>
                    <StatusBadge
                      status={run.status}
                      reasons={run.status_reasons}
                    />
                  </td>
                  <td className="num">{numTrades}</td>
                  <td className={retClass}>{pct(retVal)}</td>
                  <td className="num">
                    {pct(run.metrics?.cagr)}
                    {isShortWindow && (
                      <>
                        {" "}
                        <span
                          className="accent"
                          title="Annualised from a window under 252 sessions"
                          style={{ cursor: "help" }}
                        >
                          ⚠
                        </span>
                      </>
                    )}
                  </td>
                  <td className="num" style={{ color: "var(--text-1)", fontWeight: 500 }}>
                    {ratio(run.metrics?.sharpe)}
                  </td>
                  <td className={maxDdClass}>{pct(maxDdVal)}</td>
                  <td className="num">{ratio(run.metrics?.profit_factor)}</td>
                  <td className="num">
                    {prob(run.robustness?.p_net_positive)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "8px",
        }}
        className="muted"
      >
        <span style={{ fontSize: "12px" }}>
          Showing {startNum}–{endNum} of {total} · sorted by {sortLabels[sortKey] || sortKey}{" "}
          {sortArrow}
        </span>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            className="btn btn--sm"
            disabled={currentPage <= 1}
            onClick={() => onPageChange && onPageChange(currentPage - 1)}
          >
            Prev
          </button>
          <button
            className="btn btn--sm"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange && onPageChange(currentPage + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
