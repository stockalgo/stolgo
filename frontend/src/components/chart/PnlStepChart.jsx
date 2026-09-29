import React, { useMemo } from "react";
import { inr } from "../../lib/format.js";

export function PnlStepChart({ trades = [], visibleRange = null }) {
  const { polylinePoints, zeroY, endSum, endLabelClass } = useMemo(() => {
    // Filter trades in visible time range if specified
    let filtered = trades;
    if (visibleRange && visibleRange.from && visibleRange.to) {
      filtered = trades.filter((t) => {
        if (!t.session_date) return true;
        const sTime = new Date(t.session_date).getTime() / 1000;
        return sTime >= visibleRange.from && sTime <= visibleRange.to;
      });
    }

    if (filtered.length === 0) {
      return { polylinePoints: "", zeroY: 27, endSum: 0, endLabelClass: "faint" };
    }

    // Sort chronologically
    const sorted = [...filtered].sort((a, b) => {
      const ta = a.session_date || a.entry_ts || 0;
      const tb = b.session_date || b.entry_ts || 0;
      return ta < tb ? -1 : 1;
    });

    let running = 0;
    const series = [];
    for (const t of sorted) {
      running += t.net_pnl || 0;
      series.push(running);
    }

    const minVal = Math.min(0, ...series);
    const maxVal = Math.max(0, ...series);
    const valRange = maxVal - minVal || 1;

    // Scale Y into [46, 8] (inverted SVG: 8 is top, 46 is bottom)
    const getY = (val) => 46 - ((val - minVal) / valRange) * 38;
    const zeroLineY = getY(0);

    // Scale X into [0, 880]
    const xStep = 880 / Math.max(1, series.length - 1);

    const pts = [];
    for (let i = 0; i < series.length; i++) {
      const curX = i * xStep;
      const curY = getY(series[i]);
      if (i === 0) {
        pts.push(`0,${zeroLineY.toFixed(1)}`);
        pts.push(`0,${curY.toFixed(1)}`);
      } else {
        const prevX = (i - 1) * xStep;
        pts.push(`${curX.toFixed(1)},${getY(series[i - 1]).toFixed(1)}`);
        pts.push(`${curX.toFixed(1)},${curY.toFixed(1)}`);
      }
    }

    const finalSum = series[series.length - 1];
    const lblClass = finalSum >= 0 ? "pos" : "neg";

    return {
      polylinePoints: pts.join(" "),
      zeroY: zeroLineY,
      endSum: finalSum,
      endLabelClass: lblClass,
    };
  }, [trades, visibleRange]);

  const strokeColor = endSum >= 0 ? "var(--pos, #3ddc97)" : "var(--neg, #e5484d)";

  return (
    <div>
      {/* Legend row */}
      <div
        className="mono"
        style={{
          display: "flex",
          gap: "14px",
          fontSize: "11px",
          color: "var(--text-faint)",
          margin: "6px 0 2px",
        }}
      >
        <span>STRATEGY P&amp;L · SAME WINDOW</span>
        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: "var(--pos, #3ddc97)",
            }}
          />
          winning expiry
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: "var(--neg, #e5484d)",
            }}
          />
          losing expiry · click to inspect
        </span>
      </div>

      {/* 54px Step Chart */}
      <svg viewBox="0 0 940 54" width="100%" height="54" style={{ display: "block" }}>
        {/* Zero baseline */}
        <line x1="0" x2="880" y1={zeroY} y2={zeroY} stroke="var(--line, #22272d)" />

        {/* Step polyline */}
        {polylinePoints && (
          <polyline
            points={polylinePoints}
            fill="none"
            stroke={strokeColor}
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        )}

        {/* End sum readout */}
        <text
          x="936"
          y={Math.max(12, Math.min(48, zeroY - 14))}
          textAnchor="end"
          fill={strokeColor}
          fontSize="10"
          fontFamily="var(--font-mono, IBM Plex Mono)"
          fontWeight="500"
        >
          {inr(endSum, { signed: true })}
        </text>
      </svg>
    </div>
  );
}
