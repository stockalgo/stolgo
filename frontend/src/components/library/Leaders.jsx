import React from "react";
import { Link } from "react-router-dom";
import { isComparable } from "../../lib/verdict.js";
import { marketColor } from "../../lib/colors.js";
import { ratio, pct } from "../../lib/format.js";

export function Leaders({ runs = [] }) {
  // Filter for comparable runs only, sorted by Sharpe desc
  const comparableRuns = runs
    .filter(isComparable)
    .filter((r) => r.metrics?.sharpe != null)
    .sort((a, b) => (b.metrics?.sharpe ?? -Infinity) - (a.metrics?.sharpe ?? -Infinity));

  const leaders = comparableRuns.slice(0, 6);
  const topLeaderSharpe = leaders.length > 0 ? leaders[0].metrics?.sharpe : -Infinity;

  // Find non-comparable runs that had higher Sharpe than the #1 leader
  const higherExcluded = runs.filter(
    (r) => !isComparable(r) && r.metrics?.sharpe != null && r.metrics.sharpe > topLeaderSharpe
  );

  let footNote = "Top comparable runs by Sharpe.";
  if (higherExcluded.length > 0) {
    const trades = higherExcluded.map((r) => r.metrics?.num_trades ?? 0);
    const minT = Math.min(...trades);
    const maxT = Math.max(...trades);
    footNote = `The highest-Sharpe runs overall (Top 1–3, combined) have ${minT}–${maxT} trades, so they are excluded here.`;
  } else if (leaders.length === 0) {
    footNote = "No runs with ≥ 100 trades and ≥ 252 sessions match these filters.";
  }

  return (
    <section className="panel" style={{ display: "flex", flexDirection: "column" }}>
      <div className="panel__head">
        <span className="eyebrow">Leaders · ≥ 100 trades · by Sharpe</span>
      </div>

      <div style={{ flex: 1 }}>
        {leaders.length === 0 ? (
          <div className="muted" style={{ padding: "16px 0", fontSize: "13px" }}>
            No comparable runs match the selected filters.
          </div>
        ) : (
          leaders.map((run, idx) => {
            const color = marketColor(run.markets, run.dte);
            const ret = run.metrics?.total_return ?? 0;
            const retClass = ret >= 0 ? "num pos" : "num neg";

            return (
              <Link
                key={run.id}
                to={`/runs/${run.id}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "18px minmax(0,1fr) 54px 64px",
                  gap: "8px",
                  alignItems: "center",
                  height: "34px",
                  borderBottom: "1px solid var(--line-faint, rgba(255,255,255,0.06))",
                  fontSize: "12.5px",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <span className="mono faint">{idx + 1}</span>
                <span
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    display: "flex",
                    alignItems: "center",
                  }}
                  title={run.name || run.id}
                >
                  <span
                    className="dot"
                    style={{
                      display: "inline-block",
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: color,
                      marginRight: "6px",
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                    {run.name || run.id}
                  </span>
                </span>
                <span className="num" style={{ fontWeight: 500 }}>
                  {ratio(run.metrics?.sharpe)}
                </span>
                <span className={retClass}>{pct(ret)}</span>
              </Link>
            );
          })
        )}
      </div>

      <div className="panel__foot">{footNote}</div>
    </section>
  );
}
