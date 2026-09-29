import React, { useMemo } from "react";
import { inr } from "../../lib/format.js";

export function ExitReasons({ run, trades = [] }) {
  const diag = run?.diagnostics || {};
  const exitReasonsDict = diag.exit_reasons || {};

  const reasonStats = useMemo(() => {
    if (trades && trades.length > 0) {
      const map = new Map();
      trades.forEach((t) => {
        let r = t.exit_reason || "UNKNOWN";
        if (r === "DATA_EXIT" && t.data_flag) {
          r = `DATA · ${t.data_flag.replace("MISSING_", "")}`;
        }
        if (!map.has(r)) {
          map.set(r, { reason: r, count: 0, net: 0 });
        }
        const item = map.get(r);
        item.count += 1;
        item.net += t.net_pnl ?? 0;
      });
      return Array.from(map.values())
        .map((item) => ({
          ...item,
          perTrade: item.count > 0 ? item.net / item.count : 0,
        }))
        .sort((a, b) => b.count - a.count);
    }

    // Fallback to manifest diag.exit_reasons
    return Object.entries(exitReasonsDict)
      .map(([reason, count]) => ({
        reason,
        count,
        net: null,
        perTrade: null,
      }))
      .sort((a, b) => b.count - a.count);
  }, [trades, exitReasonsDict]);

  const totalTrades = reasonStats.reduce((acc, r) => acc + r.count, 0) || 1;

  const hasDataExits = reasonStats.some((r) => r.reason.startsWith("DATA"));

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="eyebrow">Exit reasons</span>
        {hasDataExits && (
          <span className="faint" style={{ fontSize: "11px" }}>
            DATA &middot; SPOT = MISSING_SPOT, DATA &middot; QUOTE = MISSING_HELD_QUOTE
          </span>
        )}
      </div>

      {/* Horizontal Bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {reasonStats.map((item) => {
          const isData = item.reason.startsWith("DATA");
          const pctVal = Math.round((item.count / totalTrades) * 100);
          const widthPct = ((item.count / totalTrades) * 100).toFixed(1);

          return (
            <div
              key={item.reason}
              className="hbar"
              style={{ gridTemplateColumns: "96px minmax(0, 1fr) 64px" }}
            >
              <span
                className="mono"
                style={{ color: "var(--text-2)", fontSize: "11px" }}
              >
                {item.reason}
              </span>
              <div className="hbar__track">
                <div
                  className="hbar__fill"
                  style={{
                    width: `${widthPct}%`,
                    background: isData ? "var(--accent)" : "var(--text-3)",
                  }}
                />
              </div>
              <span className="num">
                {item.count} &middot; {pctVal}%
              </span>
            </div>
          );
        })}
      </div>

      {/* Dense Table */}
      <table className="table table--dense" style={{ marginTop: "10px" }}>
        <thead>
          <tr>
            <th>Reason</th>
            <th className="num">Trades</th>
            <th className="num">Net</th>
            <th className="num">Per trade</th>
          </tr>
        </thead>
        <tbody>
          {reasonStats.map((item) => {
            const isPosNet = (item.net ?? 0) >= 0;
            const isPosPerTrade = (item.perTrade ?? 0) >= 0;

            return (
              <tr key={item.reason}>
                <td className="mono" style={{ fontSize: "12px" }}>
                  {item.reason}
                </td>
                <td className="num">{item.count}</td>
                <td className={`num ${isPosNet ? "pos" : "neg"}`}>
                  {item.net != null ? inr(item.net, { signed: true }) : "—"}
                </td>
                <td className={`num ${isPosPerTrade ? "pos" : "neg"}`}>
                  {item.perTrade != null
                    ? inr(item.perTrade, { signed: true })
                    : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
