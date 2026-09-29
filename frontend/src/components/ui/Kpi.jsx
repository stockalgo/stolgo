import React from "react";
import { Skeleton } from "./Skeleton.jsx";

export function Kpi({
  label,
  value,
  sub,
  pos = false,
  neg = false,
  muted = false,
  warn = false,
  warnTooltip = "",
  loading = false,
  tooltip = "",
  className = "",
}) {
  if (loading) {
    return (
      <div className={`kpi ${className}`}>
        <div className="kpi__label" title={tooltip}>
          {label}
        </div>
        <Skeleton style={{ height: "28px", marginTop: "6px", width: "80%" }} />
        <Skeleton style={{ height: "12px", marginTop: "8px", width: "50%" }} />
      </div>
    );
  }

  const valueClass = [
    "kpi__value",
    pos ? "pos" : "",
    neg ? "neg" : "",
    muted ? "muted" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const subClass = ["kpi__sub", warn ? "kpi__warn" : ""].filter(Boolean).join(" ");

  return (
    <div className={`kpi ${className}`}>
      <div className="kpi__label" title={tooltip}>
        {label}
        {warn && (
          <span className="accent" title={warnTooltip} style={{ marginLeft: "4px" }}>
            ⚠
          </span>
        )}
      </div>
      <div className={valueClass}>{value}</div>
      {sub && <div className={subClass}>{sub}</div>}
    </div>
  );
}

export function KpiStrip({ items, children, className = "" }) {
  return (
    <section className={`kpis ${className}`}>
      {items
        ? items.map((it, idx) => (
            <Kpi
              key={idx}
              label={it.label}
              value={it.value}
              sub={it.sub}
              pos={it.pos || it.className === "pos"}
              neg={it.neg || it.className === "neg"}
              muted={it.muted || it.className === "muted"}
              warn={it.warn}
              warnTooltip={it.warnTooltip}
              loading={it.loading}
              tooltip={it.tooltip}
              className={it.className}
            />
          ))
        : children}
    </section>
  );
}
