import React, { useMemo } from "react";
import { useApi } from "../../hooks/useApi.js";
import { getTrade } from "../../api/endpoints.js";
import { SessionChart } from "../inspector/SessionChart.jsx";
import { inr, premium } from "../../lib/format.js";

function computeAutoNote(legs, trade) {
  if (!legs || legs.length === 0) return null;

  const sellLegs = legs.filter((l) => l.action === "SELL" || !l.action);

  // Rule 1: The losing leg is a SELL whose exit_premium >= 1.5 * entry_premium
  for (const leg of sellLegs) {
    if (
      leg.entry_premium != null &&
      leg.exit_premium != null &&
      leg.entry_premium > 0 &&
      leg.exit_premium >= 1.5 * leg.entry_premium
    ) {
      const strikeStr = leg.strike ? leg.strike.toLocaleString() : "strike";
      return `Spot moved toward the ${strikeStr} ${leg.option_type}: it went from ${premium(
        leg.entry_premium
      )} to ${premium(leg.exit_premium)}. The other short leg did not offset it.`;
    }
  }

  // Rule 2: Both SELL legs decayed and net > 0
  if (sellLegs.length >= 2 && (trade.net_pnl ?? 0) > 0) {
    const allDecayed = sellLegs.every(
      (l) =>
        l.entry_premium != null &&
        l.exit_premium != null &&
        l.exit_premium < l.entry_premium
    );
    if (allDecayed) {
      const totalCredit = sellLegs.reduce(
        (acc, l) => acc + (l.entry_premium ?? 0) * (l.qty ?? trade.qty ?? 1),
        0
      );
      let pct = 0;
      if (totalCredit > 0) {
        pct = Math.round(((trade.net_pnl ?? 0) / totalCredit) * 100);
      }
      return `Both short legs decayed. Kept ${pct}% of the credit.`;
    }
  }

  return null;
}

export function TradeRowDetail({ runId, trade }) {
  const tradeId = trade.trade_id;

  const fetchDetail = React.useCallback(() => {
    if (!runId || tradeId == null) return Promise.resolve(null);
    return getTrade(runId, tradeId);
  }, [runId, tradeId]);

  const { data: detail } = useApi(fetchDetail);

  const legs = detail?.legs || [];
  const autoNote = useMemo(() => computeAutoNote(legs, trade), [legs, trade]);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "420px minmax(0, 1fr)",
        gap: "16px",
        padding: "8px 0",
      }}
    >
      {/* Left Column: Legs table + auto note */}
      <div>
        <div className="eyebrow" style={{ marginBottom: "6px" }}>
          Legs
        </div>
        {legs.length > 0 ? (
          <table className="table" style={{ fontSize: "12px", width: "100%" }}>
            <thead>
              <tr>
                <th>Type</th>
                <th className="num">Strike</th>
                <th>Action</th>
                <th className="num">Entry ₹</th>
                <th className="num">Exit ₹</th>
                <th className="num">Leg P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {legs.map((leg, idx) => {
                let legPnl = leg.pnl;
                if (
                  legPnl == null &&
                  leg.entry_premium != null &&
                  leg.exit_premium != null
                ) {
                  const qty = leg.qty ?? trade.qty ?? 1;
                  legPnl =
                    leg.action === "BUY"
                      ? (leg.exit_premium - leg.entry_premium) * qty
                      : (leg.entry_premium - leg.exit_premium) * qty;
                }
                const isPos = (legPnl ?? 0) >= 0;

                return (
                  <tr key={idx}>
                    <td>{leg.option_type}</td>
                    <td className="num">
                      {leg.strike ? leg.strike.toLocaleString() : "—"}
                    </td>
                    <td>{leg.action || "—"}</td>
                    <td className="num">{premium(leg.entry_premium)}</td>
                    <td className="num">{premium(leg.exit_premium)}</td>
                    <td className={`num ${isPos ? "pos" : "neg"}`}>
                      {legPnl != null ? inr(legPnl, { signed: true }) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <div className="muted" style={{ padding: "12px 0", fontSize: "12px" }}>
            Legs not recorded for this run
          </div>
        )}

        {autoNote && (
          <div className="callout" style={{ marginTop: "10px" }}>
            {autoNote}
          </div>
        )}
      </div>

      {/* Right Column: Intraday Session Chart */}
      <div>
        <div className="eyebrow" style={{ marginBottom: "6px" }}>
          Session · 15m · entry/exit and strikes
        </div>
        <div
          style={{
            background: "#0d1013",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            overflow: "hidden",
          }}
        >
          <SessionChart tradeDetail={detail} width={760} height={200} />
        </div>
      </div>
    </div>
  );
}
