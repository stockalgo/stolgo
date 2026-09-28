import React from "react";

export function HBar({
  label,
  count,
  pct = 0,
  color = "var(--text-3)",
  labelWidth = 96,
  className = "",
}) {
  const clampedPct = Math.max(0, Math.min(100, Number(pct) || 0));

  return (
    <div
      className={`hbar-row ${className}`}
      style={{
        display: "grid",
        gridTemplateColumns: `${labelWidth}px 1fr 70px`,
        gap: "10px",
        alignItems: "center",
        fontSize: "12px",
        height: "22px",
      }}
    >
      <span
        style={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: "var(--text-2)",
        }}
        title={label}
      >
        {label}
      </span>
      <div
        style={{
          height: "6px",
          background: "var(--bg-raised)",
          borderRadius: "3px",
          overflow: "hidden",
          width: "100%",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${clampedPct}%`,
            background: color,
            borderRadius: "3px",
          }}
        />
      </div>
      <span className="mono" style={{ textAlign: "right", color: "var(--text-muted)" }}>
        {count !== undefined && count !== null ? `${count} · ` : ""}
        {Math.round(clampedPct)}%
      </span>
    </div>
  );
}
