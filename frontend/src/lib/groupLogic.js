import { pct, ratio } from "./format.js";
import { isComparable } from "./verdict.js";

export const FAMILY_ORDER = {
  STATIC: 1,
  LEG100: 2,
  A: 3,
  B: 4,
  C: 5,
  D: 6,
  CUT: 7,
  EXIT_TOUCH: 8,
  ONE_CONV: 9,
};

export function deriveRows(axes = {}, rowAxis = "family") {
  const vals = axes[rowAxis] || [];
  const sorted = [...vals];
  if (rowAxis === "family") {
    sorted.sort((a, b) => {
      const oA = FAMILY_ORDER[a] ?? 99;
      const oB = FAMILY_ORDER[b] ?? 99;
      if (oA !== oB) return oA - oB;
      return String(a).localeCompare(String(b));
    });
  } else {
    sorted.sort((a, b) => {
      if (typeof a === "number" && typeof b === "number") return a - b;
      return String(a).localeCompare(String(b));
    });
  }
  return sorted;
}

export function deriveCols(axes = {}, colAxis = "market × dte") {
  if (colAxis === "market × dte") {
    const markets = axes.market || ["NIFTY", "SENSEX"];
    const dtes = axes.dte || [0, 1];
    const list = [];
    markets.forEach((m) => {
      dtes.forEach((d) => {
        list.push({
          key: `${m} ${d}-DTE`,
          label: `${m} ${d}-DTE`,
          market: m,
          dte: d,
        });
      });
    });
    return list;
  }
  const vals = axes[colAxis] || [];
  return vals.map((v) => ({
    key: String(v),
    label: `${colAxis} ${v}`,
    val: v,
  }));
}

export function aggregateHeatGrid(runs = [], rows = [], cols = [], rowAxis, colAxis) {
  const map = new Map();

  rows.forEach((r) => {
    cols.forEach((c) => {
      const matchingRuns = runs.filter((run) => {
        const runRowVal = run.group?.axes?.[rowAxis];
        if (String(runRowVal) !== String(r)) return false;

        if (colAxis === "market × dte") {
          const m = run.group?.axes?.market;
          const d = run.group?.axes?.dte;
          return `${m} ${d}-DTE` === c.key;
        }
        return String(run.group?.axes?.[colAxis]) === String(c.key);
      });

      const count = matchingRuns.length;
      if (count === 0) {
        map.set(`${r}__${c.key}`, { count: 0, runs: [] });
        return;
      }

      const returns = matchingRuns.map((x) => x.metrics?.total_return || 0);
      const sharpes = matchingRuns.map((x) => x.metrics?.sharpe || 0);
      const dds = matchingRuns.map((x) => x.metrics?.max_drawdown || 0);
      const posCount = matchingRuns.filter(
        (x) => (x.metrics?.total_return || 0) > 0
      ).length;

      const meanReturn = returns.reduce((a, b) => a + b, 0) / count;
      const meanSharpe = sharpes.reduce((a, b) => a + b, 0) / count;
      const worstDD = Math.min(...dds);
      const posRatio = posCount / count;

      map.set(`${r}__${c.key}`, {
        count,
        runs: matchingRuns,
        meanReturn,
        meanSharpe,
        worstDD,
        posRatio,
      });
    });
  });

  return map;
}

export function calculateGridExtremes(cellDataLookup, cellMetric = "return") {
  let min = Infinity;
  let max = -Infinity;
  cellDataLookup.forEach((cell) => {
    if (cell.count === 0) return;
    let v = 0;
    if (cellMetric === "return") v = (cell.meanReturn || 0) * 100;
    else if (cellMetric === "sharpe") v = cell.meanSharpe || 0;
    else if (cellMetric === "max_dd") v = (cell.worstDD || 0) * 100;
    else if (cellMetric === "pct_pos") v = (cell.posRatio || 0) * 100;

    if (v < min) min = v;
    if (v > max) max = v;
  });

  if (min === Infinity) return { minStr: "—", maxStr: "—" };

  if (cellMetric === "return" || cellMetric === "max_dd") {
    return {
      minStr: `${min >= 0 ? "+" : "−"}${Math.abs(Math.round(min))}%`,
      maxStr: `${max >= 0 ? "+" : "−"}${Math.abs(Math.round(max))}%`,
    };
  } else if (cellMetric === "sharpe") {
    return { minStr: ratio(min), maxStr: ratio(max) };
  } else {
    return { minStr: `${Math.round(min)}%`, maxStr: `${Math.round(max)}%` };
  }
}

export function deriveRemainingAxes(axes = {}, rowAxis, colAxis) {
  const excluded = new Set([rowAxis]);
  if (colAxis === "market × dte") {
    excluded.add("market");
    excluded.add("dte");
  } else {
    excluded.add(colAxis);
  }
  return Object.keys(axes).filter((k) => !excluded.has(k));
}

export function pickTop4Runs(runs = [], cellMetric = "return") {
  if (runs.length === 0) return [];
  let pool = runs.filter((r) => isComparable(r));
  if (pool.length < 4) pool = runs;

  const sorted = [...pool].sort((a, b) => {
    if (cellMetric === "sharpe") {
      return (b.metrics?.sharpe || 0) - (a.metrics?.sharpe || 0);
    }
    if (cellMetric === "max_dd") {
      return (b.metrics?.max_drawdown || 0) - (a.metrics?.max_drawdown || 0);
    }
    return (b.metrics?.total_return || 0) - (a.metrics?.total_return || 0);
  });

  return sorted.slice(0, 4).map((r) => r.id);
}

export function calculateWindowRange(runs = []) {
  let windowStart = "";
  let windowEnd = "";
  runs.forEach((r) => {
    if (r.window?.start && (!windowStart || r.window.start < windowStart)) {
      windowStart = r.window.start;
    }
    if (r.window?.end && (!windowEnd || r.window.end > windowEnd)) {
      windowEnd = r.window.end;
    }
  });
  return windowStart && windowEnd ? `${windowStart} → ${windowEnd}` : "—";
}

export function calculateKnobEffects({ runs = [], axes = {}, cols = [], rows = [], rowAxis, colAxis }) {
  if (!runs || runs.length === 0) return null;

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

  const bestColStat =
    colStats.length > 0
      ? [...colStats].sort((a, b) => b.meanReturn - a.meanReturn)[0]
      : null;

  const bestCol2ValAxes = [];
  if (bestColStat && bestColStat.runs.length > 0) {
    const bestRuns = bestColStat.runs;
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

  const wholeGroup2ValAxes = [];
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

  const colMeans = colStats.map((c) => c.meanReturn);
  const colSpread =
    colMeans.length > 0
      ? Math.max(...colMeans) - Math.min(...colMeans)
      : 0;

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
}
