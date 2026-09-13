export const RANGE_PRESETS = [
  { id: "1D", label: "1D", days: 1 },
  { id: "5D", label: "5D", days: 5 },
  { id: "1M", label: "1M", days: 30 },
  { id: "3M", label: "3M", days: 90 },
  { id: "6M", label: "6M", days: 180 },
  { id: "1Y", label: "1Y", days: 365 },
  { id: "ALL", label: "ALL", days: null },
];

export function RangeBar({
  activeRange,
  onFitContent,
  onOpenGoToDate,
  onSelectRange,
  onToggleSubchart,
  subcharts,
  timeZoneLabel = "Asia/Kolkata (IST)",
}) {
  return (
    <div className="tv-bottom-range-bar" aria-label="Time range selector">
      <div className="range-presets-group">
        {RANGE_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            className={`range-btn ${activeRange === preset.id ? "active" : ""}`}
            onClick={() => onSelectRange(preset.id)}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {subcharts && onToggleSubchart && (
        <div className="range-subchart-group" role="group" aria-label="Subchart visibility toggles">
          <span className="subchart-toggle-label">Subcharts:</span>
          <button
            type="button"
            className={`range-subchart-btn ${subcharts.equity ? "active" : ""}`}
            onClick={() => onToggleSubchart("equity")}
            title={subcharts.equity ? "Hide Equity Curve" : "Show Equity Curve"}
          >
            {subcharts.equity ? "✓ Equity" : "+ Equity"}
          </button>
          <button
            type="button"
            className={`range-subchart-btn ${subcharts.drawdown ? "active" : ""}`}
            onClick={() => onToggleSubchart("drawdown")}
            title={subcharts.drawdown ? "Hide Drawdown Curve" : "Show Drawdown Curve"}
          >
            {subcharts.drawdown ? "✓ Drawdown" : "+ Drawdown"}
          </button>
        </div>
      )}

      <div className="range-meta-group">
        <button
          type="button"
          className="range-action-btn"
          title="Jump to date or trade"
          onClick={onOpenGoToDate}
        >
          <span>📅 Go to date...</span>
        </button>
        <button
          type="button"
          className="range-action-btn"
          title="Reset zoom and fit all data"
          onClick={onFitContent}
        >
          <span>⤢ Fit</span>
        </button>
        <span className="tz-label">{timeZoneLabel}</span>
      </div>
    </div>
  );
}
