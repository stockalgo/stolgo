import React, { useState, useCallback, useMemo } from "react";
import { useOutletContext } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { getTrades, getMonthly } from "../api/endpoints.js";
import { OverviewKpis } from "../components/overview/OverviewKpis.jsx";
import { EdgeIntegrity } from "../components/overview/EdgeIntegrity.jsx";
import { Histogram } from "../components/overview/Histogram.jsx";
import { MonthlyHeatmap } from "../components/overview/MonthlyHeatmap.jsx";
import { ChartPanel } from "../components/chart/ChartPanel.jsx";
import { TradeInspector } from "../components/inspector/TradeInspector.jsx";

export function RunOverviewPage() {
  const { run } = useOutletContext();
  const [selectedTradeId, setSelectedTradeId] = useState(null);

  const fetchTrades = useCallback(() => (run?.id ? getTrades(run.id) : Promise.resolve([])), [run?.id]);
  const fetchMonthly = useCallback(() => (run?.id ? getMonthly(run.id) : Promise.resolve([])), [run?.id]);

  const { data: rawTrades } = useApi(`run:${run?.id}:trades`, fetchTrades, [run?.id]);
  const { data: rawMonthly } = useApi(`run:${run?.id}:monthly`, fetchMonthly, [run?.id]);

  const trades = useMemo(
    () => (Array.isArray(rawTrades) ? rawTrades : rawTrades?.rows || []),
    [rawTrades]
  );
  const monthly = useMemo(
    () => (Array.isArray(rawMonthly) ? rawMonthly : rawMonthly?.rows || []),
    [rawMonthly]
  );

  if (!run) return null;

  const currentTradeId =
    selectedTradeId ?? (trades && trades.length > 0 ? trades[trades.length - 1].trade_id : null);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {/* Row 1: KPI Strip (6 cells) */}
      <OverviewKpis run={run} />

      {/* Row 2: Chart panel (left) + EdgeIntegrity (right, 330px) */}
      <div
        className="grid"
        style={{ gridTemplateColumns: "minmax(0, 1fr) 330px", gap: "14px" }}
      >
        <ChartPanel
          run={run}
          trades={trades || []}
          selectedTradeId={currentTradeId}
          onSelectTrade={setSelectedTradeId}
        />
        <EdgeIntegrity run={run} />
      </div>

      {/* Row 3: Histogram (300px) + MonthlyHeatmap (center) + TradeInspector (right, 560px) */}
      <div
        className="grid"
        style={{ gridTemplateColumns: "300px minmax(0, 1fr) 560px", gap: "14px" }}
      >
        <Histogram trades={trades || []} />
        <MonthlyHeatmap monthly={monthly || []} />
        <TradeInspector
          runId={run.id}
          trades={trades || []}
          selectedTradeId={currentTradeId}
          onSelectTrade={setSelectedTradeId}
        />
      </div>
    </div>
  );
}
