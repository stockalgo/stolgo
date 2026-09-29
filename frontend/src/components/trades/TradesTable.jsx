import React, { useEffect, useRef } from "react";
import { TradesFooter } from "./TradesFooter.jsx";
import { TradeRowDetail } from "./TradeRowDetail.jsx";
import { inr, premium, level, timeIST, rmult } from "../../lib/format.js";

function structureLabel(str) {
  if (!str) return "—";
  return str
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function TradesTable({
  runId,
  trades = [],
  filteredTrades = [],
  expandedTradeId = null,
  onToggleExpand,
  page = 1,
  pageSize = 50,
  filterDesc = "all",
}) {
  const expandedRowRef = useRef(null);

  // Scroll expanded row into view when expandedTradeId changes
  useEffect(() => {
    if (expandedTradeId && expandedRowRef.current) {
      expandedRowRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [expandedTradeId]);

  const startIndex = (page - 1) * pageSize;
  const pageTrades = filteredTrades.slice(startIndex, startIndex + pageSize);

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th style={{ width: "36px" }} />
            <th>#</th>
            <th aria-sort="descending">Session</th>
            <th>Structure · legs</th>
            <th className="num">Underlying</th>
            <th className="num">Premium</th>
            <th className="num">Qty</th>
            <th className="num">Gross</th>
            <th className="num">Fees</th>
            <th className="num">Slippage</th>
            <th className="num">Net</th>
            <th className="num">R</th>
            <th>Exit</th>
            <th>Flag</th>
          </tr>
        </thead>
        <tbody>
          {pageTrades.length === 0 ? (
            <tr>
              <td colSpan="14" style={{ textAlign: "center", padding: "32px" }}>
                <span className="muted">No trades match the current filters</span>
              </td>
            </tr>
          ) : (
            pageTrades.map((t) => {
              const isExpanded = t.trade_id === expandedTradeId;
              const isWin = (t.net_pnl ?? 0) >= 0;
              const isGrossWin = (t.gross_pnl ?? 0) >= 0;

              return (
                <React.Fragment key={t.trade_id}>
                  <tr
                    id={`trade-row-${t.trade_id}`}
                    ref={isExpanded ? expandedRowRef : null}
                    aria-selected={isExpanded}
                  >
                    <td>
                      <button
                        type="button"
                        className="btn btn--ghost icon-btn"
                        aria-label={isExpanded ? "Collapse row" : "Expand row"}
                        aria-expanded={isExpanded}
                        style={{ height: "24px", width: "24px" }}
                        onClick={() => onToggleExpand?.(t.trade_id)}
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
                          {isExpanded ? (
                            <polyline points="6 9 12 15 18 9" />
                          ) : (
                            <polyline points="9 6 15 12 9 18" />
                          )}
                        </svg>
                      </button>
                    </td>
                    <td className="num" style={{ textAlign: "left" }}>
                      {t.trade_id}
                    </td>
                    <td className="mono">
                      {t.session_date}
                      <span className="sub">
                        {t.entry_ts ? timeIST(t.entry_ts) : "—"} &rarr;{" "}
                        {t.exit_ts ? timeIST(t.exit_ts) : "—"} IST
                      </span>
                    </td>
                    <td>
                      <span className="chip">{structureLabel(t.structure)}</span>
                      {t.legs_label && (
                        <span className="sub" style={{ marginTop: "2px" }}>
                          {t.legs_label}
                        </span>
                      )}
                    </td>
                    <td className="num">
                      {t.underlying_entry != null ? level(t.underlying_entry) : "—"}
                      <span className="sub">
                        &rarr; {t.underlying_exit != null ? level(t.underlying_exit) : "—"}
                      </span>
                    </td>
                    <td className="num">
                      {t.premium_entry != null ? premium(t.premium_entry) : "—"}
                      <span className="sub">
                        &rarr; {t.premium_exit != null ? premium(t.premium_exit) : "—"}
                      </span>
                    </td>
                    <td className="num">
                      {t.qty}
                      {t.lots != null && (
                        <span className="sub">
                          {t.lots} {t.lots === 1 ? "lot" : "lots"}
                        </span>
                      )}
                    </td>
                    <td className={`num ${isGrossWin ? "pos" : "neg"}`}>
                      {t.gross_pnl != null ? inr(t.gross_pnl, { signed: true }) : "—"}
                    </td>
                    <td className="num muted">
                      {t.fees != null ? inr(t.fees) : "—"}
                    </td>
                    <td className="num faint">
                      {t.slippage != null ? inr(t.slippage) : "—"}
                    </td>
                    <td className={`num ${isWin ? "pos" : "neg"}`}>
                      {t.net_pnl != null ? inr(t.net_pnl, { signed: true }) : "—"}
                    </td>
                    <td className="num">
                      {t.r_multiple != null
                        ? t.r_multiple >= 0
                          ? `+${Number(t.r_multiple).toFixed(2)}`
                          : Number(t.r_multiple).toFixed(2)
                        : "—"}
                    </td>
                    <td>
                      <span
                        className={
                          t.exit_reason === "DATA_EXIT"
                            ? "badge badge--warn"
                            : "badge badge--muted"
                        }
                      >
                        {t.exit_reason || "—"}
                      </span>
                    </td>
                    <td>
                      {t.data_flag ? (
                        <span className="badge badge--warn">{t.data_flag}</span>
                      ) : null}
                    </td>
                  </tr>

                  {/* Expanded Row Detail */}
                  {isExpanded && (
                    <tr className="row-expanded">
                      <td />
                      <td colSpan="13">
                        <TradeRowDetail runId={runId} trade={t} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })
          )}
        </tbody>

        {/* Sticky Reconciling Footer */}
        <TradesFooter trades={filteredTrades} filterDesc={filterDesc} />
      </table>
    </div>
  );
}
