import React from "react";
import { Banner } from "../ui/Banner.jsx";

export function DataCoverage({ run }) {
  const diag = run?.diagnostics || {};
  const dq = diag.data_quality || run?.data_quality || {};

  const tradesTotal = dq.trades_total ?? run?.metrics?.num_trades ?? 0;
  const missingTrades = dq.trades_with_missing_data ?? 0;
  const missingPct =
    tradesTotal > 0
      ? ((missingTrades / tradesTotal) * 100).toFixed(1)
      : "0.0";

  const eligibleSessions = dq.eligible_sessions ?? "—";
  const tradedSessions = dq.traded_sessions ?? tradesTotal;
  const skippedSessions = dq.skipped_sessions ?? 0;
  const unresolved = dq.unresolved_sessions ?? dq.unresolved_pnl ?? 0;
  const missingReasons = dq.missing_reasons || {};

  const isDataIssues = run?.status === "data_issues";

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="eyebrow">Data coverage</span>
      </div>

      {missingTrades > 0 && (
        <Banner variant="warn" style={{ marginBottom: "12px" }}>
          <span>
            <b>
              {missingTrades} of {tradesTotal} trades ({missingPct}%)
            </b>{" "}
            exited because market data went missing. Their P&amp;L is known but was
            forced.
            {isDataIssues && (
              <>
                {" "}
                Status: <b>DATA ISSUES</b>.
              </>
            )}
          </span>
        </Banner>
      )}

      <div className="kv kv--divided">
        <span>Eligible sessions</span>
        <span>{eligibleSessions}</span>
      </div>
      <div className="kv kv--divided">
        <span>Traded</span>
        <span>{tradedSessions}</span>
      </div>
      <div className="kv kv--divided">
        <span>Skipped</span>
        <span>{skippedSessions}</span>
      </div>
      <div className="kv kv--divided">
        <span>Unresolved P&amp;L</span>
        <span className={unresolved === 0 ? "pos" : "neg"}>{unresolved}</span>
      </div>

      {Object.entries(missingReasons).map(([key, count], index, arr) => (
        <div
          key={key}
          className={`kv ${index < arr.length - 1 ? "kv--divided" : ""}`}
        >
          <span>Forced exit &middot; {key}</span>
          <span className="accent">{count}</span>
        </div>
      ))}
    </section>
  );
}
