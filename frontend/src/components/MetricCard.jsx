import { metricTone, metricValue } from "../utils/formatters";

export function MetricCard({ metric }) {
  const tone = metricTone(metric.value, metric.fmt);

  return (
    <div className="metric-card">
      <div className="metric-label">{metric.label}</div>
      <div className={`metric-value ${tone}`}>{metricValue(metric.value, metric.fmt)}</div>
    </div>
  );
}
