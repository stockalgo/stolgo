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
