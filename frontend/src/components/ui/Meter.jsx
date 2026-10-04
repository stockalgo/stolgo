import React from "react";

export function Meter({ value = 0, threshold = null, height = 8, className = "" }) {
  const clamped = Math.max(0, Math.min(1, Number(value) || 0));
  const pctVal = clamped * 100;
  const threshPct = threshold !== null ? Math.max(0, Math.min(1, threshold)) * 100 : null;

  return (
    <div
      className={`meter ${className}`}
      style={{
        position: "relative",
        height: `${height}px`,
        background: "var(--bg-raised)",
        borderRadius: "4px",
        overflow: "hidden",
        width: "100%",
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${pctVal}%`,
          background: clamped >= (threshold ?? 0.8) ? "var(--pos)" : "var(--warn)",
          borderRadius: "4px",
          transition: "width 0.2s ease",
        }}
      />
      {threshPct !== null && (
        <div
          style={{
            position: "absolute",
            left: `${threshPct}%`,
            top: 0,
            bottom: 0,
            width: "2px",
            background: "var(--text-1)",
            opacity: 0.6,
          }}
        />
      )}
    </div>
  );
}
