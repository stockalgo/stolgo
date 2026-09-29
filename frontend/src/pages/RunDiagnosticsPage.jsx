import React, { useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { getTrades, getMonthly } from "../api/endpoints.js";
import { DataCoverage } from "../components/diagnostics/DataCoverage.jsx";
import { ExitReasons } from "../components/diagnostics/ExitReasons.jsx";
import { CostBreakdown } from "../components/diagnostics/CostBreakdown.jsx";
import { Stability } from "../components/diagnostics/Stability.jsx";
import { Extremes } from "../components/diagnostics/Extremes.jsx";
import { MonthlyConsistency } from "../components/diagnostics/MonthlyConsistency.jsx";
import { ValidationConfig } from "../components/diagnostics/ValidationConfig.jsx";

export function RunDiagnosticsPage() {
  const { run } = useOutletContext();

  const fetchTrades = useCallback(
    () => (run?.id ? getTrades(run.id) : Promise.resolve([])),
    [run?.id]
  );
  const fetchMonthly = useCallback(
    () => (run?.id ? getMonthly(run.id) : Promise.resolve([])),
    [run?.id]
  );

  const { data: rawTrades } = useApi(fetchTrades);
  const { data: rawMonthly } = useApi(fetchMonthly);

  const trades = Array.isArray(rawTrades) ? rawTrades : rawTrades?.rows || [];
  const monthly = Array.isArray(rawMonthly) ? rawMonthly : rawMonthly?.rows || [];

  if (!run) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {/* 2 rows of 3 columns = 6 panels */}
      <div
        className="grid"
        style={{
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: "14px",
        }}
      >
        <DataCoverage run={run} />
        <ExitReasons run={run} trades={trades || []} />
        <CostBreakdown run={run} trades={trades || []} />
        <Stability run={run} trades={trades || []} />
        <Extremes run={run} />
        <MonthlyConsistency run={run} monthly={monthly || []} />
      </div>

      {/* Row 3: Full-width Validation, execution & configuration */}
      <ValidationConfig run={run} />
    </div>
  );
}
