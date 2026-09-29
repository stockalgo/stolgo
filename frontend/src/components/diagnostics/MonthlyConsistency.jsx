import React from "react";
import { pct } from "../../lib/format.js";

export function MonthlyConsistency({ run, monthly = [] }) {
  const diag = run?.diagnostics || {};
  const mDiag = diag.monthly;

  let profitableMonths = mDiag?.profitable_months;
  let totalMonths = mDiag?.months;
  let meanPct = mDiag?.mean_monthly_pct;
  let medianPct = mDiag?.median_monthly_pct;

  if (mDiag == null && monthly && monthly.length > 0) {
    totalMonths = monthly.length;
    profitableMonths = monthly.filter((m) => (m.pnl ?? 0) > 0).length;
    const rets = monthly
      .map((m) => m.return_pct)
      .filter((v) => v !== null && v !== undefined)
      .sort((a, b) => a - b);
    if (rets.length > 0) {
      meanPct = rets.reduce((a, b) => a + b, 0) / rets.length;
      const mid = Math.floor(rets.length / 2);
      medianPct =
        rets.length % 2 !== 0 ? rets[mid] : (rets[mid - 1] + rets[mid]) / 2;
    }
  }

  const decisionCounts = diag.decision_counts;
  const hasDecisions =
    decisionCounts && Object.keys(decisionCounts).length > 0;

  const decisionList = hasDecisions
    ? Object.entries(decisionCounts)
        .map(([k, v]) => ({ label: k.replace(/_/g, " "), count: Number(v) }))
        .sort((a, b) => b.count - a.count)
    : [];

  const maxDecision = hasDecisions ? Math.max(...decisionList.map((d) => d.count), 1) : 1;

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="eyebrow">Monthly consistency</span>
      </div>

      <div className="kv kv--divided">
        <span>Profitable months</span>
        <span>
          {profitableMonths != null && totalMonths != null
            ? `${profitableMonths} / ${totalMonths}`
            : "—"}
        </span>
      </div>

      <div className="kv kv--divided">
        <span>Mean month</span>
        <span className={(meanPct ?? 0) >= 0 ? "pos" : "neg"}>
          {meanPct != null ? pct(meanPct, { dec: 2, signed: true }) : "—"}
        </span>
      </div>

      <div className="kv">
        <span>Median month</span>
        <span className={(medianPct ?? 0) >= 0 ? "pos" : "neg"}>
          {medianPct != null ? pct(medianPct, { dec: 2, signed: true }) : "—"}
        </span>
      </div>

      {/* Signal Funnel */}
      <div className="eyebrow" style={{ marginTop: "14px", marginBottom: "6px" }}>
        Signal funnel (S/R runs only)
      </div>

      {hasDecisions ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {decisionList.map((d) => (
            <div
              key={d.label}
              className="hbar"
              style={{ gridTemplateColumns: "110px minmax(0, 1fr) 50px" }}
            >
              <span
                className="mono"
                style={{ color: "var(--text-2)", fontSize: "11px" }}
              >
                {d.label}
              </span>
              <div className="hbar__track">
                <div
                  className="hbar__fill"
                  style={{
                    width: `${((d.count / maxDecision) * 100).toFixed(1)}%`,
                    background: "var(--text-3)",
                  }}
                />
              </div>
              <span className="num">{d.count}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="muted" style={{ fontSize: "12px" }}>
          Not recorded for this run. Shown when{" "}
          <span className="mono">diagnostics.decision_counts</span> exists.
        </div>
      )}
    </section>
  );
}
