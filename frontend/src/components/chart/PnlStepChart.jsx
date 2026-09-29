import React, { useMemo } from "react";
import { inr } from "../../lib/format.js";

const dtf = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" });

export function PnlStepChart({
  trades = [],
  candles = [],
  visibleRange = null,
  timeToCoordinate = null,
  timeScaleWidth = 880,
}) {
  const { polylinePoints, zeroY, endSum, endLabelClass, plotWidth, totalWidth } = useMemo(() => {
    const plotW = Math.max(100, timeScaleWidth || 880);
    const totalW = plotW + 60;

    if (!trades || trades.length === 0) {
      return {
        polylinePoints: `0,27 ${plotW},27`,
        zeroY: 27,
        endSum: 0,
        endLabelClass: "faint",
        plotWidth: plotW,
        totalWidth: totalW,
      };
    }

    // 1. Group trade net_pnl by session_date
    const pnlByDate = {};
    for (const t of trades) {
      if (t.session_date) {
        pnlByDate[t.session_date] = (pnlByDate[t.session_date] || 0) + (t.net_pnl || 0);
      }
    }

    // 2. Prepare series of sessions
    // If candles are provided, use candle sessions for date alignment
    let sessionPoints = [];
    if (candles && candles.length > 0) {
      const sortedCandles = [...candles]
        .filter((c) => c && c.time)
        .sort((a, b) => a.time - b.time);

      let running = 0;
      for (const c of sortedCandles) {
        let dateStr = "";
        try {
          dateStr = dtf.format(new Date(c.time * 1000));
        } catch {
          dateStr = new Date(c.time * 1000).toISOString().slice(0, 10);
        }
        const dayPnl = pnlByDate[dateStr] || 0;
        running += dayPnl;
        sessionPoints.push({
          time: c.time,
          sessionDate: dateStr,
          cumPnl: running,
        });
      }
    } else {
      // Fallback if no candles: sort trades by date/entry_ts
      const sortedTrades = [...trades].sort((a, b) => {
        const ta = a.session_date || a.entry_ts || 0;
        const tb = b.session_date || b.entry_ts || 0;
        return ta < tb ? -1 : 1;
      });
      let running = 0;
      for (const t of sortedTrades) {
        running += t.net_pnl || 0;
        sessionPoints.push({
          time: t.entry_ts || (t.session_date ? new Date(t.session_date).getTime() / 1000 : null),
          sessionDate: t.session_date || "",
          cumPnl: running,
        });
      }
    }

    if (sessionPoints.length === 0) {
      return {
        polylinePoints: `0,27 ${plotW},27`,
        zeroY: 27,
        endSum: 0,
        endLabelClass: "faint",
        plotWidth: plotW,
        totalWidth: totalW,
      };
    }

    const cumValues = sessionPoints.map((s) => s.cumPnl);
    const minVal = Math.min(0, ...cumValues);
    const maxVal = Math.max(0, ...cumValues);
    const valRange = maxVal - minVal || 1;

    // Scale Y into [46, 8] (inverted SVG: 8 is top, 46 is bottom)
    const getY = (val) => 46 - ((val - minVal) / valRange) * 38;
    const zeroLineY = getY(0);

    const pts = [];
    const n = sessionPoints.length;
    let prevX = null;
    let prevY = zeroLineY;

    for (let i = 0; i < n; i++) {
      const sp = sessionPoints[i];
      let curX = null;
      if (typeof timeToCoordinate === "function" && sp.time) {
        curX = timeToCoordinate(sp.time);
      }
      if (curX === null || isNaN(curX)) {
        curX = (i / Math.max(1, n - 1)) * plotW;
      }
      const curY = getY(sp.cumPnl);

      if (i === 0) {
        if (curX > 0) {
          pts.push(`0,${zeroLineY.toFixed(1)}`);
        }
        pts.push(`${curX.toFixed(1)},${zeroLineY.toFixed(1)}`);
        if (curY !== zeroLineY) {
          pts.push(`${curX.toFixed(1)},${curY.toFixed(1)}`);
        }
      } else {
        pts.push(`${curX.toFixed(1)},${prevY.toFixed(1)}`);
        if (curY !== prevY) {
          pts.push(`${curX.toFixed(1)},${curY.toFixed(1)}`);
        }
      }
      prevX = curX;
      prevY = curY;
    }

    if (prevX !== null && prevX < plotW) {
      pts.push(`${plotW.toFixed(1)},${prevY.toFixed(1)}`);
    }

    const finalSum = sessionPoints[sessionPoints.length - 1].cumPnl;
    const lblClass = finalSum >= 0 ? "pos" : "neg";

    return {
      polylinePoints: pts.join(" "),
      zeroY: zeroLineY,
      endSum: finalSum,
      endLabelClass: lblClass,
      plotWidth: plotW,
      totalWidth: totalW,
    };
  }, [trades, candles, timeToCoordinate, timeScaleWidth]);

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
      <svg viewBox={`0 0 ${totalWidth} 54`} width="100%" height="54" style={{ display: "block", overflow: "hidden" }}>
        {/* Zero baseline */}
        <line x1="0" x2={plotWidth} y1={zeroY} y2={zeroY} stroke="var(--line, #22272d)" />

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
          x={totalWidth - 4}
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
