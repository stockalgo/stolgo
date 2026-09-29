import React, { useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../../hooks/useApi.js";
import { getTrade } from "../../api/endpoints.js";
import { SessionChart } from "./SessionChart.jsx";
import { inr, rmult, premium, sessionShort } from "../../lib/format.js";

export function TradeInspector({
  runId,
  trades = [],
  selectedTradeId = null,
  onSelectTrade = null,
}) {
  // Determine current trade
  const currentTrade =
    trades.find((t) => t.trade_id === selectedTradeId) ||
    (trades.length > 0 ? trades[trades.length - 1] : null);
  const currentTradeId = currentTrade?.trade_id;

  // Last 6 trades for the top button strip
  const lastSix = trades.slice(-6);

  // Fetch full trade detail (bars, legs, trade)
  const fetchTradeDetail = useCallback(() => {
    if (!runId || !currentTradeId) return Promise.resolve(null);
    return getTrade(runId, currentTradeId);
  }, [runId, currentTradeId]);

  const { data: tradeDetail } = useApi(fetchTradeDetail);

  // Global [ and ] keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        document.activeElement?.isContentEditable
      ) {
        return;
      }
      if (e.key === "[") {
        e.preventDefault();
        if (!trades || trades.length === 0) return;
        const idx = trades.findIndex((t) => t.trade_id === currentTradeId);
        if (idx > 0) {
          onSelectTrade?.(trades[idx - 1].trade_id);
        }
      } else if (e.key === "]") {
        e.preventDefault();
        if (!trades || trades.length === 0) return;
        const idx = trades.findIndex((t) => t.trade_id === currentTradeId);
        if (idx >= 0 && idx < trades.length - 1) {
          onSelectTrade?.(trades[idx + 1].trade_id);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [trades, currentTradeId, onSelectTrade]);

  if (!trades || trades.length === 0) {
    return (
      <section
        className="panel"
        style={{ display: "flex", flexDirection: "column", gap: "8px" }}
      >
        <div className="panel__head" style={{ margin: 0 }}>
          <span className="eyebrow">Trade inspector</span>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: 1,
            minHeight: "220px",
          }}
          className="muted"
        >
          No trades recorded
        </div>
      </section>
    );
  }

  const legs = tradeDetail?.legs || [];
  const hasLegs = legs.length > 0;
  const ceLeg =
    legs.find((l) => l.option_type === "CE" && (l.action === "SELL" || !l.action)) ||
    legs.find((l) => l.option_type === "CE");
  const peLeg =
    legs.find((l) => l.option_type === "PE" && (l.action === "SELL" || !l.action)) ||
    legs.find((l) => l.option_type === "PE");

  const tradeInfo = tradeDetail?.trade || currentTrade || {};
  const fees = tradeInfo.fees;
  const slippage = tradeInfo.slippage;
  const netPnl = tradeInfo.net_pnl;
  const rMultiple = tradeInfo.r_multiple;

  return (
    <section
      className="panel"
      style={{ display: "flex", flexDirection: "column", gap: "8px" }}
    >
      <div className="panel__head" style={{ margin: 0 }}>
        <span className="eyebrow">
          Trade inspector · #{currentTradeId} · 15m
        </span>
        <Link
          to={`/runs/${encodeURIComponent(runId)}/trades?trade=${currentTradeId}`}
          style={{ fontSize: "11px" }}
        >
          Open in Trades &rarr;
        </Link>
      </div>

      {/* Last 6 trades button strip */}
      <div style={{ display: "flex", gap: "4px" }}>
        {lastSix.map((t) => {
          const isSelected = t.trade_id === currentTradeId;
          const isWin = (t.net_pnl ?? 0) >= 0;
          return (
            <button
              key={t.trade_id}
              type="button"
              className="btn btn--sm mono"
              aria-pressed={isSelected}
              style={{
                flex: 1,
                height: "40px",
                flexDirection: "column",
                gap: 0,
                justifyContent: "center",
                background: isSelected ? "var(--bg-active)" : "transparent",
                borderColor: isSelected ? "var(--line-strong)" : "var(--line)",
              }}
              onClick={() => onSelectTrade?.(t.trade_id)}
            >
              <span style={{ fontSize: "11px", color: "var(--text-2)" }}>
                {sessionShort(t.session_date)}
              </span>
              <span
                style={{ fontSize: "11px" }}
                className={isWin ? "pos" : "neg"}
              >
                {inr(t.net_pnl, { signed: true })}
              </span>
            </button>
          );
        })}
      </div>

      {/* Intraday 15m session chart */}
      <SessionChart tradeDetail={tradeDetail} />

      {/* Footer 4 columns */}
      <div
        className="mono"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
          gap: "8px",
          fontSize: "11px",
          borderTop: "1px solid var(--line)",
          paddingTop: "8px",
        }}
      >
        {hasLegs ? (
          <>
            <div>
              <div className="faint">SHORT CE</div>
              <div style={{ marginTop: "2px" }}>
                {ceLeg?.strike
                  ? `${ceLeg.strike.toLocaleString()} · ${premium(ceLeg.entry_premium)}→${premium(ceLeg.exit_premium)}`
                  : "—"}
              </div>
            </div>
            <div>
              <div className="faint">SHORT PE</div>
              <div style={{ marginTop: "2px" }}>
                {peLeg?.strike
                  ? `${peLeg.strike.toLocaleString()} · ${premium(peLeg.entry_premium)}→${premium(peLeg.exit_premium)}`
                  : "—"}
              </div>
            </div>
          </>
        ) : (
          <div style={{ gridColumn: "span 2" }}>
            <div className="faint">LEGS</div>
            <div style={{ marginTop: "2px" }} className="muted">
              Legs not recorded for this run
            </div>
          </div>
        )}

        <div>
          <div className="faint">FEES · SLIPPAGE</div>
          <div style={{ marginTop: "2px" }}>
            {inr(fees)} · {slippage != null ? inr(slippage) : "—"}
          </div>
        </div>

        <div>
          <div className="faint">NET</div>
          <div
            className={(netPnl ?? 0) >= 0 ? "pos" : "neg"}
            style={{ marginTop: "2px" }}
          >
            {inr(netPnl, { signed: true })} · {rmult(rMultiple)}
          </div>
        </div>
      </div>
    </section>
  );
}
