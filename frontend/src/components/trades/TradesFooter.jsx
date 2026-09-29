import React from "react";
import { inr } from "../../lib/format.js";

export function TradesFooter({ trades = [], filterDesc = "all" }) {
  const n = trades.length;
  const winCount = trades.filter((t) => (t.net_pnl ?? 0) >= 0).length;
  const lossCount = n - winCount;

  const grossSum = trades.reduce((acc, t) => acc + (t.gross_pnl ?? 0), 0);
  const feesSum = trades.reduce((acc, t) => acc + (t.fees ?? 0), 0);
  const hasAnySlippage = trades.some(
    (t) => t.slippage !== null && t.slippage !== undefined
  );
  const slipSum = trades.reduce((acc, t) => acc + (t.slippage ?? 0), 0);
  const netSum = trades.reduce((acc, t) => acc + (t.net_pnl ?? 0), 0);

  // Mean R computation across trades with non-null r_multiple
  const rTrades = trades.filter(
    (t) => t.r_multiple !== null && t.r_multiple !== undefined
  );
  let meanRStr = "—";
  if (rTrades.length > 0) {
    const meanR =
      rTrades.reduce((acc, t) => acc + Number(t.r_multiple), 0) / rTrades.length;
    meanRStr = meanR >= 0 ? `+${meanR.toFixed(2)}` : meanR.toFixed(2);
  }

  // Reconciliation: |Σgross − Σfees − Σslip − Σnet| ≤ 0.05·n
  const diff = Math.abs(grossSum - feesSum - slipSum - netSum);
  const tolerance = 0.05 * (n || 1);
  const reconciles = diff <= tolerance;

  return (
    <tfoot>
      <tr>
        <td />
        <td colSpan="6">
          {n} trades · {winCount} W / {lossCount} L · filtered: {filterDesc}
        </td>
        <td className={`num ${grossSum >= 0 ? "pos" : "neg"}`}>
          {inr(grossSum, { signed: true })}
        </td>
        <td className="num">
          {feesSum > 0 ? inr(-feesSum) : inr(0)}
        </td>
        <td className="num faint">
          {hasAnySlippage ? (slipSum > 0 ? inr(-slipSum) : inr(0)) : "—"}
        </td>
        <td className={`num ${netSum >= 0 ? "pos" : "neg"}`}>
          {inr(netSum, { signed: true })}
        </td>
        <td className="num">{meanRStr}</td>
        <td
          colSpan="2"
          className={reconciles ? "muted" : "warn"}
          style={{
            fontFamily: "var(--font-sans)",
            color: reconciles ? "var(--text-3)" : "var(--warn)",
          }}
        >
          {reconciles
            ? "Gross − fees − slippage = net ✓"
            : `⚠ does not reconcile by ₹${Math.round(diff).toLocaleString()}`}
        </td>
      </tr>
    </tfoot>
  );
}
