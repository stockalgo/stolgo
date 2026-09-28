import React from "react";
import { Button } from "./Button.jsx";

export function EmptyState({
  title,
  children,
  action,
  variant = "default", // "default" | "not-migrated" | "error" | "no-trades" | "no-price"
  className = "",
  style = {},
}) {
  let content = children;
  let computedTitle = title;
  let computedAction = action;
  let customStyle = { ...style };

  if (variant === "not-migrated") {
    computedTitle = title || "Run not migrated";
    content = (
      <>
        This run still uses the v1 manifest. Run
        <br />
        <span className="mono">python scripts/migrate_runs_v2.py</span>
      </>
    );
  } else if (variant === "error") {
    computedTitle = title || "Can’t reach the API";
    customStyle = { borderColor: "rgba(229, 72, 77, 0.4)", ...customStyle };
    if (!action) {
      computedAction = (
        <Button size="sm" onClick={() => window.location.reload()}>
          Retry
        </Button>
      );
    }
  } else if (variant === "no-trades") {
    computedTitle = title || "No trades";
    content = content || "The strategy never entered. Check the signal funnel in Diagnostics.";
  } else if (variant === "no-price") {
    computedTitle = title || "No price data for this run";
    content = (
      <>
        The generator did not export <span className="mono">ohlcv.parquet</span>. Equity and trades
        are still available.
      </>
    );
  }

  return (
    <div className={`empty-state ${className}`} style={customStyle}>
      {computedTitle && <div className="empty-state__title">{computedTitle}</div>}
      {content && <div>{content}</div>}
      {computedAction && <div>{computedAction}</div>}
    </div>
  );
}
