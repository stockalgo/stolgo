import React, { useMemo } from "react";
import { inr } from "../../lib/format.js";

export function CostBreakdown({ run, trades = [] }) {
  const { gross, fees, slippage, net, avgStop, avgTarget } = useMemo(() => {
    if (trades && trades.length > 0) {
      const g = trades.reduce((acc, t) => acc + (t.gross_pnl ?? 0), 0);
      const f = trades.reduce((acc, t) => acc + (t.fees ?? 0), 0);
      const hasSlip = trades.some(
        (t) => t.slippage !== null && t.slippage !== undefined
      );
      const s = hasSlip
        ? trades.reduce((acc, t) => acc + (t.slippage ?? 0), 0)
        : null;
      const n = trades.reduce((acc, t) => acc + (t.net_pnl ?? 0), 0);

      const stops = trades.filter((t) => t.exit_reason === "STOP");
      const targets = trades.filter((t) => t.exit_reason === "TARGET");
      const aStop =
        stops.length > 0
          ? stops.reduce((acc, t) => acc + (t.net_pnl ?? 0), 0) / stops.length
          : null;
      const aTarget =
        targets.length > 0
          ? targets.reduce((acc, t) => acc + (t.net_pnl ?? 0), 0) / targets.length
          : null;

      return {
        gross: g,
        fees: f,
        slippage: s,
        net: n,
        avgStop: aStop,
        avgTarget: aTarget,
      };
    }

    const m = run?.metrics || {};
    return {
      gross: m.gross_pnl ?? (m.net_pnl != null && m.fees != null ? m.net_pnl + m.fees : null),
      fees: m.fees ?? 0,
      slippage: m.slippage ?? null,
      net: m.net_pnl ?? 0,
      avgStop: null,
      avgTarget: null,
    };
  }, [trades, run?.metrics]);

  const hasSlippage = slippage !== null && slippage !== undefined;
  const base = Math.max(Math.abs(gross ?? 0), Math.abs(net ?? 0) + Math.abs(fees) + Math.abs(slippage ?? 0)) || 1;

  // Percentage widths and left offsets for the waterfall
  const grossW = 100;
  const feesW = Math.min(100, (fees / base) * 100);
  const feesLeft = Math.max(0, 100 - feesW);

  const netW = Math.max(0, Math.min(100, (net / base) * 100));
  const slipW = hasSlippage ? Math.min(100, (slippage / base) * 100) : 0;
  const slipLeft = netW;

  const costTakePct =
    gross && gross > 0
      ? Math.round(((fees + (slippage || 0)) / gross) * 100)
      : 0;

  const perTradeSlip =
    hasSlippage && trades.length > 0 ? Math.round(slippage / trades.length) : null;

  const hasStopLossBias =
    avgStop != null && avgTarget != null && Math.abs(avgStop) > avgTarget;

  return (
    <section className="panel">
      <div className="panel__head">
        <span className="eyebrow">Where the money went</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
        {/* Row 1: Gross P&L */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "78px minmax(0, 1fr) 86px",
            gap: "10px",
            alignItems: "center",
            height: "30px",
            fontSize: "12px",
          }}
        >
          <span style={{ color: "var(--text-2)" }}>Gross P&amp;L</span>
          <div
            style={{
              position: "relative",
              height: "20px",
              background: "var(--bg-raised)",
              borderRadius: "3px",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: "0%",
                width: `${grossW}%`,
                top: 0,
                bottom: 0,
                borderRadius: "3px",
                background: "#3ddc97",
              }}
            />
          </div>
          <span className="num">{inr(gross, { signed: true })}</span>
        </div>

        {/* Row 2: Fees */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "78px minmax(0, 1fr) 86px",
            gap: "10px",
            alignItems: "center",
            height: "30px",
            fontSize: "12px",
          }}
        >
          <span style={{ color: "var(--text-2)" }}>Fees</span>
          <div
            style={{
              position: "relative",
              height: "20px",
              background: "var(--bg-raised)",
              borderRadius: "3px",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: `${feesLeft.toFixed(1)}%`,
                width: `${feesW.toFixed(1)}%`,
                top: 0,
                bottom: 0,
                borderRadius: "3px",
                background: "#e5484d",
              }}
            />
          </div>
          <span className="num">
            <span className="neg">{fees > 0 ? inr(-fees) : inr(0)}</span>
          </span>
        </div>

        {/* Row 3: Slippage (if recorded) */}
        {hasSlippage && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "78px minmax(0, 1fr) 86px",
              gap: "10px",
              alignItems: "center",
              height: "30px",
              fontSize: "12px",
            }}
          >
            <span style={{ color: "var(--text-2)" }}>Slippage</span>
            <div
              style={{
                position: "relative",
                height: "20px",
                background: "var(--bg-raised)",
                borderRadius: "3px",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: `${slipLeft.toFixed(1)}%`,
                  width: `${slipW.toFixed(1)}%`,
                  top: 0,
                  bottom: 0,
                  borderRadius: "3px",
                  background: "#f5a524",
                }}
              />
            </div>
            <span className="num">
              <span className="accent">
                {slippage > 0 ? inr(-slippage) : inr(0)}
              </span>
            </span>
          </div>
        )}

        {/* Row 4: Net P&L */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "78px minmax(0, 1fr) 86px",
            gap: "10px",
            alignItems: "center",
            height: "30px",
            fontSize: "12px",
          }}
        >
          <span
            style={{
              fontWeight: 600,
              color: "var(--text-1)",
            }}
          >
            Net P&amp;L
          </span>
          <div
            style={{
              position: "relative",
              height: "20px",
              background: "var(--bg-raised)",
              borderRadius: "3px",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: "0%",
                width: `${netW.toFixed(1)}%`,
                top: 0,
                bottom: 0,
                borderRadius: "3px",
                background: "#e6e8ea",
              }}
            />
          </div>
          <span className="num" style={{ fontWeight: 600 }}>
            {inr(net, { signed: true })}
          </span>
        </div>
      </div>

      <div className="panel__foot">
        Costs take {costTakePct}% of gross.{" "}
        {hasSlippage ? (
          <>
            Slippage alone is {inr(slippage)} (₹{perTradeSlip} per trade).
          </>
        ) : (
          <>Slippage not recorded.</>
        )}
        {hasStopLossBias && (
          <>
            {" "}
            STOP exits lose more than TARGET exits earn back per trade. See the Exit
            reasons table.
          </>
        )}
      </div>
    </section>
  );
}
