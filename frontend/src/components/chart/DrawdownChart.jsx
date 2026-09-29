import React, { useMemo } from "react";
import { pct } from "../../lib/format.js";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function DrawdownChart({ daily = [], run = null, range = "ALL" }) {
  const dailyRows = useMemo(() => {
    return Array.isArray(daily) ? daily : daily?.rows || [];
  }, [daily]);

  const { caption, polylinePoints, polygonPoints } = useMemo(() => {
    if (dailyRows.length === 0) {
      return { caption: "DRAWDOWN · —", polylinePoints: "", polygonPoints: "" };
    }

    let filtered = dailyRows;
    if (range === "1Y" && dailyRows.length > 252) {
      filtered = dailyRows.slice(-252);
    }

    const n = filtered.length;
    // drawdown is a decimal <= 0 (e.g. -0.095)
    const drawdowns = filtered.map((d) => (d.drawdown !== undefined && d.drawdown !== null ? d.drawdown : 0));
    const maxDd = Math.min(0, ...drawdowns);
    const worstDdAbs = Math.abs(maxDd) || 0.01;

    // Peak note calculation
    const lastDd = drawdowns[drawdowns.length - 1];
    let peakNote = "recovered";

    if (lastDd < -0.0001) {
      // Find session date where drawdown was 0 right before the last dive
      let peakSession = null;
      for (let i = drawdowns.length - 1; i >= 0; i--) {
        if (drawdowns[i] >= -0.0001) {
          peakSession = filtered[i].session;
          break;
        }
      }
      if (peakSession) {
        const parts = peakSession.split("-");
        const mIdx = parseInt(parts[1], 10) - 1;
        const monStr = MONTH_NAMES[mIdx] || parts[1];
        peakNote = `${monStr}-${parts[0]} peak not yet reclaimed`;
      } else {
        peakNote = "peak not yet reclaimed";
      }
    } else {
      const dur = run?.metrics?.max_drawdown_duration;
      peakNote = dur ? `recovered in ${dur} sessions` : "recovered";
    }

    const maxDdFormatted = pct(run?.metrics?.max_drawdown ?? maxDd);
    const durationStr = `${run?.metrics?.max_drawdown_duration ?? filtered.length} sessions`;
    const capStr = `DRAWDOWN · max ${maxDdFormatted} · ${durationStr} · ${peakNote}`;

    // SVG coordinate space: 940 x 64. 0 is top (0% drawdown), 60 is max drawdown
    const getY = (dd) => (Math.abs(dd) / worstDdAbs) * 58 + 2;

    const pts = [];
    for (let i = 0; i < n; i++) {
      const x = n > 1 ? (i / (n - 1)) * 940 : 470;
      const y = getY(drawdowns[i]);
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }

    const polyline = pts.join(" ");
    const polygon = `0,0 ${polyline} 940,0`;

    return {
      caption: capStr,
      polylinePoints: polyline,
      polygonPoints: polygon,
    };
  }, [dailyRows, run, range]);

  return (
    <div>
      <div className="mono faint" style={{ fontSize: "11px", margin: "8px 0 4px" }}>
        {caption}
      </div>

      <svg viewBox="0 0 940 64" width="100%" height="64" preserveAspectRatio="none" style={{ display: "block" }}>
        {polygonPoints && (
          <polygon
            points={polygonPoints}
            fill="var(--neg, #e5484d)"
            fillOpacity="0.28"
          />
        )}
        {polylinePoints && (
          <polyline
            points={polylinePoints}
            fill="none"
            stroke="var(--neg, #e5484d)"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        )}
      </svg>
    </div>
  );
}
