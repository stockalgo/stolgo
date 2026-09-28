import React from "react";
import { StatusBadge } from "../ui/StatusBadge.jsx";
import { VerdictPill } from "../ui/VerdictPill.jsx";
import { Chip } from "../ui/Chip.jsx";
import { inr, sessionLabel, sessions } from "../../lib/format.js";

export function RunHeader({ run }) {
  if (!run) return null;

  const marketsStr = (run.markets || []).join(" + ");
  const rawStructure = run.structure || "";
  const structureLabel = rawStructure
    ? rawStructure.charAt(0).toUpperCase() + rawStructure.slice(1).replace(/_/g, " ")
    : "";
  const dteStr = (run.dte || []).join(",") + " DTE";
  const numTrades = run.metrics?.num_trades ?? 0;
  const startStr = sessionLabel(run.window?.start);
  const endStr = sessionLabel(run.window?.end);
  const sessCount = sessions(run.window?.sessions);
  const capitalVal = run.capital ?? run.config?.capital ?? 0;

  // Timing from diagnostics if present and uniform
  const timing = run.diagnostics?.timing || run.diagnostics?.common_timing;
  const showTiming = Boolean(timing?.entry && timing?.exit);

  return (
    <section className="run-head" style={{ display: "flex", alignItems: "flex-start", gap: "16px" }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Line 1: StatusBadge + eyebrow */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <StatusBadge status={run.status} reasons={run.status_reasons} />
          <span className="eyebrow">Run · {run.id}</span>
        </div>

        {/* H1: name */}
        <h1
          className="run-head__title"
          style={{ margin: "6px 0 0", fontSize: "30px", fontWeight: 600 }}
        >
          {run.name || run.id}
        </h1>

        {/* Chips */}
        <div className="run-head__chips" style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
          {marketsStr && <Chip>{marketsStr}</Chip>}
          {(structureLabel || dteStr) && (
            <Chip>{structureLabel ? `${structureLabel} · ${dteStr}` : dteStr}</Chip>
          )}
          <Chip>{numTrades} trades</Chip>
          {run.window?.start && run.window?.end && (
            <Chip>
              {startStr} → {endStr} · {sessCount}
            </Chip>
          )}
          <Chip>Capital {inr(capitalVal)}</Chip>
          {showTiming && (
            <Chip>
              Entry {timing.entry} · Exit {timing.exit} IST
            </Chip>
          )}
        </div>
      </div>

      {/* Right side: VerdictPill */}
      <VerdictPill run={run} />
    </section>
  );
}
