import React, { useMemo } from "react";
import { inr } from "../../lib/format.js";

export function EquityChart({ daily = [], capital = 0, trades = [], range = "ALL" }) {
  const dailyRows = useMemo(() => {
    return Array.isArray(daily) ? daily : daily?.rows || [];
  }, [daily]);

  const { points, polylinePoints, polygonPoints, zeroY, top5Markers } = useMemo(() => {
    if (dailyRows.length === 0) {
      return { points: [], polylinePoints: "", polygonPoints: "", zeroY: 115, top5Markers: [] };
    }

    // Filter by range: 1Y = last 252 sessions
    let filtered = dailyRows;
    if (range === "1Y" && dailyRows.length > 252) {
      filtered = dailyRows.slice(-252);
    }

    const n = filtered.length;
    const values = filtered.map((d) => (d.equity ?? capital) - capital);

    const minVal = Math.min(0, ...values);
    const maxVal = Math.max(0, ...values);
    const valRange = maxVal - minVal || 1;

    // SVG coordinate space: 940 x 230. Y from 12 to 218
    const getY = (v) => 218 - ((v - minVal) / valRange) * 206;
    const zeroLineY = getY(0);

    const pts = [];
    const ptsList = [];
    for (let i = 0; i < n; i++) {
      const x = n > 1 ? (i / (n - 1)) * 940 : 470;
      const y = getY(values[i]);
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
      ptsList.push({ x, y, session: filtered[i].session, val: values[i] });
    }

    const polyline = pts.join(" ");
    const polygon = `0,${zeroLineY.toFixed(1)} ${polyline} 940,${zeroLineY.toFixed(1)}`;

    // Top 5 trades markers
    const sortedTrades = [...trades]
      .filter((t) => (t.net_pnl || 0) > 0)
      .sort((a, b) => (b.net_pnl || 0) - (a.net_pnl || 0))
      .slice(0, 5);

    const sessionIdxMap = new Map();
    filtered.forEach((d, idx) => {
      if (d.session) sessionIdxMap.set(d.session, idx);
    });

    const markers = [];
    for (const t of sortedTrades) {
      if (t.session_date && sessionIdxMap.has(t.session_date)) {
        const idx = sessionIdxMap.get(t.session_date);
        const pt = ptsList[idx];
        if (pt) {
          markers.push({
            cx: pt.x,
            cy: pt.y,
            trade: t,
          });
        }
      }
    }

    return {
      points: ptsList,
      polylinePoints: polyline,
      polygonPoints: polygon,
      zeroY: zeroLineY,
      top5Markers: markers,
    };
  }, [dailyRows, capital, trades, range]);

  return (
    <div>
      <div className="mono faint" style={{ fontSize: "11px", marginBottom: "4px" }}>
        EQUITY − CAPITAL (₹) · DAILY, EVERY SESSION
      </div>

      <svg viewBox="0 0 940 230" width="100%" height="230" preserveAspectRatio="none" style={{ display: "block" }}>
        {/* Zero baseline dashed line */}
        <line
          x1="0"
          x2="940"
          y1={zeroY.toFixed(1)}
          y2={zeroY.toFixed(1)}
          stroke="var(--line-strong)"
          strokeDasharray="3 4"
        />

        {/* Area fill */}
        {polygonPoints && (
          <polygon
            points={polygonPoints}
            fill="var(--pos)"
            fillOpacity="0.08"
          />
        )}

        {/* Polyline */}
        {polylinePoints && (
          <polyline
            points={polylinePoints}
            fill="none"
            stroke="var(--pos)"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        )}

        {/* Top 5 trades rings */}
        {top5Markers.map((m, i) => (
          <circle
            key={i}
            cx={m.cx.toFixed(1)}
            cy={m.cy.toFixed(1)}
            r="5.5"
            fill="var(--bg-app)"
            stroke="var(--accent)"
            strokeWidth="2"
          >
            <title>
              {`Top trade: ${m.trade.session_date} (${inr(m.trade.net_pnl, { signed: true })})`}
            </title>
          </circle>
        ))}
      </svg>
    </div>
  );
}
