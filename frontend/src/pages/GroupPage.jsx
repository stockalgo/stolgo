import React, { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getGroup } from "../api/endpoints.js";
import { HeatGrid } from "../components/groups/HeatGrid.jsx";
import { KnobEffects } from "../components/groups/KnobEffects.jsx";
import { Button } from "../components/ui/Button.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { isComparable } from "../lib/verdict.js";
import { pct, ratio } from "../lib/format.js";
import { useBreadcrumbs } from "../context/BreadcrumbContext.jsx";

const FAMILY_ORDER = {
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

export function GroupPage() {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const { setCrumbs } = useBreadcrumbs();

  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Controls state
  const [rowAxis, setRowAxis] = useState("family");
  const [colAxis, setColAxis] = useState("market × dte");
  const [cellMetric, setCellMetric] = useState("return"); // 'return' | 'sharpe' | 'max_dd' | 'pct_pos'
  const [selectedCell, setSelectedCell] = useState(null);

  useEffect(() => {
    setCrumbs(
      <>
        <Link to="/groups" style={{ color: "inherit", textDecoration: "none" }}>
          Groups
        </Link>
        <span className="sep">/</span>
        <b>{groupId}</b>
      </>
    );
    return () => setCrumbs(null);
  }, [groupId, setCrumbs]);

  useEffect(() => {
    const title = group?.label || group?.id || groupId || "Group";
    document.title = `${title} · Stolgo`;
  }, [group, groupId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getGroup(groupId)
      .then((data) => {
        if (!cancelled) {
          setGroup(data);
          // Set initial defaults based on available axes
          const axesKeys = Object.keys(data.axes || {});
          if (!axesKeys.includes("family") && axesKeys.length > 0) {
            setRowAxis(axesKeys[0]);
          }
          if (
            (!axesKeys.includes("market") || !axesKeys.includes("dte")) &&
            axesKeys.length > 1
          ) {
            setColAxis(axesKeys[1]);
          }
          // Default selection if available
          setSelectedCell({ row: "A", col: "SENSEX 0-DTE" });
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load group");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [groupId]);

  const axes = group?.axes || {};
  const runs = group?.runs || [];

  // Available column axis options
  const colAxisOptions = useMemo(() => {
    const opts = [];
    const keys = Object.keys(axes);
    if (keys.includes("market") && keys.includes("dte")) {
      opts.push("market × dte");
    }
    keys.forEach((k) => opts.push(k));
    return opts;
  }, [axes]);

  // Derived Rows
  const rows = useMemo(() => {
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
  }, [axes, rowAxis]);

  // Derived Columns
  const cols = useMemo(() => {
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
  }, [axes, colAxis]);

  // Grid cell data mapping
  const cellDataLookup = useMemo(() => {
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
        // worst DD is the most negative (min)
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
  }, [rows, cols, runs, rowAxis, colAxis]);

  const getCellData = (row, colKey) => {
    return cellDataLookup.get(`${row}__${colKey}`) || { count: 0, runs: [] };
  };

  // Min / max metric across entire grid for footer
  const gridExtremes = useMemo(() => {
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
  }, [cellDataLookup, cellMetric]);

  // Selected cell runs
  const selectedRuns = useMemo(() => {
    if (!selectedCell) return [];
    const cell = cellDataLookup.get(`${selectedCell.row}__${selectedCell.col}`);
    if (!cell || !cell.runs) return [];
    return [...cell.runs].sort(
      (a, b) => (b.metrics?.total_return || 0) - (a.metrics?.total_return || 0)
    );
  }, [selectedCell, cellDataLookup]);

  // Remaining axes not in row or column
  const remainingAxes = useMemo(() => {
    const excluded = new Set([rowAxis]);
    if (colAxis === "market × dte") {
      excluded.add("market");
      excluded.add("dte");
    } else {
      excluded.add(colAxis);
    }
    return Object.keys(axes).filter((k) => !excluded.has(k));
  }, [axes, rowAxis, colAxis]);

  // Compare top 4 action
  const handleCompareTop4 = () => {
    if (runs.length === 0) return;
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

    const top4 = sorted.slice(0, 4).map((r) => r.id);
    navigate(`/compare?ids=${top4.join(",")}`);
  };

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <div className="muted">Loading group {groupId}…</div>
      </div>
    );
  }

  if (error || !group) {
    return (
      <div style={{ padding: 24 }}>
        <EmptyState
          title="Group not found"
          description={error || `Could not find group "${groupId}"`}
          action={
            <Button onClick={() => navigate("/groups")}>Back to Groups</Button>
          }
        />
      </div>
    );
  }

  // Window info
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
  const windowStr =
    windowStart && windowEnd ? `${windowStart} → ${windowEnd}` : "—";
  const axesNames = Object.keys(axes).join(", ");

  const metricLabelMap = {
    return: "Mean total return",
    sharpe: "Mean Sharpe ratio",
    max_dd: "Max drawdown (worst)",
    pct_pos: "% positive runs",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Header section */}
      <section style={{ display: "flex", alignItems: "flex-end", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div className="eyebrow">Group</div>
          <h1 style={{ margin: "4px 0 0", fontSize: 28, fontWeight: 600 }}>
            {group.label}
          </h1>
          <div className="muted">
            {runs.length} runs · {windowStr} · axes: {axesNames}
          </div>
        </div>
        <Button onClick={handleCompareTop4}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            style={{ marginRight: 6 }}
          >
            <line x1="8" y1="4" x2="8" y2="20" />
            <line x1="16" y1="4" x2="16" y2="20" />
            <polyline points="4 8 8 4 12 8" />
            <polyline points="12 16 16 20 20 16" />
          </svg>
          Compare top 4
        </Button>
      </section>

      {/* Controls row */}
      <section
        style={{
          display: "flex",
          gap: 10,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <span className="eyebrow">Rows</span>
        <select
          className="select"
          value={rowAxis}
          onChange={(e) => setRowAxis(e.target.value)}
        >
          {Object.keys(axes).map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>

        <span className="eyebrow">Columns</span>
        <select
          className="select"
          value={colAxis}
          onChange={(e) => setColAxis(e.target.value)}
        >
          {colAxisOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>

        <span className="eyebrow">Cell</span>
        <div className="seg">
          <button
            className="seg__item"
            aria-selected={cellMetric === "return"}
            onClick={() => setCellMetric("return")}
          >
            Mean return
          </button>
          <button
            className="seg__item"
            aria-selected={cellMetric === "sharpe"}
            onClick={() => setCellMetric("sharpe")}
          >
            Mean Sharpe
          </button>
          <button
            className="seg__item"
            aria-selected={cellMetric === "max_dd"}
            onClick={() => setCellMetric("max_dd")}
          >
            Max DD
          </button>
          <button
            className="seg__item"
            aria-selected={cellMetric === "pct_pos"}
            onClick={() => setCellMetric("pct_pos")}
          >
            % positive
          </button>
        </div>
      </section>

      {/* Matrix + Knob effects grid */}
      <div
        className="grid"
        style={{ gridTemplateColumns: "minmax(0, 1fr) 400px", gap: "var(--gap)" }}
      >
        {/* Heatmap Panel */}
        <section className="panel">
          <div className="panel__head">
            <span className="eyebrow">
              {metricLabelMap[cellMetric]} · cell label = mean · count
            </span>
          </div>

          <HeatGrid
            rows={rows}
            cols={cols}
            cellData={getCellData}
            cellMetric={cellMetric}
            selectedCell={selectedCell}
            onSelectCell={(r, c) => setSelectedCell({ row: r, col: c })}
          />

          <div
            className="panel__foot"
            style={{ display: "flex", gap: 10, alignItems: "center" }}
          >
            <span
              style={{
                width: 44,
                height: 8,
                borderRadius: 2,
                background: "linear-gradient(90deg,#e07a45,#1a2233,#5ab0ff)",
              }}
            ></span>
            {gridExtremes.minStr} … {gridExtremes.maxStr} · diverging blue/orange
            (colour-blind safe) · click a cell to list its variants
          </div>
        </section>

        {/* Knob Effects Panel */}
        <section className="panel">
          <div className="panel__head">
            <span className="eyebrow">Knob effects</span>
          </div>
          <KnobEffects
            runs={runs}
            axes={axes}
            cols={cols}
            rows={rows}
            rowAxis={rowAxis}
            colAxis={colAxis}
          />
        </section>
      </div>

      {/* Selected Cell Table */}
      <section className="panel panel--flush">
        <div style={{ padding: "12px 16px" }} className="panel__head">
          <span className="eyebrow">
            Selected cell · {rowAxis} {selectedCell ? selectedCell.row : "—"} ×{" "}
            {selectedCell ? selectedCell.col : "—"} · {selectedRuns.length} variants
          </span>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Variant</th>
              {remainingAxes.map((axis) => (
                <th key={axis} className="num">
                  {axis}
                </th>
              ))}
              <th className="num" aria-sort="descending">
                Return
              </th>
              <th className="num">Sharpe</th>
              <th className="num">Max DD</th>
              <th className="num">PF</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {selectedRuns.length === 0 ? (
              <tr>
                <td
                  colSpan={remainingAxes.length + 6}
                  style={{ textAlign: "center", color: "var(--text-3)", padding: 24 }}
                >
                  Select a cell above to inspect variants
                </td>
              </tr>
            ) : (
              selectedRuns.map((r) => {
                // Strip group prefix from ID
                const prefix = `${groupId}-`;
                const variantId = r.id.startsWith(prefix)
                  ? r.id.slice(prefix.length)
                  : r.id;

                const ret = r.metrics?.total_return;
                const sharpeVal = r.metrics?.sharpe;
                const dd = r.metrics?.max_drawdown;
                const pf = r.metrics?.profit_factor;

                return (
                  <tr key={r.id}>
                    <td className="mono">{variantId}</td>
                    {remainingAxes.map((axis) => (
                      <td key={axis} className="num">
                        {r.group?.axes?.[axis] !== null &&
                        r.group?.axes?.[axis] !== undefined
                          ? String(r.group?.axes?.[axis])
                          : "—"}
                      </td>
                    ))}
                    <td className={`num ${ret >= 0 ? "pos" : "neg"}`}>
                      {pct(ret, { signed: true })}
                    </td>
                    <td className="num">{ratio(sharpeVal)}</td>
                    <td className="num neg">{pct(dd)}</td>
                    <td className="num">{ratio(pf)}</td>
                    <td>
                      <Link to={`/runs/${r.id}`}>Open →</Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
