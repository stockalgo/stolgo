import React from "react";
import { getStatusBadge } from "../../lib/verdict.js";

export function StatusBadge({ status, tooltip, className = "" }) {
  const badgeInfo = getStatusBadge(status);
  return (
    <span
      className={`badge ${badgeInfo.className} ${className}`}
      title={tooltip}
    >
      {badgeInfo.label}
    </span>
  );
}
