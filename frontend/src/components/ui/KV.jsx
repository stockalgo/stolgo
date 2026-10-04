import React from "react";

export function KV({
  label,
  value,
  sub = null,
  pos = false,
  neg = false,
  muted = false,
  children,
  className = "",
}) {
  const valueClass = [
    pos ? "pos" : "",
    neg ? "neg" : "",
    muted ? "muted" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={`kv ${className}`}>
      <span>{label}</span>
      {children ? (
        <span>{children}</span>
      ) : (
        <span className={valueClass}>
          {value}
          {sub && <span style={{ fontSize: "11px", marginLeft: "4px", color: "var(--text-muted)" }}>{sub}</span>}
        </span>
      )}
    </div>
  );
}
