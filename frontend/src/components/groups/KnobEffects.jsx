import React, { useMemo } from "react";
import { pct } from "../../lib/format.js";

export function KnobEffects({ runs = [], axes = {}, cols = [], rows = [], rowAxis, colAxis }) {
  const analysis = useMemo(() => {
    if (!runs || runs.length === 0) return null;

    // 1. For each column value: {col} · variants positive {pos} / {n}
    const colStats = cols.map((col) => {
      const colRuns = runs.filter((r) => {
        if (colAxis === "market × dte") {
          const m = r.group?.axes?.market;
          const d = r.group?.axes?.dte;
          return `${m} ${d}-DTE` === col.key;
        }
        return String(r.group?.axes?.[colAxis]) === String(col.key);
      });

      const total = colRuns.length;
      const pos = colRuns.filter(
        (r) => (r.metrics?.total_return || 0) > 0
      ).length;
      const returns = colRuns.map((r) => r.metrics?.total_return || 0);
      const meanReturn =
        total > 0 ? returns.reduce((a, b) => a + b, 0) / total : 0;

      return {
        col: col.label,
        key: col.key,
        total,
        pos,
        meanReturn,
        runs: colRuns,
      };
    });

    // Best col by highest mean return
    const bestColStat =
      colStats.length > 0
        ? [...colStats].sort((a, b) => b.meanReturn - a.meanReturn)[0]
        : null;

    // 2. For each axis with exactly 2 values present inside the best column:
    // {best col} {rows-filter?} · {axis}={v} positive {a}/{b}
    const bestCol2ValAxes = [];
    if (bestColStat && bestColStat.runs.length > 0) {
      const bestRuns = bestColStat.runs;
      // Filter out axes used in colAxis
      const excludedAxes =
        colAxis === "market × dte" ? ["market", "dte"] : [colAxis];

      Object.entries(axes).forEach(([ax, vals]) => {
        if (excludedAxes.includes(ax)) return;
        const presentVals = Array.from(
          new Set(
            bestRuns
              .map((r) => r.group?.axes?.[ax])
              .filter((v) => v !== null && v !== undefined)
          )
        );

        if (presentVals.length === 2) {
          presentVals.sort();
          presentVals.forEach((v) => {
            const sub = bestRuns.filter((r) => r.group?.axes?.[ax] === v);
            const total = sub.length;
            const pos = sub.filter(
              (r) => (r.metrics?.total_return || 0) > 0
            ).length;
            bestCol2ValAxes.push({
              label: `${bestColStat.col} · ${ax}=${v} positive`,
              pos,
              total,
              axis: ax,
              val: v,
            });
          });
        }
      });
    }

    // 3. For each other 2-valued axis over the whole group:
    // {axis} {v1} vs {axis} {v2} · mean return x% vs y%
    const wholeGroup2ValAxes = [];
    const usedInBestCol = new Set(bestCol2ValAxes.map((x) => x.axis));
    const excludedAxes =
      colAxis === "market × dte" ? ["market", "dte"] : [colAxis];

    Object.entries(axes).forEach(([ax, vals]) => {
      if (excludedAxes.includes(ax)) return;
      const presentVals = Array.from(
        new Set(
          runs
            .map((r) => r.group?.axes?.[ax])
            .filter((v) => v !== null && v !== undefined)
        )
      );

      if (presentVals.length === 2) {
        presentVals.sort();
        const [v1, v2] = presentVals;
        const sub1 = runs.filter((r) => r.group?.axes?.[ax] === v1);
        const sub2 = runs.filter((r) => r.group?.axes?.[ax] === v2);

        const m1 =
          sub1.length > 0
            ? sub1.reduce((sum, r) => sum + (r.metrics?.total_return || 0), 0) /
              sub1.length
            : 0;
        const m2 =
          sub2.length > 0
            ? sub2.reduce((sum, r) => sum + (r.metrics?.total_return || 0), 0) /
              sub2.length
            : 0;

        wholeGroup2ValAxes.push({
          label: `${ax} ${v1} vs ${ax} ${v2} · mean return`,
          val1: pct(m1, { signed: true }),
          val2: pct(m2, { signed: true }),
        });
      }
    });

    // Spread between column means vs row means
    const colMeans = colStats.map((c) => c.meanReturn);
    const colSpread =
      colMeans.length > 0
        ? Math.max(...colMeans) - Math.min(...colMeans)
        : 0;

    // Calculate row means
    const rowMeans = rows.map((rLabel) => {
      const rowRuns = runs.filter(
        (r) => String(r.group?.axes?.[rowAxis]) === String(rLabel)
      );
      if (rowRuns.length === 0) return 0;
      return (
        rowRuns.reduce((sum, r) => sum + (r.metrics?.total_return || 0), 0) /
        rowRuns.length
      );
    });
    const rowSpread =
      rowMeans.length > 0
        ? Math.max(...rowMeans) - Math.min(...rowMeans)
        : 0;

    // Callout text
    const worstCol =
      colStats.length > 0
        ? [...colStats].sort((a, b) => a.meanReturn - b.meanReturn)[0]
        : null;

    let calloutText = "";
    if (colSpread > rowSpread) {
      if (worstCol && worstCol.pos === 0) {
        calloutText = `The market/DTE regime matters more than any knob: ${worstCol.col} loses in every variant. Within ${bestColStat ? bestColStat.col : "the best regime"}, knob choices decide the result.`;
      } else {
        calloutText = `The market/DTE regime matters more than any knob: spread between column regimes (${pct(colSpread, { signed: false })}) is wider than between row variants (${pct(rowSpread, { signed: false })}).`;
      }
    } else {
      calloutText = "Knob choice matters more than market/DTE regime here.";
    }

    return {
      colStats,
      bestCol2ValAxes,
      wholeGroup2ValAxes,
      calloutText,
    };
  }, [runs, axes, cols, rows, rowAxis, colAxis]);

  if (!analysis) {
    return <div className="muted" style={{ padding: 16 }}>No knob analysis available</div>;
  }

  const getRatioClass = (pos, total) => {
    if (total === 0) return "";
    if (pos === total) return "pos";
    if (pos === 0) return "neg";
    return "accent";
  };

  return (
    <div>
      {/* 1. Column variants positive */}
      {analysis.colStats.map((cs) => (
        <div key={cs.key} className="kv kv--divided">
          <span>{cs.col} · variants positive</span>
          <span className={getRatioClass(cs.pos, cs.total)}>
            {cs.pos} / {cs.total}
          </span>
        </div>
      ))}

      {/* 2. Best col 2-valued axes */}
      {analysis.bestCol2ValAxes.map((bca, idx) => (
        <div key={`bca-${idx}`} className="kv kv--divided">
          <span>{bca.label}</span>
          <span className={getRatioClass(bca.pos, bca.total)}>
            {bca.pos} / {bca.total}
          </span>
        </div>
      ))}

      {/* 3. Other 2-valued axes over whole group */}
      {analysis.wholeGroup2ValAxes.map((wga, idx) => (
        <div key={`wga-${idx}`} className="kv">
          <span>{wga.label}</span>
          <span>
            {wga.val1} vs {wga.val2}
          </span>
        </div>
      ))}

      {/* Callout */}
      <div className="callout" style={{ marginTop: 10 }}>
        {analysis.calloutText}
      </div>
    </div>
  );
}
