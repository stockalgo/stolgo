import React, { useMemo } from "react";
import { inr, pct } from "../../lib/format.js";

export function Stability({ run, trades = [] }) {
  const diag = run?.diagnostics || {};
  const manifestStability = diag.stability;

  const stabilityData = useMemo(() => {
    if (manifestStability?.early && manifestStability?.recent) {
      return manifestStability;
    }

    if (trades && trades.length >= 2) {
      // Sort chronologically
      const sorted = [...trades].sort((a, b) =>
        (a.session_date || "").localeCompare(b.session_date || "")
      );
      const mid = Math.ceil(sorted.length / 2);
      const earlyTrades = sorted.slice(0, mid);
      const recentTrades = sorted.slice(mid);

      const calcHalf = (half) => {
        const net = half.reduce((acc, t) => acc + (t.net_pnl ?? 0), 0);
        const wins = half.filter((t) => (t.net_pnl ?? 0) >= 0).length;
        const hit = half.length > 0 ? wins / half.length : 0;
        const start = half[0]?.session_date || "";
        const end = half[half.length - 1]?.session_date || "";
        return { trades: half.length, net_pnl: net, hit_rate: hit, start, end };
      };

      return {
        early: calcHalf(earlyTrades),
        recent: calcHalf(recentTrades),
      };
    }

    return null;
  }, [manifestStability, trades]);

  if (!stabilityData) {
    return (
      <section className="panel">
        <div className="panel__head">
          <span className="eyebrow">Stability &middot; early vs recent</span>
        </div>
        <div className="muted" style={{ padding: "12px 0", fontSize: "12px" }}>
          Insufficient trades to evaluate stability
        </div>
      </section>
    );
  }

  const { early, recent } = stabilityData;
  const earlyNet = early?.net_pnl ?? 0;
  const recentNet = recent?.net_pnl ?? 0;

  const isEarlyPos = earlyNet >= 0;
  const isRecentPos = recentNet >= 0;

  let calloutText = "";
  if (isEarlyPos && isRecentPos) {
    calloutText =
      "Both halves are profitable with similar hit rates, so the edge is not concentrated in one period.";
  } else if (isEarlyPos && !isRecentPos) {
    calloutText =
      "Only the early half is profitable. The edge may be period-specific.";
  } else if (!isEarlyPos && isRecentPos) {
    calloutText =
      "Only the recent half is profitable. The edge may be period-specific.";
  } else {
    calloutText = "Neither half is profitable.";
  }

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="eyebrow">Stability &middot; early vs recent</span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: "10px",
        }}
      >
        {/* Early half box */}
        <div
          style={{
            padding: "12px",
            borderRadius: "8px",
            background: "var(--bg-raised)",
          }}
        >
          <div className="eyebrow">Early half &middot; {early?.trades} trades</div>
          <div
            className={`mono ${isEarlyPos ? "pos" : "neg"}`}
            style={{ fontSize: "20px", marginTop: "6px" }}
          >
            {inr(earlyNet, { signed: true })}
          </div>
          <div className="muted" style={{ fontSize: "12px" }}>
            hit {early?.hit_rate != null ? pct(early.hit_rate, { signed: false }) : "—"} &middot;{" "}
            {early?.start} &rarr; {early?.end}
          </div>
        </div>

        {/* Recent half box */}
        <div
          style={{
            padding: "12px",
            borderRadius: "8px",
            background: "var(--bg-raised)",
          }}
        >
          <div className="eyebrow">Recent half &middot; {recent?.trades} trades</div>
          <div
            className={`mono ${isRecentPos ? "pos" : "neg"}`}
            style={{ fontSize: "20px", marginTop: "6px" }}
          >
            {inr(recentNet, { signed: true })}
          </div>
          <div className="muted" style={{ fontSize: "12px" }}>
            hit {recent?.hit_rate != null ? pct(recent.hit_rate, { signed: false }) : "—"} &middot;{" "}
            {recent?.start} &rarr; {recent?.end}
          </div>
        </div>
      </div>

      <div className="callout" style={{ marginTop: "10px" }}>
        {calloutText}
      </div>
    </section>
  );
}
