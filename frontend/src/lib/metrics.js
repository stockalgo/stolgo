import { formatMetric } from "./format.js";

export function getMetricDef(key, defs = []) {
  if (!Array.isArray(defs)) return null;
  return defs.find((d) => d.key === key) || null;
}

export { formatMetric };
