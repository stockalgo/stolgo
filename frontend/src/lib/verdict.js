/**
 * Domain rules and verdicts (UI plan §7).
 */

export const MIN_TRADES = 100;
export const MIN_SESSIONS = 252;

export const isComparable = (r) =>
  Boolean(
    r &&
      r.metrics &&
      (r.metrics.num_trades ?? 0) >= MIN_TRADES &&
      r.window &&
      (r.window.sessions ?? 0) >= MIN_SESSIONS &&
      !["empty", "superseded"].includes(r.status)
  );

export function getVerdict(r) {
  if (!r || !r.metrics) {
    return { label: "NO TRADES", style: "muted", text: "Nothing to evaluate" };
  }
  const n = r.metrics.num_trades ?? 0;
  const netPnl = r.metrics.net_pnl ?? 0;
  const pNetPos = r.robustness ? r.robustness.p_net_positive : null;
  const netNoTop5 = r.robustness ? r.robustness.net_without_top5 : null;
  const status = r.status || "ok";
  const sessions = r.window?.sessions ?? 0;

  // 1. num_trades === 0
  if (n === 0) {
    return { label: "NO TRADES", style: "muted", text: "Nothing to evaluate" };
  }
  // 2. num_trades < 30
  if (n < 30) {
    return { label: "EDGE · UNPROVEN", style: "amber", text: "Fewer than 30 trades" };
  }
  // 3. net_pnl <= 0 or p_net_positive < 0.80
  if (netPnl <= 0) {
    return { label: "NO EDGE", style: "red", text: "Net P&L is not positive" };
  }
  if (pNetPos !== null && pNetPos < 0.8) {
    return { label: "NO EDGE", style: "red", text: "P(net > 0) below 80%" };
  }
  // 4. net_without_top5 <= 0
  if (netNoTop5 !== null && netNoTop5 <= 0) {
    return {
      label: "EDGE · FRAGILE",
      style: "amber",
      text: "Profitable, but the best 5 trades carry it",
    };
  }
  // 5. p_net_positive < 0.95 or status in {low_sample, short_window, data_issues}
  const isFragileStatus = ["low_sample", "short_window", "data_issues"].includes(status);
  const isLowPNet = pNetPos !== null && pNetPos < 0.95;
  if (isLowPNet || isFragileStatus) {
    let reasonText = "";
    if (status === "data_issues") {
      const dq = r.data_quality || r.diagnostics?.data_quality;
      const x = dq?.trades_with_missing_data ?? 0;
      const pctVal = n > 0 ? Math.round((x / n) * 100) : 0;
      reasonText = `${pctVal}% forced data exits`;
    } else if (status === "low_sample") {
      reasonText = `Only ${n} trades`;
    } else if (status === "short_window") {
      reasonText = `Only ${sessions} sessions`;
    } else if (pNetPos !== null) {
      reasonText = `P(net > 0) is ${Math.round(pNetPos * 100)}%`;
    }
    return { label: "EDGE · FRAGILE", style: "amber", text: reasonText };
  }
  // 6. otherwise
  return { label: "EDGE · ROBUST", style: "green", text: "Survives bootstrap and top-5 removal" };
}

export function getStatusBadge(status) {
  switch (status) {
    case "ok":
      return { label: "OK", className: "badge--ok" };
    case "low_sample":
      return { label: "Low sample", className: "badge--low" };
    case "short_window":
      return { label: "Short window", className: "badge--low" };
    case "data_issues":
      return { label: "Data issues", className: "badge--warn" };
    case "superseded":
      return { label: "Superseded", className: "badge--muted" };
    case "empty":
      return { label: "Empty", className: "badge--muted" };
    default:
      return { label: status || "—", className: "badge--muted" };
  }
}

export function getAutoInsight(runDetail) {
  if (!runDetail) return null;
  const m = runDetail.metrics || {};
  const hitRate = m.hit_rate;
  const payoff = m.payoff;
  const numTrades = m.num_trades || 0;
  const worstDay = m.worst_day;
  const fees = m.fees || 0;
  const grossPnl = m.gross_pnl || 0;

  // Rule 1: hit_rate < 0.45 && payoff >= 1.5
  if (hitRate !== null && hitRate < 0.45 && payoff !== null && payoff >= 1.5) {
    const hitPct = Math.round(hitRate * 100);
    const added = Math.round(50 * numTrades);
    return `Right-tail strategy: ${hitPct}% hit rate, payoff ${payoff.toFixed(2)}×. Cutting costs by ₹50 per trade adds ₹${added.toLocaleString("en-IN")}.`;
  }
  // Rule 2: hit_rate >= 0.6 && payoff < 1
  if (hitRate !== null && hitRate >= 0.6 && payoff !== null && payoff > 0 && payoff < 1) {
    const hitPct = Math.round(hitRate * 100);
    const lossMultiple = (1 / payoff).toFixed(1);
    const worstStr =
      worstDay !== null && worstDay !== undefined
        ? `₹${Math.round(Math.abs(worstDay)).toLocaleString("en-IN")}`
        : "—";
    return `Left-tail strategy: wins ${hitPct}% of trades but a loss costs ${lossMultiple}× a win. Watch the worst day (${worstStr}).`;
  }
  // Rule 3: fees / gross_pnl > 0.4
  if (grossPnl > 0 && fees / grossPnl > 0.4) {
    const feePct = Math.round((fees / grossPnl) * 100);
    return `Costs take ${feePct}% of gross profit.`;
  }
  // Rule 4: otherwise no callout
  return null;
}

export function isBestComparableValue(run, metricKey, allRuns, better = "higher") {
  if (!isComparable(run)) return false;
  const comparableRuns = (allRuns || []).filter(isComparable);
  if (comparableRuns.length === 0) return false;
  const val = run.metrics ? run.metrics[metricKey] : null;
  if (val === null || val === undefined || Number.isNaN(val)) return false;

  const validValues = comparableRuns
    .map((r) => r.metrics?.[metricKey])
    .filter((v) => v !== null && v !== undefined && !Number.isNaN(v));

  if (validValues.length === 0) return false;

  if (better === "lower") {
    const minVal = Math.min(...validValues);
    return Math.abs(val - minVal) < 1e-9;
  }
  const maxVal = Math.max(...validValues);
  return Math.abs(val - maxVal) < 1e-9;
}
