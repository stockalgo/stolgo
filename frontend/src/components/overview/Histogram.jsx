import React, { useState, useMemo } from "react";
import { Seg } from "../ui/Seg.jsx";
import { computeHistogramBins } from "../../lib/histogram.js";
import { inr, inrCompact, rmult } from "../../lib/format.js";

export function Histogram({ trades = [] }) {
  const [mode, setMode] = useState("inr"); // "inr" | "r"

  const hasAnyR = useMemo(() => {
    return trades.some((t) => t.r_multiple !== null && t.r_multiple !== undefined && !Number.isNaN(t.r_multiple));
  }, [trades]);

  const effectiveMode = hasAnyR ? mode : "inr";

  const { bins, minEdge, maxEdge, median, mean } = useMemo(() => {
    const isR = effectiveMode === "r";
    const rawValues = trades
      .map((t) => (isR ? t.r_multiple : t.net_pnl))
      .filter((v) => v !== null && v !== undefined && !Number.isNaN(v));

    if (rawValues.length === 0) {
      return { bins: [], minEdge: 0, maxEdge: 0, median: null, mean: null };
    }

    const binSize = isR ? 0.5 : 1000;
    const hist = computeHistogramBins(rawValues, binSize);

    const sorted = [...rawValues].sort((a, b) => a - b);
    const midIdx = Math.floor(sorted.length / 2);
    const med =
      sorted.length % 2 === 0
        ? (sorted[midIdx - 1] + sorted[midIdx]) / 2
        : sorted[midIdx];
    const avg = rawValues.reduce((a, b) => a + b, 0) / rawValues.length;

    return {
      bins: hist.bins,
      minEdge: hist.minEdge,
      maxEdge: hist.maxEdge,
      median: med,
      mean: avg,
    };
  }, [trades, effectiveMode]);

  const maxCount = useMemo(() => {
    return Math.max(1, ...bins.map((b) => b.count));
  }, [bins]);

  // Axis labels: min, 0, mid-positive, max
  const axisLabels = useMemo(() => {
    const isR = effectiveMode === "r";
    const fmt = (v) => {
      if (v === 0) return "0";
      if (isR) return rmult(v);
      return inrCompact(v, { signed: true });
    };

    const midPos = maxEdge > 0 ? Math.round(maxEdge / 2 / (isR ? 0.5 : 1000)) * (isR ? 0.5 : 1000) : null;

    return {
      min: fmt(minEdge),
      zero: "0",
      mid: midPos !== null && midPos > 0 && midPos < maxEdge ? fmt(midPos) : null,
      max: fmt(maxEdge),
    };
  }, [minEdge, maxEdge, effectiveMode]);

  const formatStat = (val) => {
    if (val === null || val === undefined) return "—";
    return effectiveMode === "r" ? rmult(val) : inr(val, { signed: true });
  };

  const medClass = median === null ? "" : median >= 0 ? "pos" : "neg";
  const meanClass = mean === null ? "" : mean >= 0 ? "pos" : "neg";

  return (
    <section className="panel" style={{ display: "flex", flexDirection: "column" }}>
      <div className="panel__head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="eyebrow">Trade P&amp;L distribution</span>
        <div className="seg seg--mono">
          <button
            className={`seg__item ${effectiveMode === "inr" ? "seg__item--active" : ""}`}
            aria-selected={effectiveMode === "inr"}
            onClick={() => setMode("inr")}
          >
            ₹
          </button>
          <button
            className={`seg__item ${effectiveMode === "r" ? "seg__item--active" : ""}`}
            aria-selected={effectiveMode === "r"}
            disabled={!hasAnyR}
            title={!hasAnyR ? "No R-multiples recorded for this run" : undefined}
            onClick={() => setMode("r")}
          >
            R
          </button>
        </div>
      </div>

      {bins.length === 0 ? (
        <div className="muted" style={{ padding: "32px 0", textAlign: "center", fontSize: "12px" }}>
          No trade data available
        </div>
      ) : (
        <>
          {/* Histogram bars container */}
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: "3px",
              height: "116px",
              borderBottom: "1px solid var(--line-strong)",
              paddingTop: "8px",
            }}
          >
            {bins.map((bin, i) => {
              const heightPct = bin.count > 0 ? Math.max(2, (bin.count / maxCount) * 110) : 0;
              const barColor = bin.isNegative ? "var(--neg)" : "var(--pos)";

              return (
                <div
                  key={i}
                  title={`${bin.start}…${bin.end}: ${bin.count}`}
                  style={{
                    flex: 1,
                    height: `${heightPct}px`,
                    borderRadius: "2px 2px 0 0",
                    background: barColor,
                    transition: "height 0.2s ease",
                  }}
                />
              );
            })}
          </div>

          {/* Axis readout */}
          <div
            className="mono faint"
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "10px",
              marginTop: "6px",
            }}
          >
            <span>{axisLabels.min}</span>
            <span>{axisLabels.zero}</span>
            {axisLabels.mid && <span>{axisLabels.mid}</span>}
            <span>{axisLabels.max}</span>
          </div>
        </>
      )}

      {/* Footer */}
      <div className="panel__foot" style={{ marginTop: "auto" }}>
        Median trade <span className={`mono ${medClass}`}>{formatStat(median)}</span> · mean{" "}
        <span className={`mono ${meanClass}`}>{formatStat(mean)}</span>
      </div>
    </section>
  );
}
