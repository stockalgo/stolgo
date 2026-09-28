import React from "react";

export function RangeBand({
  p05 = 0,
  p95 = 3,
  point = 1.3,
  min = 0,
  max = 3,
  breakEven = 1.0,
  height = 20,
  className = "",
}) {
  const range = max - min || 1;
  const toPct = (val) => Math.max(0, Math.min(100, ((val - min) / range) * 100));

  const startPct = toPct(p05);
  const endPct = toPct(p95);
  const pointPct = toPct(point);
  const breakEvenPct = toPct(breakEven);

  return (
    <div
      className={`range-band ${className}`}
      style={{
        position: "relative",
        height: `${height}px`,
        background: "var(--bg-raised)",
        borderRadius: "4px",
        width: "100%",
        display: "flex",
        alignItems: "center",
      }}
    >
      {/* 90% band */}
      <div
        style={{
          position: "absolute",
          left: `${startPct}%`,
          width: `${Math.max(2, endPct - startPct)}%`,
          height: "8px",
          background: "var(--accent)",
          opacity: 0.35,
          borderRadius: "4px",
        }}
      />
      {/* Break-even line */}
      <div
        style={{
          position: "absolute",
          left: `${breakEvenPct}%`,
          top: 0,
          bottom: 0,
          width: "2px",
          background: "var(--neg)",
        }}
        title={`Break-even: ${breakEven}`}
      />
      {/* Point estimate dot */}
      {point !== null && point !== undefined && (
        <div
          style={{
            position: "absolute",
            left: `${pointPct}%`,
            top: "50%",
            transform: "translate(-50%, -50%)",
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: "var(--accent)",
            border: "2px solid var(--bg-panel)",
          }}
          title={`Point: ${point}`}
        />
      )}
    </div>
  );
}
