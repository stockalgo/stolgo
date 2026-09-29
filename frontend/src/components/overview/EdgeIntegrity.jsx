import React from "react";
import { Meter } from "../ui/Meter.jsx";
import { RangeBand } from "../ui/RangeBand.jsx";
import { KV } from "../ui/KV.jsx";
import { inr, pct, ratio } from "../../lib/format.js";
import { getAutoInsight } from "../../lib/verdict.js";

export function EdgeIntegrity({ run }) {
  if (!run) return null;

  const rob = run.robustness || {};
  const m = run.metrics || {};

  const resamples = (rob.resamples ?? 4000).toLocaleString();
  const seed = rob.seed ?? 7;

  // P(net > 0)
  const pNetPos = rob.p_net_positive;
  const pNetPosPct = pNetPos != null ? pct(pNetPos, { signed: false }) : "—";
  const meterVal = pNetPos != null ? Math.round(pNetPos * 100) : 0;

  // PF 90% band
  const pfLow = rob.pf_p05;
  const pfHigh = rob.pf_p95;
  const pfPoint = m.profit_factor;
  const pfBandStr =
    pfLow != null && pfHigh != null
      ? `${ratio(pfLow)} – ${ratio(pfHigh)}`
      : "—";

  const isBreakEvenInside =
    pfLow != null && pfHigh != null && pfLow <= 1.0 && pfHigh >= 1.0;
  const breakEvenNote =
    pfLow != null && pfHigh != null
      ? `break-even 1.0 ${isBreakEvenInside ? "inside band" : "outside band"}`
      : "—";

  // KV metrics
  const netNoTop5 = rob.net_without_top5;
  const netNoTop10 = rob.net_without_top10;
  const streak = rob.longest_losing_streak;

  const fees = m.fees ?? 0;
  const gross = m.gross_pnl ?? 0;
  const feeRatio = gross > 0 ? fees / gross : null;

  const worstDay = m.worst_day;

  // Auto-insight
  const insight = getAutoInsight(run);

  return (
    <aside
      className="panel"
      style={{ display: "flex", flexDirection: "column", gap: "14px", height: "100%" }}
    >
      <div>
        <div className="eyebrow">Edge integrity</div>
        <div className="faint" style={{ fontSize: "12px", marginTop: "4px" }}>
          Bootstrap of trade P&amp;L · {resamples} resamples · seed {seed}
        </div>
      </div>

      {/* Meter block */}
      <div>
        <div className="kv" style={{ padding: 0 }}>
          <span>P(net P&amp;L &gt; 0)</span>
          <span className="pos">{pNetPosPct}</span>
        </div>
        <div style={{ marginTop: "8px" }}>
          <Meter value={meterVal} max={100} intent={pNetPos >= 0.8 ? "pos" : "neg"} />
        </div>
      </div>

      {/* PF 90% band block */}
      <div>
        <div className="kv" style={{ padding: 0 }}>
          <span>Profit factor, 90% band</span>
          <span>{pfBandStr}</span>
        </div>
        <div style={{ marginTop: "4px" }}>
          <RangeBand
            p05={pfLow ?? 0}
            p95={pfHigh ?? 3}
            point={pfPoint ?? 1.0}
            min={0}
            max={Math.max(3, (pfHigh ?? 3) * 1.1)}
            breakEven={1.0}
            height={26}
          />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "11px",
            marginTop: "4px",
          }}
          className="faint"
        >
          <span>{breakEvenNote}</span>
          <span className="mono">point {ratio(pfPoint)}</span>
        </div>
      </div>

      {/* KV rows block */}
      <div style={{ borderTop: "1px solid var(--line)", paddingTop: "10px" }}>
        <KV
          label="Without best 5 trades"
          value={inr(netNoTop5, { signed: true })}
          className={netNoTop5 == null ? "" : netNoTop5 < 0 ? "neg" : "pos"}
        />
        <KV
          label="Without best 10 trades"
          value={inr(netNoTop10, { signed: true })}
          className={netNoTop10 == null ? "" : netNoTop10 < 0 ? "neg" : "pos"}
        />
        <KV
          label="Longest losing streak"
          value={streak != null ? `${streak} trades` : "—"}
        />
        <KV
          label="Fees ÷ gross profit"
          value={feeRatio != null ? pct(feeRatio, { signed: false }) : "—"}
          className={feeRatio != null && feeRatio > 0.4 ? "accent" : ""}
        />
        <KV
          label="Worst day"
          value={inr(worstDay, { signed: true })}
          className={worstDay == null ? "" : worstDay < 0 ? "neg" : "pos"}
        />
      </div>

      {/* Auto-insight callout */}
      {insight && (
        <div className="callout" style={{ marginTop: "auto" }}>
          {insight}
        </div>
      )}
    </aside>
  );
}
