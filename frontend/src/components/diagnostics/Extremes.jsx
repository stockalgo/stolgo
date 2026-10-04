import React from "react";
import { inr, pct } from "../../lib/format.js";

export function Extremes({ run }) {
  const diag = run?.diagnostics || {};
  const ext = diag.extremes || {};
  const metrics = run?.metrics || {};

  const best = ext.best_trade ?? ext.best_expiry;
  const worst = ext.worst_trade ?? ext.worst_expiry;
  const worstMtm = ext.worst_mtm;
  const maxOvershoot = ext.max_stop_overshoot;
  const es95 = ext.expected_shortfall_95 ?? ext.es_95 ?? metrics.cvar_95;
  const maxDd = ext.intraday_max_drawdown ?? metrics.max_drawdown;

  const rows = [];
  if (best != null) {
    rows.push({
      label: "Best expiry",
      value: inr(best, { signed: true }),
      className: "pos",
    });
  }
  if (worst != null) {
    rows.push({
      label: "Worst expiry",
      value: inr(worst, { signed: true }),
      className: "neg",
    });
  }
  if (worstMtm != null) {
    rows.push({
      label: "Worst intraday MTM",
      value: inr(worstMtm, { signed: true }),
      className: "neg",
    });
  }
  if (maxOvershoot != null) {
    rows.push({
      label: "Max stop overshoot",
      value: inr(maxOvershoot),
      className: "accent",
    });
  }
  if (es95 != null) {
    rows.push({
      label: "Expected shortfall 95%",
      value: inr(es95, { signed: true }),
      className: "neg",
    });
  }
  if (maxDd != null) {
    rows.push({
      label: "Intraday max drawdown",
      value: pct(maxDd, { signed: true }),
      className: "neg",
    });
  }

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="eyebrow">Tail risk &amp; extremes</span>
      </div>

      {rows.length === 0 ? (
        <div className="muted" style={{ padding: "12px 0", fontSize: "12px" }}>
          No extremes recorded for this run
        </div>
      ) : (
        rows.map((row, idx) => (
          <div
            key={row.label}
            className={`kv ${idx < rows.length - 1 ? "kv--divided" : ""}`}
          >
            <span>{row.label}</span>
            <span className={row.className}>{row.value}</span>
          </div>
        ))
      )}
    </section>
  );
}
