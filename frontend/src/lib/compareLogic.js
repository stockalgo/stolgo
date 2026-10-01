import { inr, pct, ratio, prob } from "./format.js";
import { isComparable, isBestComparableValue } from "./verdict.js";

export const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

export function formatMonthYear(dateStr) {
  if (!dateStr) return "";
  const parts = String(dateStr).slice(0, 10).split("-");
  if (parts.length < 2) return dateStr;
  const [year, month] = parts;
  const mIdx = parseInt(month, 10) - 1;
  return `${MONTH_NAMES[mIdx] || month} ${year}`;
}

export function parseRunIds(idsParam) {
  if (!idsParam) return [];
  return idsParam
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 4);
}

export function getMetricValue(run, metricKey) {
  if (!run) return undefined;
  if (metricKey === "p_net_positive") {
    return run.robustness?.p_net_positive ?? run.metrics?.p_net_positive;
  }
  if (metricKey === "net_without_top5") {
    return run.robustness?.net_without_top5 ?? run.metrics?.net_without_top5;
  }
  return run.metrics?.[metricKey];
}

export function isBestValue(run, metricKey, allRuns, direction = "higher") {
  const normalizedRuns = allRuns.map((r) => ({
    ...r,
    metrics: {
      ...r?.metrics,
      [metricKey]: getMetricValue(r, metricKey),
    },
  }));
  const normalizedRun = {
    ...run,
    metrics: {
      ...run?.metrics,
      [metricKey]: getMetricValue(run, metricKey),
    },
  };
  return isBestComparableValue(normalizedRun, metricKey, normalizedRuns, direction);
}

export const COMPARE_METRICS = [
  {
    key: "net_pnl",
    label: "Net P&L",
    format: (val) => inr(val, { signed: true }),
    direction: "higher",
  },
  {
    key: "total_return",
    label: "Total return",
    format: (val) => pct(val),
    direction: "higher",
  },
  {
    key: "cagr",
    label: "CAGR",
    format: (val) => pct(val),
    direction: "higher",
    warnIf: (r) => !isComparable(r) || r.metrics?.annualised_from_short_window,
    warnTitle: "Annualised from short window; not comparable",
  },
  {
    key: "sharpe",
    label: "Sharpe",
    format: (val) => ratio(val),
    direction: "higher",
  },
  {
    key: "sortino",
    label: "Sortino",
    format: (val) => ratio(val),
    direction: "higher",
  },
  {
    key: "max_drawdown",
    label: "Max drawdown",
    format: (val) => pct(val, { signed: true }),
    direction: "higher",
  },
  {
    key: "profit_factor",
    label: "Profit factor",
    format: (val) => ratio(val),
    direction: "higher",
  },
  {
    key: "hit_rate",
    label: "Hit rate",
    format: (val) => pct(val, { signed: false }),
    direction: "higher",
  },
  {
    key: "p_net_positive",
    label: "P(net > 0) · bootstrap",
    format: (val) => prob(val),
    direction: "higher",
  },
  {
    key: "net_without_top5",
    label: "Net without best 5",
    format: (val) => inr(val, { signed: true }),
    direction: "higher",
  },
];
