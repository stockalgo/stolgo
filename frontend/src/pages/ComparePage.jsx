import React, { useState, useEffect, useMemo } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { getRun, getDaily, listRuns } from "../api/endpoints.js";
import { seriesColor } from "../lib/colors.js";
import { isComparable } from "../lib/verdict.js";
import {
  formatMonthYear,
  parseRunIds,
  getMetricValue,
  isBestValue,
  COMPARE_METRICS,
} from "../lib/compareLogic.js";
import { StatusBadge } from "../components/ui/StatusBadge.jsx";
import { Banner } from "../components/ui/Banner.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { Button } from "../components/ui/Button.jsx";
import { CompareChart } from "../components/chart/CompareChart.jsx";
import { copyText } from "../lib/clipboard.js";

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [metricMode, setMetricMode] = useState("% return");
  const [copiedLink, setCopiedLink] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [allAvailableRuns, setAllAvailableRuns] = useState([]);

  const idsParam = searchParams.get("ids") || "";
  const runIds = useMemo(() => parseRunIds(idsParam), [idsParam]);

  const [loadedData, setLoadedData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.title = "Compare · Stolgo";
  }, []);

  // Fetch runs and daily data in parallel
  useEffect(() => {
    if (runIds.length === 0) {
      setLoadedData([]);
      return;
    }
    let cancelled = false;
    setLoading(true);

    Promise.all(
      runIds.map((id, index) =>
        Promise.all([
          getRun(id).catch(() => null),
          getDaily(id).catch(() => ({ rows: [] })),
        ]).then(([run, daily]) => ({
          run: run || { id, name: id, metrics: {}, window: {} },
          daily: daily || { rows: [] },
          slotIndex: index,
          color: seriesColor(index),
        }))
      )
    ).then((results) => {
      if (!cancelled) {
        setLoadedData(results);
        setLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [idsParam, runIds]);

  // Fetch all runs for the Add Run picker
  useEffect(() => {
    if (showAddModal && allAvailableRuns.length === 0) {
      listRuns().then((res) => {
        setAllAvailableRuns(res?.items || []);
      });
    }
  }, [showAddModal, allAvailableRuns.length]);

  const handleCopyLink = async () => {
    const success = await copyText(window.location.href);
    if (success) {
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  const handleRemoveRun = (idToRemove) => {
    const nextIds = runIds.filter((id) => id !== idToRemove);
    setSearchParams(nextIds.length > 0 ? { ids: nextIds.join(",") } : {});
  };

  const handleAddRun = (newId) => {
    if (!newId || runIds.includes(newId) || runIds.length >= 4) return;
    const nextIds = [...runIds, newId];
    setSearchParams({ ids: nextIds.join(",") });
    setShowAddModal(false);
  };

  if (runIds.length < 2) {
    return (
      <div>
        <section
          style={{
            display: "flex",
            alignItems: "flex-end",
            gap: "16px",
            marginBottom: "16px",
          }}
        >
          <div style={{ flex: 1 }}>
            <div className="eyebrow">Compare</div>
            <h1 style={{ margin: "4px 0 0", fontSize: "28px", fontWeight: 600 }}>
              Compare runs
            </h1>
          </div>
        </section>
        <EmptyState
          title="Pick at least two runs"
          action={
            <Button variant="primary" onClick={() => navigate("/")}>
              Go to Library
            </Button>
          }
        >
          Select runs from the Library table or enter their IDs to compare side by side.
        </EmptyState>
      </div>
    );
  }

  const runs = loadedData.map((d) => d.run);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {/* Header */}
      <section style={{ display: "flex", alignItems: "flex-end", gap: "16px" }}>
        <div style={{ flex: 1 }}>
          <div className="eyebrow">Compare</div>
          <h1 style={{ margin: "4px 0 0", fontSize: "28px", fontWeight: 600 }}>
            {runIds.length} runs, one calendar
          </h1>
        </div>
        <Button size="sm" onClick={handleCopyLink} aria-label="Copy link">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V5a1 1 0 0 1 1-1h10" />
          </svg>
          {copiedLink ? "Copied link!" : "Copy link"}
        </Button>
      </section>

      {/* Chips Row */}
      <section style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
        {loadedData.map(({ run, color }) => (
          <span
            key={run.id}
            className="chip chip--on"
            style={{ height: "30px", display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            <span className="dot" style={{ background: color }} />
            {run.name || run.id}
            <button
              type="button"
              className="btn btn--ghost icon-btn"
              style={{ width: "18px", height: "18px", padding: 0 }}
              aria-label={`Remove ${run.name || run.id}`}
              onClick={() => handleRemoveRun(run.id)}
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="6" y1="6" x2="18" y2="18" />
                <line x1="18" y1="6" x2="6" y2="18" />
              </svg>
            </button>
          </span>
        ))}

        {runIds.length < 4 && (
          <Button size="sm" onClick={() => setShowAddModal(true)}>
            + Add run
          </Button>
        )}

        <span className="muted" style={{ fontSize: "12px", marginLeft: "auto" }}>
          Max 4 &middot; colours are fixed by slot
        </span>
      </section>

      {/* Non-comparable Warning Banners */}
      {runs.map((r) => {
        if (!r || isComparable(r)) return null;
        const sDate = formatMonthYear(r.window?.start);
        const eDate = formatMonthYear(r.window?.end);
        const winStr = sDate && eDate ? ` (${sDate}–${eDate})` : "";
        const sess = r.window?.sessions ?? "—";
        const trades = r.metrics?.num_trades ?? "—";

        return (
          <Banner key={r.id} variant="warn">
            <b>{r.name || r.id}</b> covers {sess} sessions{winStr} and {trades} trades.
            Its CAGR and Sharpe are annualised from a short window and are not comparable
            to the 3-year runs.
          </Banner>
        );
      })}

      {/* Compare Chart Panel */}
      <section className="panel">
        <div className="panel__head">
          <span className="eyebrow">
            Cumulative return on capital &middot; daily, aligned by date
          </span>
          <div className="seg seg--mono">
            {["% return", "₹ P&L"].map((m) => (
              <button
                key={m}
                type="button"
                className={`seg__item ${metricMode === m ? "seg__item--active" : ""}`}
                aria-selected={metricMode === m}
                onClick={() => setMetricMode(m)}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <CompareChart
          runsWithDaily={loadedData}
          metricMode={metricMode}
        />
      </section>

      {/* Comparison Table */}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Metric</th>
              {loadedData.map(({ run, color }) => (
                <th
                  key={run.id}
                  className="num"
                  style={{
                    textTransform: "none",
                    letterSpacing: 0,
                    fontFamily: "var(--font-sans)",
                    fontSize: "12px",
                    color: "var(--text-1)",
                  }}
                >
                  <span
                    style={{
                      display: "inline-block",
                      width: "10px",
                      height: "10px",
                      borderRadius: "2px",
                      background: color,
                      marginRight: "6px",
                    }}
                  />
                  {run.name || run.id}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Status */}
            <tr>
              <td style={{ color: "var(--text-2)" }}>Status</td>
              {runs.map((r) => (
                <td key={r.id}>
                  <StatusBadge status={r.status} />
                </td>
              ))}
            </tr>

            {/* Trades */}
            <tr>
              <td style={{ color: "var(--text-2)" }}>Trades</td>
              {runs.map((r) => {
                const comp = isComparable(r);
                return (
                  <td key={r.id} className="num">
                    {r.metrics?.num_trades ?? "—"}
                    {!comp && <span className="accent"> ⚠</span>}
                  </td>
                );
              })}
            </tr>

            {/* Sessions in window */}
            <tr>
              <td style={{ color: "var(--text-2)" }}>Sessions in window</td>
              {runs.map((r) => (
                <td key={r.id} className="num">
                  {r.window?.sessions ?? "—"}
                </td>
              ))}
            </tr>

            {/* Structured metric rows */}
            {COMPARE_METRICS.map(({ key, label, format, direction, warnIf, warnTitle }) => (
              <tr key={key}>
                <td style={{ color: "var(--text-2)" }}>{label}</td>
                {runs.map((r) => {
                  const val = getMetricValue(r, key);
                  const isBest = isBestValue(r, key, runs, direction);
                  const showWarn = warnIf && warnIf(r);
                  return (
                    <td
                      key={r.id}
                      className="num"
                      style={
                        isBest
                          ? {
                              color: "var(--text-1)",
                              fontWeight: 600,
                              background: "rgba(245,165,36,.07)",
                            }
                          : {}
                      }
                    >
                      {format(val)}
                      {showWarn && (
                        <span className="accent" title={warnTitle}>
                          {" "}⚠
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footnote */}
      <div className="muted" style={{ fontSize: "12px" }}>
        The best value in each row is highlighted, counting only runs with &ge; 100
        trades and &ge; 252 sessions. Values from runs below those limits are marked
        &#9888; and never highlighted. &mdash; means the metric is not recorded for
        that run.
      </div>

      {/* Add Run Picker Modal */}
      {showAddModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
          onClick={() => setShowAddModal(false)}
        >
          <div
            className="panel"
            style={{
              width: "480px",
              maxHeight: "80vh",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel__head" style={{ margin: 0 }}>
              <span className="eyebrow">Select run to compare</span>
              <button
                type="button"
                className="btn btn--ghost icon-btn"
                onClick={() => setShowAddModal(false)}
              >
                &times;
              </button>
            </div>
            <div style={{ overflow: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "4px" }}>
              {allAvailableRuns
                .filter((r) => !runIds.includes(r.id))
                .slice(0, 50)
                .map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    className="btn btn--ghost"
                    style={{ justifyContent: "flex-start", textAlign: "left" }}
                    onClick={() => handleAddRun(r.id)}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{r.name || r.id}</div>
                      <div className="muted" style={{ fontSize: "11px" }}>
                        {r.id} &middot; {r.metrics?.num_trades ?? 0} trades
                      </div>
                    </div>
                  </button>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
