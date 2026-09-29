import React, { useMemo } from "react";
import { inr } from "../../lib/format.js";

const MONTH_LETTERS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

export function MonthlyHeatmap({ monthly = [] }) {
  const rows = useMemo(() => {
    return Array.isArray(monthly) ? monthly : monthly?.rows || [];
  }, [monthly]);

  const { years, monthMap, greenCount, totalCount } = useMemo(() => {
    const map = new Map();
    const yearSet = new Set();
    let green = 0;

    for (const r of rows) {
      if (!r.month) continue;
      const [yStr, mStr] = r.month.split("-");
      const y = parseInt(yStr, 10);
      const m = parseInt(mStr, 10);
      if (!Number.isNaN(y) && !Number.isNaN(m)) {
        yearSet.add(y);
        map.set(`${y}-${m}`, r);
        if (r.pnl > 0) {
          green += 1;
        }
      }
    }

    const sortedYears = Array.from(yearSet).sort((a, b) => a - b);
    return {
      years: sortedYears,
      monthMap: map,
      greenCount: green,
      totalCount: rows.length,
    };
  }, [rows]);

  return (
    <section className="panel" style={{ display: "flex", flexDirection: "column" }}>
      <div
        className="panel__head"
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
      >
        <span className="eyebrow">Monthly P&amp;L</span>
        <span className="faint" style={{ fontSize: "11px" }}>
          {greenCount} of {totalCount} months green
        </span>
      </div>

      {years.length === 0 ? (
        <div className="muted" style={{ padding: "32px 0", textAlign: "center", fontSize: "12px" }}>
          No monthly data available
        </div>
      ) : (
        <div
          className="heat"
          style={{ gridTemplateColumns: "38px repeat(12, minmax(0, 1fr))", marginTop: "4px" }}
        >
          {/* Header row: empty corner + month initials */}
          <span></span>
          {MONTH_LETTERS.map((letter, i) => (
            <span key={i} className="mono faint" style={{ textAlign: "center" }}>
              {letter}
            </span>
          ))}

          {/* Rows: year + 12 cells */}
          {years.map((year) => (
            <React.Fragment key={year}>
              <span className="mono muted" style={{ alignSelf: "center", fontSize: "11px" }}>
                {year}
              </span>
              {Array.from({ length: 12 }, (_, idx) => {
                const monthNum = idx + 1;
                const entry = monthMap.get(`${year}-${monthNum}`);

                if (!entry || entry.pnl === null || entry.pnl === undefined) {
                  return <div key={monthNum} className="heat__cell heat__cell--empty" />;
                }

                const pnl = entry.pnl;
                const alpha = Math.min(1, 0.15 + Math.abs(pnl) / 8000);
                const bg =
                  pnl >= 0
                    ? `rgba(61, 220, 151, ${alpha.toFixed(2)})`
                    : `rgba(229, 72, 77, ${alpha.toFixed(2)})`;

                const monthStr = String(monthNum).padStart(2, "0");
                const titleStr = `${year}-${monthStr}: ${inr(pnl, { signed: true })}`;

                return (
                  <div
                    key={monthNum}
                    className="heat__cell"
                    title={titleStr}
                    style={{ background: bg }}
                  />
                );
              })}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Footer legend */}
      <div
        className="panel__foot"
        style={{
          display: "flex",
          gap: "10px",
          alignItems: "center",
          marginTop: "auto",
        }}
      >
        <span
          style={{
            width: "36px",
            height: "8px",
            borderRadius: "2px",
            background: "linear-gradient(90deg, var(--neg), var(--bg-raised), var(--pos))",
            flexShrink: 0,
          }}
        />
        <span>−₹8k … +₹8k per month</span>
      </div>
    </section>
  );
}
