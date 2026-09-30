import React, { useState } from "react";
import { inr } from "../../lib/format.js";
import { copyText } from "../../lib/clipboard.js";

export function ValidationConfig({ run }) {
  const [copied, setCopied] = useState(false);

  const handleCopyManifest = async () => {
    if (!run) return;
    const success = await copyText(JSON.stringify(run, null, 2));
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const diag = run?.diagnostics || {};
  const validation = diag.validation || {};
  const limitations = validation.limitations || [];
  const caveats = validation.caveats || [];

  const executionModel = run?.config?.execution ?? null;

  const win = run?.window || {};
  const windowStr =
    win.start && win.end ? `${win.start} to ${win.end}` : "—";
  const windowDetailStr =
    win.start && win.end
      ? `${win.start} \u2192 ${win.end} (${win.sessions ?? "—"} sessions)`
      : "null \u2190 not recorded by generator";

  const metricBasis = run?.metrics?.basis ?? null;
  const equityBasis = run?.metrics?.equity_basis ?? run?.equity_basis ?? null;
  const orders = diag.orders ?? run?.metrics?.orders;
  const validationStatus = validation.status ?? run?.validation_status;

  // Configuration strings for the code view
  const inst = run?.instrument || {};
  const markets = (run?.markets || inst.markets || []).join(", ");
  const structure = run?.structure || inst.structure || "";
  const dte = (run?.dte || inst.dte || []).join(", ");
  const instStr =
    markets || structure || dte
      ? `${markets || "—"}${structure ? ` \u00b7 ${structure}` : ""}${
          dte ? ` \u00b7 dte [${dte}]` : ""
        }`
      : "null \u2190 not recorded by generator";

  const group = run?.group || {};
  const groupLabel = group.label || group.id || "";
  const family = group.axes?.family || "";
  const groupStr =
    group?.id
      ? `${groupLabel}${family ? ` \u00b7 family ${family}` : ""}`
      : "none";

  const cap = run?.capital ?? run?.config?.capital;
  const capitalStr = cap != null ? inr(cap) : "null \u2190 not recorded by generator";

  const costModel = run?.config?.cost_model || null;
  const costStr = costModel
    ? JSON.stringify(costModel)
    : "null   \u2190 not recorded by generator";

  const dataSource = run?.data_source || run?.config?.data_source || null;
  const sourceStr = dataSource || "null  \u2190 not recorded by generator";

  const codeVersion = run?.code_version || run?.config?.code_version || null;
  const versionStr = codeVersion || "null";

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="eyebrow">Validation, execution &amp; configuration</span>
        <button
          type="button"
          className="btn btn--sm"
          onClick={handleCopyManifest}
          aria-label="Copy manifest JSON"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V5a1 1 0 0 1 1-1h10" />
          </svg>
          {copied ? "Copied manifest JSON" : "Copy manifest JSON"}
        </button>
      </div>

      <div
        className="grid"
        style={{
          gridTemplateColumns: "minmax(0, 1.2fr) minmax(0, 1fr)",
          gap: "16px",
        }}
      >
        {/* Left Side: KV + details + caveats */}
        <div>
          <div className="kv kv--divided">
            <span>Execution model</span>
            <span
              style={{
                fontFamily: "var(--font-sans)",
                textAlign: "right",
                maxWidth: "340px",
              }}
            >
              {executionModel ? (
                executionModel
              ) : (
                <span>
                  — <span className="muted" style={{ fontWeight: "normal" }}>not recorded by generator</span>
                </span>
              )}
            </span>
          </div>

          <div className="kv kv--divided">
            <span>Window</span>
            <span>{windowStr}</span>
          </div>

          <div className="kv kv--divided">
            <span>Metric basis</span>
            <span>
              {metricBasis ? (
                <span className="badge badge--info">{metricBasis}</span>
              ) : (
                "—"
              )}
            </span>
          </div>

          <div className="kv kv--divided">
            <span>Equity basis</span>
            <span>
              {equityBasis ? (
                <span className="badge badge--info">{equityBasis}</span>
              ) : (
                "—"
              )}
            </span>
          </div>

          {orders != null && (
            <div className="kv kv--divided">
              <span>Orders</span>
              <span>{orders}</span>
            </div>
          )}

          {validationStatus != null && (
            <div className="kv kv--divided">
              <span>Validation status</span>
              <span>{validationStatus}</span>
            </div>
          )}

          {limitations.length > 0 && (
            <details style={{ marginTop: "10px" }}>
              <summary>Model limitations ({limitations.length})</summary>
              {limitations.map((lim, i) => (
                <p key={i} className="muted" style={{ margin: "4px 0" }}>
                  {lim}
                </p>
              ))}
            </details>
          )}

          {caveats.map((c, i) => (
            <div
              key={i}
              className="callout callout--warn"
              style={{ marginTop: "10px" }}
            >
              <b>Caveat from the run:</b> {c}
            </div>
          ))}
        </div>

        {/* Right Side: Code View */}
        <div className="code" style={{ whiteSpace: "pre-wrap" }}>
{`instrument:   ${instStr}
group:        ${groupStr}
capital:      ${capitalStr}
window:       ${windowDetailStr}
cost_model:   ${costStr}
data_source:  ${sourceStr}
code_version: ${versionStr}`}
        </div>
      </div>
    </section>
  );
}
