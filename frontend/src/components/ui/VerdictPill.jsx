import React from "react";
import { getVerdict } from "../../lib/verdict.js";

export function VerdictPill({ run, verdict: overrideVerdict, className = "" }) {
  const v = overrideVerdict || getVerdict(run);

  let variantClass = "";
  let styleOverride = {};

  if (v.style === "green") {
    variantClass = "verdict--ok";
  } else if (v.style === "red") {
    variantClass = "verdict--bad";
  } else if (v.style === "muted") {
    styleOverride = { borderColor: "var(--line-strong)", background: "transparent" };
  }

  const dotStyle = v.style === "muted" ? { background: "var(--text-muted)" } : {};
  const textStyle = v.style === "muted" ? { color: "var(--text-muted)" } : {};

  return (
    <div className={`verdict ${variantClass} ${className}`} style={styleOverride}>
      <span className="verdict__dot" style={dotStyle} />
      <div>
        <div className="verdict__label" style={textStyle}>
          {v.label}
        </div>
        <div className="verdict__text" style={textStyle}>
          {v.text}
        </div>
      </div>
    </div>
  );
}
