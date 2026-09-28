import React from "react";
import { Chip } from "../ui/Chip.jsx";
import { StatusBadge } from "../ui/StatusBadge.jsx";

export function LibraryFilters({
  market = "All",
  onMarketChange,
  dte = "Any",
  onDteChange,
  structure = "All",
  onStructureChange,
  structureOptions = [],
  statusFilters = ["ok", "low_sample", "short_window", "data_issues"],
  onStatusToggle,
  statusCounts = {},
  groupId = "Any",
  onGroupChange,
  groupOptions = [],
  minTrades = 0,
  onMinTradesChange,
}) {
  const statuses = [
    { key: "ok", label: "OK" },
    { key: "low_sample", label: "Low sample" },
    ...(statusCounts.short_window ? [{ key: "short_window", label: "Short window" }] : []),
    { key: "data_issues", label: "Data issues" },
    { key: "superseded", label: "Superseded" },
    { key: "empty", label: "Empty" },
  ];

  return (
    <aside className="panel" style={{ display: "flex", flexDirection: "column", gap: "18px", alignSelf: "start" }}>
      {/* Market */}
      <div>
        <div className="eyebrow" style={{ marginBottom: "8px" }}>
          Market
        </div>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {["All", "NIFTY", "SENSEX"].map((m) => (
            <Chip
              key={m}
              as="button"
              selected={market === m}
              onClick={() => onMarketChange(m)}
            >
              {m}
            </Chip>
          ))}
        </div>
      </div>

      {/* DTE */}
      <div>
        <div className="eyebrow" style={{ marginBottom: "8px" }}>
          DTE
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          {["Any", "0", "1", "2"].map((d) => (
            <Chip
              key={d}
              as="button"
              selected={String(dte) === d}
              onClick={() => onDteChange(d)}
            >
              {d}
            </Chip>
          ))}
        </div>
      </div>

      {/* Structure */}
      <div>
        <div className="eyebrow" style={{ marginBottom: "8px" }}>
          Structure
        </div>
        <select
          className="select"
          style={{ width: "100%" }}
          value={structure}
          onChange={(e) => onStructureChange(e.target.value)}
        >
          <option value="All">All structures ({structureOptions.reduce((acc, o) => acc + o.count, 0)})</option>
          {structureOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label} ({opt.count})
            </option>
          ))}
        </select>
      </div>

      {/* Status */}
      <div>
        <div className="eyebrow" style={{ marginBottom: "4px" }}>
          Status
        </div>
        {statuses.map((st) => {
          const isChecked = statusFilters.includes(st.key);
          const count = statusCounts[st.key] || 0;
          return (
            <label key={st.key} className="check">
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => onStatusToggle(st.key)}
              />
              <StatusBadge status={st.key} />
              <span className="mono faint" style={{ marginLeft: "auto" }}>
                {count}
              </span>
            </label>
          );
        })}
      </div>

      {/* Group */}
      <div>
        <div className="eyebrow" style={{ marginBottom: "8px" }}>
          Group
        </div>
        <select
          className="select"
          style={{ width: "100%" }}
          value={groupId}
          onChange={(e) => onGroupChange(e.target.value)}
        >
          <option value="Any">Any group</option>
          {groupOptions.map((g) => (
            <option key={g.id} value={g.id}>
              {g.label} ({g.count})
            </option>
          ))}
        </select>
      </div>

      {/* Min trades */}
      <label className="field">
        Min. trades{" "}
        <span className="mono accent" style={{ float: "right" }}>
          {minTrades}
        </span>
        <input
          type="range"
          className="range"
          min="0"
          max="160"
          step="10"
          value={minTrades}
          onChange={(e) => onMinTradesChange(Number(e.target.value))}
        />
      </label>

      {/* Callout */}
      <div className="callout">
        Hollow dots and dimmed rows have fewer than 100 trades.{" "}
        <b>Data issues</b> means more than 5% of trades were forced out by missing market data.
      </div>
    </aside>
  );
}
