import React from "react";
import { KpiStrip } from "../ui/KpiStrip.jsx";
import { inr, pct, ratio } from "../../lib/format.js";

export function OverviewKpis({ run }) {
  if (!run) return null;

  const m = run.metrics || {};
  const w = run.window || {};
  const numTrades = m.num_trades ?? 0;
  const hitRate = m.hit_rate;
  const isShort = Boolean(m.annualised_from_short_window);

  // Net P&L
  const netPnl = m.net_pnl;
  const totalReturn = m.total_return;
  const netPnlClass = netPnl == null ? "" : netPnl >= 0 ? "pos" : "neg";

  // CAGR years
  let yearsStr = "—";
  if (w.sessions) {
    yearsStr = `${(w.sessions / 252).toFixed(1)} yrs`;
  } else if (w.start && w.end) {
    const ms = new Date(w.end) - new Date(w.start);
    yearsStr = `${(ms / (365.25 * 86400000)).toFixed(1)} yrs`;
  }

  const cagrLabel = isShort ? (
    <span>
      CAGR{" "}
      <span className="accent" title="Annualised from a window under 252 sessions">
        ⚠
      </span>
    </span>
  ) : (
    "CAGR"
  );

  const cagrSub = isShort ? (
    <span className="accent">
      from {w.sessions ?? "—"} sessions · not comparable
    </span>
  ) : (
    `calendar · ${yearsStr}`
  );

  // Hit rate W / L
  let wlSub = "—";
  if (hitRate != null && numTrades > 0) {
    const wCount = Math.round(hitRate * numTrades);
    const lCount = numTrades - wCount;
    const expStr = inr(m.expectancy);
    wlSub = `${wCount} W · ${lCount} L · ${expStr} / trade`;
  }

  const items = [
    {
      label: "Net P&L",
      value: inr(netPnl, { signed: true }),
      className: netPnlClass,
      sub: `${pct(totalReturn)} on capital`,
    },
    {
      label: cagrLabel,
      value: pct(m.cagr),
      sub: cagrSub,
    },
    {
      label: "Sharpe",
      value: ratio(m.sharpe),
      sub: `Sortino ${ratio(m.sortino)} · daily, √252`,
    },
    {
      label: "Max drawdown",
      value: pct(m.max_drawdown),
      className: "neg",
      sub: `${m.max_drawdown_duration ?? "—"} sessions underwater`,
    },
    {
      label: "Profit factor",
      value: ratio(m.profit_factor),
      sub: `payoff ${ratio(m.payoff)}×`,
    },
    {
      label: "Hit rate",
      value: pct(hitRate, { signed: false }),
      sub: wlSub,
    },
  ];

  return <KpiStrip items={items} />;
}
