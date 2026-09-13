import { AVAILABLE_INDICATORS } from "./IndicatorsModal";
import { percent, price } from "../../utils/formatters";

export function ChartLegend({
  activeIndicators,
  hoverCandle,
  hoverVol,
  indicatorValues = {},
  lastCandle,
  onRemoveIndicator,
  onToggleIndicatorVisibility,
  priorCandle,
  run,
  timeframe,
}) {
  const displayCandle = hoverCandle || lastCandle;
  const change = displayCandle && priorCandle ? displayCandle.close - priorCandle.close : 0;
  const changePct = priorCandle ? change / priorCandle.close : 0;

  const activeList = AVAILABLE_INDICATORS.filter((ind) => !!activeIndicators[ind.id]);

  return (
    <div className="tv-chart-legend" aria-label="Chart status legend">
      <div className="legend-symbol-row">
        <span className="legend-symbol">{run?.market ?? "-"}</span>
        <span className="legend-tf">{timeframe}</span>
        <span className="legend-platform">Stolgo TV</span>
        {displayCandle && (
          <div className="legend-ohlc">
            <span>O<b>{price(displayCandle.open)}</b></span>
            <span>H<b>{price(displayCandle.high)}</b></span>
            <span>L<b>{price(displayCandle.low)}</b></span>
            <span>C<b>{price(displayCandle.close)}</b></span>
            {hoverVol != null && <span>Vol<b>{Number(hoverVol).toLocaleString()}</b></span>}
            <span className={change >= 0 ? "positive" : "negative"}>
              {price(change)} ({percent(changePct)})
            </span>
          </div>
        )}
      </div>

      {activeList.length > 0 && (
        <div className="legend-indicators-row">
          {activeList.map((ind) => {
            const val = indicatorValues[ind.id];
            const isHidden = activeIndicators[ind.id]?.hidden;
            return (
              <div className={`legend-ind-tag ${isHidden ? "muted" : ""}`} key={ind.id}>
                <span className="ind-dot" style={{ background: ind.color }} />
                <span className="ind-name">{ind.name}:</span>
                <b className="ind-val">{val !== undefined ? price(val) : "-"}</b>
                <button
                  type="button"
                  className="ind-action-btn"
                  title={isHidden ? "Show indicator" : "Hide indicator"}
                  onClick={() => onToggleIndicatorVisibility(ind.id)}
                >
                  {isHidden ? "👁‍🗨" : "👁"}
                </button>
                <button
                  type="button"
                  className="ind-action-btn delete"
                  title="Remove indicator"
                  onClick={() => onRemoveIndicator(ind.id)}
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
