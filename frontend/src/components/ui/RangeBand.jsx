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
  showTicks = true,
}) {
  const range = max - min || 1;
  const toPct = (val) => Math.max(0, Math.min(100, ((val - min) / range) * 100));

  const startPct = toPct(p05);
  const endPct = toPct(p95);
  const pointPct = toPct(point);
  const breakEvenPct = toPct(breakEven);

  // Band boundaries clamped strictly inside [0, 100]
  const bandLeft = Math.max(0, Math.min(100, startPct));
  const bandWidth = Math.max(2, Math.min(100 - bandLeft, endPct - bandLeft));

  return (
    <div className={`range-band-container ${className}`} style={{ width: "100%" }}>
      <div
        className="range-band"
        style={{
          position: "relative",
          height: `${height}px`,
          background: "var(--bg-raised)",
          borderRadius: "4px",
          width: "100%",
          display: "flex",
          alignItems: "center",
          overflow: "hidden",
        }}
      >
        {/* Ticks at 0, 1, max */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: "1px",
            background: "var(--line)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: `${breakEvenPct}%`,
            top: 0,
            bottom: 0,
            width: "2px",
            background: "var(--neg)",
            zIndex: 1,
          }}
          title={`Break-even: ${breakEven}`}
        />
        <div
          style={{
            position: "absolute",
            right: 0,
            top: 0,
            bottom: 0,
            width: "1px",
            background: "var(--line)",
          }}
        />

        {/* 90% band */}
        <div
          style={{
            position: "absolute",
            left: `${bandLeft}%`,
            width: `${bandWidth}%`,
            height: "8px",
            background: "var(--accent)",
            opacity: 0.35,
            borderRadius: "4px",
          }}
        />

        {/* Point estimate dot */}
        {point !== null && point !== undefined && (
          <div
            style={{
              position: "absolute",
              left: `clamp(5px, ${pointPct}%, calc(100% - 5px))`,
              top: "50%",
              transform: "translate(-50%, -50%)",
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: "var(--accent)",
              border: "2px solid var(--bg-panel)",
              zIndex: 2,
            }}
            title={`Point: ${point}`}
          />
        )}
      </div>

      {/* Ticks labels at 0, 1, and max */}
      {showTicks && (
        <div
          style={{
            position: "relative",
            display: "flex",
            justifyContent: "space-between",
            fontSize: "10px",
            color: "var(--text-faint)",
            marginTop: "3px",
            fontFamily: "var(--font-mono)",
            height: "14px",
          }}
        >
          <span>{min}</span>
          <span
            style={{
              position: "absolute",
              left: `${breakEvenPct}%`,
              transform: "translateX(-50%)",
            }}
          >
            {breakEven % 1 === 0 ? breakEven.toFixed(0) : breakEven.toFixed(1)}
          </span>
          <span>{max % 1 === 0 ? max : max.toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}
