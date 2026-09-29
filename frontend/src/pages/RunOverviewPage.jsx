import React, { useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { getTrades, getMonthly } from "../api/endpoints.js";
import { OverviewKpis } from "../components/overview/OverviewKpis.jsx";
import { EdgeIntegrity } from "../components/overview/EdgeIntegrity.jsx";
import { Histogram } from "../components/overview/Histogram.jsx";
import { MonthlyHeatmap } from "../components/overview/MonthlyHeatmap.jsx";
import { ChartPanel } from "../components/chart/ChartPanel.jsx";

export function RunOverviewPage() {
  const { run } = useOutletContext();

  const fetchTrades = useCallback(() => (run?.id ? getTrades(run.id) : Promise.resolve([])), [run?.id]);
  const fetchMonthly = useCallback(() => (run?.id ? getMonthly(run.id) : Promise.resolve([])), [run?.id]);

  const { data: trades } = useApi(fetchTrades);
  const { data: monthly } = useApi(fetchMonthly);

  if (!run) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {/* Row 1: KPI Strip (6 cells) */}
      <OverviewKpis run={run} />

      {/* Row 2: Chart panel (left) + EdgeIntegrity (right, 330px) */}
      <div
        className="grid"
        style={{ gridTemplateColumns: "minmax(0, 1fr) 330px", gap: "14px" }}
      >
        <ChartPanel run={run} trades={trades || []} />
        <EdgeIntegrity run={run} />
      </div>

      {/* Row 3: Histogram (300px) + MonthlyHeatmap (center) + TradeInspector (right, 560px) */}
      <div
        className="grid"
        style={{ gridTemplateColumns: "300px minmax(0, 1fr) 560px", gap: "14px" }}
      >
        <Histogram trades={trades || []} />
        <MonthlyHeatmap monthly={monthly || []} />

        <section
          className="panel"
          style={{ display: "flex", flexDirection: "column", gap: "8px" }}
        >
          <div className="panel__head" style={{ margin: 0 }}>
            <span className="eyebrow">Trade inspector</span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flex: 1,
              minHeight: "220px",
            }}
            className="muted"
          >
            Trade inspector (U9)
          </div>
        </section>
      </div>
    </div>
  );
}
