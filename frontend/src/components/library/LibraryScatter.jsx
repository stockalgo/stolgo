import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { marketColor } from "../../lib/colors.js";
import { pct, ratio } from "../../lib/format.js";

export function LibraryScatter({ runs = [] }) {
  const navigate = useNavigate();
  const [tooltip, setTooltip] = useState(null);

  // SVG coordinate system matches 01-library.html exactly
  // x: 0% to 55% drawdown -> 44 to 710 (width 666)
  // y: +20% to -55% return -> 12 to 304 (height 292)
  const getCoords = (run) => {
    const rawDd = Math.abs(run.metrics?.max_drawdown ?? 0) * 100;
    const rawRet = (run.metrics?.total_return ?? 0) * 100;

    const dd = Math.max(0, Math.min(55, rawDd));
    const ret = Math.max(-55, Math.min(20, rawRet));

    const cx = 44 + (dd / 55) * 666;
    const cy = 12 + ((20 - ret) / 75) * 292;
    const trades = run.metrics?.num_trades ?? 0;
    const r = 2.2 + Math.sqrt(trades) * 0.36;
    const isHollow = trades < 100;
    const color = marketColor(run.markets, run.dte);

    return { cx, cy, r, isHollow, color };
  };

  const xTicks = [
    { val: "−0%", x: 44.0 },
    { val: "−10%", x: 165.1 },
    { val: "−20%", x: 286.2 },
    { val: "−30%", x: 407.3 },
    { val: "−40%", x: 528.4 },
    { val: "−50%", x: 649.5 },
  ];

  const yTicks = [
    { val: "+20%", y: 15.0 },
    { val: "+5%", y: 73.4 },
    { val: "-10%", y: 131.8 },
    { val: "-25%", y: 190.2 },
    { val: "-40%", y: 248.6 },
    { val: "-55%", y: 307.0 },
  ];

  return (
    <section className="panel" style={{ position: "relative" }}>
      <div className="panel__head">
        <span className="eyebrow">Return vs max drawdown · size = trades</span>
      </div>

      <div style={{ position: "relative", width: "100%", overflow: "hidden" }}>
        <svg viewBox="0 0 720 330" width="100%" height="330" style={{ display: "block" }}>
          {/* Sweet spot box: dd < 10%, return > 0% */}
          <rect
            x="44.0"
            y="12"
            width="121.1"
            height="77.9"
            fill="#7cc4ff"
            fillOpacity=".05"
            stroke="#7cc4ff"
            strokeOpacity=".25"
            strokeDasharray="3 4"
          />

          {/* Zero return line */}
          <line x1="44" x2="710" y1="89.9" y2="89.9" stroke="var(--line, #2a3650)" />

          {/* X ticks */}
          {xTicks.map((t) => (
            <text
              key={t.val}
              x={t.x}
              y={322}
              textAnchor="middle"
              fill="var(--text-3, #6b737c)"
              fontSize="10"
              fontFamily="var(--font-mono, IBM Plex Mono)"
            >
              {t.val}
            </text>
          ))}

          {/* Y ticks */}
          {yTicks.map((t) => (
            <text
              key={t.val}
              x={36}
              y={t.y}
              textAnchor="end"
              fill="var(--text-3, #6b737c)"
              fontSize="10"
              fontFamily="var(--font-mono, IBM Plex Mono)"
            >
              {t.val}
            </text>
          ))}

          {/* Data points */}
          {runs.map((run) => {
            const { cx, cy, r, isHollow, color } = getCoords(run);
            return (
              <circle
                key={run.id}
                cx={cx.toFixed(1)}
                cy={cy.toFixed(1)}
                r={r.toFixed(1)}
                fill={isHollow ? "none" : color}
                fillOpacity=".8"
                stroke={color}
                strokeWidth="1.4"
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/runs/${run.id}`)}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  setTooltip({
                    run,
                    x: e.clientX,
                    y: e.clientY,
                  });
                }}
                onMouseMove={(e) => {
                  setTooltip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null));
                }}
                onMouseLeave={() => setTooltip(null)}
              />
            );
          })}
        </svg>

        {/* Hover Tooltip */}
        {tooltip && tooltip.run && (
          <div
            style={{
              position: "fixed",
              left: tooltip.x + 12,
              top: tooltip.y + 12,
              background: "var(--bg-overlay, #1b2028)",
              border: "1px solid var(--line, #2a3650)",
              borderRadius: "4px",
              padding: "8px 12px",
              fontSize: "12px",
              lineHeight: 1.4,
              color: "var(--text-1, #e6e8ea)",
              pointerEvents: "none",
              zIndex: 1000,
              boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
              maxWidth: "260px",
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: "4px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {tooltip.run.name || tooltip.run.id}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "auto auto", gap: "2px 8px", fontSize: "11px", color: "var(--text-2, #9aa3b2)" }}>
              <span>Return:</span>
              <span className="mono" style={{ textAlign: "right", color: (tooltip.run.metrics?.total_return ?? 0) >= 0 ? "var(--pos)" : "var(--neg)" }}>
                {pct(tooltip.run.metrics?.total_return)}
              </span>
              <span>Max DD:</span>
              <span className="mono neg" style={{ textAlign: "right" }}>
                {pct(tooltip.run.metrics?.max_drawdown)}
              </span>
              <span>Sharpe:</span>
              <span className="mono" style={{ textAlign: "right" }}>
                {ratio(tooltip.run.metrics?.sharpe)}
              </span>
              <span>Trades:</span>
              <span className="mono" style={{ textAlign: "right" }}>
                {tooltip.run.metrics?.num_trades ?? "—"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Legend chips */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "6px" }}>
        <span className="chip">
          <span className="dot" style={{ background: "#7cc4ff" }}></span>
          NIFTY 0-DTE
        </span>
        <span className="chip">
          <span className="dot" style={{ background: "#2f6fd6" }}></span>
          NIFTY 1-DTE
        </span>
        <span className="chip">
          <span className="dot" style={{ background: "#ffb35c" }}></span>
          SENSEX 0-DTE
        </span>
        <span className="chip">
          <span className="dot" style={{ background: "#c4561b" }}></span>
          SENSEX 1-DTE
        </span>
        <span className="chip">
          <span className="dot" style={{ background: "#9aa3b2" }}></span>
          Other / mixed
        </span>
        <span className="chip" style={{ borderStyle: "dashed", borderColor: "rgba(124, 196, 255, 0.35)" }}>
          Dashed box = sweet spot · DD &lt; 10%, return &gt; 0
        </span>
        <span className="chip">○ hollow = &lt; 100 trades</span>
      </div>
    </section>
  );
}
