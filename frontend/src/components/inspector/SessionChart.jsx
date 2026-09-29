import React, { useMemo } from "react";
import { timeIST } from "../../lib/format.js";
import { EmptyState } from "../ui/EmptyState.jsx";

export function SessionChart({ tradeDetail, width = 520, height = 176 }) {
  const bars = tradeDetail?.bars || [];
  const legs = tradeDetail?.legs || [];
  const trade = tradeDetail?.trade || {};

  const { chartData, noBars } = useMemo(() => {
    if (!bars || bars.length === 0) {
      return { chartData: null, noBars: true };
    }

    // CE and PE short legs
    const ceLeg = legs.find((l) => l.option_type === "CE");
    const peLeg = legs.find((l) => l.option_type === "PE");

    const allPrices = bars.flatMap((b) => [b.open, b.high, b.low, b.close]);
    if (ceLeg?.strike) allPrices.push(ceLeg.strike);
    if (peLeg?.strike) allPrices.push(peLeg.strike);

    const minP = Math.min(...allPrices);
    const maxP = Math.max(...allPrices);
    const pMargin = (maxP - minP) * 0.08 || 10;
    const minDomain = minP - pMargin;
    const maxDomain = maxP + pMargin;
    const rangeP = maxDomain - minDomain || 1;

    const chartH = height - 20;
    const chartW = width - 55;

    // SVG coordinates: usable height for bars is chartH (leaving 20px at bottom for labels)
    const getY = (p) => chartH - ((p - minDomain) / rangeP) * (chartH - 12);

    const n = bars.length;
    // usable width for candles is chartW (leaving 55px on right for strike text)
    const getX = (i) => 14 + (n > 1 ? (i / (n - 1)) * (chartW - 28) : chartW / 2);

    // Candle bar elements
    const candles = bars.map((b, i) => {
      const cx = getX(i);
      const isUp = (b.close ?? 0) >= (b.open ?? 0);
      const color = isUp ? "var(--pos)" : "var(--neg)";
      const topY = getY(Math.max(b.open, b.close));
      const botY = getY(Math.min(b.open, b.close));
      const bodyH = Math.max(1.5, botY - topY);

      return {
        cx,
        highY: getY(b.high),
        lowY: getY(b.low),
        bodyY: topY,
        bodyH,
        color,
        time: b.time,
      };
    });

    // Timing window
    let entryX = 24;
    let exitX = chartW - 20;
    let entryLabel = "SELL";
    let exitLabel = "BUY";

    if (trade.entry_ts) {
      const eTime = typeof trade.entry_ts === "number" ? trade.entry_ts : Math.floor(new Date(trade.entry_ts).getTime() / 1000);
      entryLabel = `SELL ${timeIST(eTime)}`;
      // Find closest bar index
      let closestIdx = 0;
      let minDiff = Infinity;
      bars.forEach((b, i) => {
        const diff = Math.abs(b.time - eTime);
        if (diff < minDiff) {
          minDiff = diff;
          closestIdx = i;
        }
      });
      entryX = getX(closestIdx);
    }

    if (trade.exit_ts) {
      const xTime = typeof trade.exit_ts === "number" ? trade.exit_ts : Math.floor(new Date(trade.exit_ts).getTime() / 1000);
      exitLabel = `BUY ${timeIST(xTime)}`;
      let closestIdx = bars.length - 1;
      let minDiff = Infinity;
      bars.forEach((b, i) => {
        const diff = Math.abs(b.time - xTime);
        if (diff < minDiff) {
          minDiff = diff;
          closestIdx = i;
        }
      });
      exitX = getX(closestIdx);
    }

    return {
      chartData: {
        candles,
        ceLeg,
        peLeg,
        ceY: ceLeg?.strike ? getY(ceLeg.strike) : null,
        peY: peLeg?.strike ? getY(peLeg.strike) : null,
        entryX,
        exitX,
        entryLabel,
        exitLabel,
        chartH,
        chartW,
      },
      noBars: false,
    };
  }, [bars, legs, trade, width, height]);

  if (noBars || !chartData) {
    return (
      <EmptyState
        title="No intraday bars for this session"
        style={{ height: `${height}px`, justifyContent: "center" }}
      />
    );
  }

  const { candles, ceLeg, peLeg, ceY, peY, entryX, exitX, entryLabel, exitLabel, chartH, chartW } = chartData;
  const holdingW = Math.max(2, exitX - entryX);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      style={{ display: "block" }}
    >
      {/* Shaded holding window */}
      <rect
        x={entryX}
        y={0}
        width={holdingW}
        height={chartH}
        fill="var(--accent)"
        fillOpacity="0.05"
      />

      {/* Strike CE line */}
      {ceY !== null && (
        <>
          <line
            x1="0"
            x2={chartW}
            y1={ceY}
            y2={ceY}
            stroke="var(--neg-text)"
            strokeDasharray="4 3"
          />
          <text
            x={width - 2}
            y={ceY + 3}
            textAnchor="end"
            fill="var(--neg-text)"
            fontSize="10"
            fontFamily="var(--font-mono, IBM Plex Mono)"
          >
            CE {ceLeg.strike.toLocaleString()}
          </text>
        </>
      )}

      {/* Strike PE line */}
      {peY !== null && (
        <>
          <line
            x1="0"
            x2={chartW}
            y1={peY}
            y2={peY}
            stroke="var(--info)"
            strokeDasharray="4 3"
          />
          <text
            x={width - 2}
            y={peY + 3}
            textAnchor="end"
            fill="var(--info)"
            fontSize="10"
            fontFamily="var(--font-mono, IBM Plex Mono)"
          >
            PE {peLeg.strike.toLocaleString()}
          </text>
        </>
      )}

      {/* 15m Candles */}
      {candles.map((c, i) => (
        <g key={i}>
          {/* Wick */}
          <line
            x1={c.cx}
            x2={c.cx}
            y1={c.highY}
            y2={c.lowY}
            stroke={c.color}
            strokeWidth="1"
          />
          {/* Body */}
          <rect
            x={c.cx - 4.5}
            y={c.bodyY}
            width={9}
            height={c.bodyH}
            fill={c.color}
          />
        </g>
      ))}

      {/* SELL entry vertical line + label */}
      <line
        x1={entryX}
        x2={entryX}
        y1={0}
        y2={chartH}
        stroke="var(--accent)"
        strokeWidth="1.2"
      />
      <text
        x={Math.max(28, Math.min(width - 28, entryX))}
        y={height - 6}
        textAnchor="middle"
        fill="var(--accent)"
        fontSize="10"
        fontFamily="var(--font-mono, IBM Plex Mono)"
      >
        {entryLabel}
      </text>

      {/* BUY exit vertical line + label */}
      <line
        x1={exitX}
        x2={exitX}
        y1={0}
        y2={chartH}
        stroke="var(--accent)"
        strokeWidth="1.2"
      />
      <text
        x={Math.max(28, Math.min(width - 28, exitX))}
        y={height - 6}
        textAnchor="middle"
        fill="var(--accent)"
        fontSize="10"
        fontFamily="var(--font-mono, IBM Plex Mono)"
      >
        {exitLabel}
      </text>
    </svg>
  );
}
