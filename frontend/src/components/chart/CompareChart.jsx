import React, { useMemo } from "react";

export function CompareChart({ runsWithDaily = [], metricMode = "% return" }) {
  const chartData = useMemo(() => {
    if (!runsWithDaily || runsWithDaily.length === 0) return null;

    // Collect all unique session dates sorted
    const allDatesSet = new Set();
    runsWithDaily.forEach(({ daily }) => {
      (daily?.rows || []).forEach((r) => {
        if (r.session) allDatesSet.add(r.session);
      });
    });

    const sortedDates = Array.from(allDatesSet).sort();
    if (sortedDates.length === 0) return null;

    const dateToIndex = new Map(sortedDates.map((d, i) => [d, i]));
    const totalSessions = sortedDates.length;

    // Build series points for each run
    let minVal = 0;
    let maxVal = 0;
    let minDd = 0;

    const series = runsWithDaily.map(({ run, daily, color }) => {
      const capital = run?.capital || run?.config?.capital || 180000;
      const rows = daily?.rows || [];

      let peak = capital;
      const points = [];
      const ddPoints = [];

      rows.forEach((r) => {
        const xIdx = dateToIndex.get(r.session);
        if (xIdx == null) return;

        const eq = r.equity ?? (capital + (r.pnl ?? 0));
        if (eq > peak) peak = eq;

        let val = 0;
        if (metricMode === "% return") {
          val = ((eq - capital) / capital) * 100;
        } else {
          val = eq - capital;
        }

        const dd = peak > 0 ? ((eq - peak) / peak) * 100 : 0;

        if (val < minVal) minVal = val;
        if (val > maxVal) maxVal = val;
        if (dd < minDd) minDd = dd;

        points.push({ xIdx, val });
        ddPoints.push({ xIdx, dd });
      });

      return { run, color, points, ddPoints };
    });

    // Determine scale for top chart (height 260, usable y: 15 to 235)
    // Add margin
    const rangeVal = Math.max(maxVal - minVal, 1);
    const domainMin = Math.floor(minVal - rangeVal * 0.05);
    const domainMax = Math.ceil(maxVal + rangeVal * 0.05);
    const domainRange = domainMax - domainMin || 1;

    const getX = (xIdx) =>
      60 + (totalSessions > 1 ? (xIdx / (totalSessions - 1)) * 920 : 460);
    const getY = (val) => 235 - ((val - domainMin) / domainRange) * 220;

    // Drawdown scale (height 90, usable y: 4 to 80)
    const ddRange = Math.abs(minDd) || 10;
    const getDdY = (dd) => 4 + (Math.abs(dd) / ddRange) * 76;

    // Y ticks for top chart
    const yTicks = [];
    const step = metricMode === "% return" ? 5 : 10000;
    const startTick = Math.ceil(domainMin / step) * step;
    for (let t = startTick; t <= domainMax; t += step) {
      yTicks.push(t);
    }

    // Zero Y
    const zeroY = getY(0);

    // Year markers
    const yearMarkers = [];
    let curYear = "";
    sortedDates.forEach((d, i) => {
      const y = d.slice(0, 4);
      if (y !== curYear) {
        curYear = y;
        yearMarkers.push({ year: y, x: getX(i) });
      }
    });

    return {
      totalSessions,
      series,
      getX,
      getY,
      getDdY,
      yTicks,
      zeroY,
      yearMarkers,
      minDd,
    };
  }, [runsWithDaily, metricMode]);

  if (!chartData) {
    return (
      <div
        className="muted"
        style={{
          height: "260px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        No daily series data available
      </div>
    );
  }

  const { series, getX, getY, getDdY, yTicks, zeroY, yearMarkers, minDd } = chartData;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {/* Return / P&L Chart */}
      <svg
        viewBox="0 0 1000 260"
        width="100%"
        height="260"
        style={{ display: "block" }}
      >
        {/* Y ticks and horizontal grid */}
        {yTicks.map((t) => {
          const y = getY(t);
          const label =
            metricMode === "% return"
              ? `${t > 0 ? "+" : ""}${t}%`
              : `${t > 0 ? "+" : ""}₹${(t / 1000).toFixed(0)}k`;
          return (
            <g key={t}>
              <line
                x1="50"
                x2="990"
                y1={y}
                y2={y}
                stroke="var(--bg-raised)"
                strokeWidth="1"
              />
              <text
                x="44"
                y={y + 3}
                textAnchor="end"
                fill="var(--text-faint)"
                fontSize="10"
                fontFamily="var(--font-mono, IBM Plex Mono)"
              >
                {label}
              </text>
            </g>
          );
        })}

        {/* Year dividers and labels */}
        {yearMarkers.map((ym) => (
          <g key={ym.year}>
            <line
              x1={ym.x}
              x2={ym.x}
              y1="0"
              y2="242"
              stroke="var(--bg-raised)"
              strokeWidth="1"
            />
            <text
              x={ym.x + 4}
              y="256"
              fill="var(--text-faint)"
              fontSize="10"
              fontFamily="var(--font-mono, IBM Plex Mono)"
            >
              {ym.year}
            </text>
          </g>
        ))}

        {/* Zero baseline */}
        <line
          x1="50"
          x2="990"
          y1={zeroY}
          y2={zeroY}
          stroke="var(--line-strong)"
          strokeWidth="1.2"
        />

        {/* Polylines for each run */}
        {series.map((s, idx) => {
          const polyPoints = s.points
            .map((p) => `${getX(p.xIdx).toFixed(1)},${getY(p.val).toFixed(1)}`)
            .join(" ");

          return (
            <polyline
              key={idx}
              points={polyPoints}
              fill="none"
              stroke={s.color}
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
          );
        })}
      </svg>

      {/* Drawdown Section */}
      <div>
        <div
          className="mono faint"
          style={{ fontSize: "11px", margin: "4px 0" }}
        >
          DRAWDOWN
        </div>
        <svg
          viewBox="0 0 1000 90"
          width="100%"
          height="90"
          style={{ display: "block" }}
        >
          {/* Baseline zero */}
          <line
            x1="50"
            x2="990"
            y1="4.0"
            y2="4.0"
            stroke="var(--line-strong)"
            strokeWidth="1"
          />
          <text
            x="44"
            y="61.7"
            textAnchor="end"
            fill="var(--text-faint)"
            fontSize="10"
            fontFamily="var(--font-mono, IBM Plex Mono)"
          >
            {minDd < -5 ? `${Math.round(minDd)}%` : "-10%"}
          </text>

          {/* Drawdown polylines */}
          {series.map((s, idx) => {
            const polyPoints = s.ddPoints
              .map((p) => `${getX(p.xIdx).toFixed(1)},${getDdY(p.dd).toFixed(1)}`)
              .join(" ");

            return (
              <polyline
                key={idx}
                points={polyPoints}
                fill="none"
                stroke={s.color}
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
}
