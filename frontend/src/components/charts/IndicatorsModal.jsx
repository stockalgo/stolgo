import { useState } from "react";

export const AVAILABLE_INDICATORS = [
  { id: "ema20", name: "EMA 20", category: "Moving Averages", color: "#2962ff", desc: "Short-term exponential moving average" },
  { id: "ema50", name: "EMA 50", category: "Moving Averages", color: "#ff6d00", desc: "Medium-term exponential moving average" },
  { id: "ema200", name: "EMA 200", category: "Moving Averages", color: "#9c27b0", desc: "Long-term institutional moving average" },
  { id: "sma20", name: "SMA 20", category: "Moving Averages", color: "#26a69a", desc: "Simple 20-period moving average" },
  { id: "sma50", name: "SMA 50", category: "Moving Averages", color: "#e91e63", desc: "Simple 50-period moving average" },
  { id: "volume", name: "Volume (Traded)", category: "Volume & Flow", color: "#26a69a", desc: "Bar traded volume histogram with green/red bars" },
  { id: "volumeMa", name: "Volume MA (20)", category: "Volume & Flow", color: "#29b6f6", desc: "20-period average volume overlay" },
  { id: "vwap", name: "VWAP", category: "Volume & Flow", color: "#ffd600", desc: "Intraday session volume weighted average price" },
  { id: "bollinger", name: "Bollinger Bands (20, 2)", category: "Volatility", color: "#00bcd4", desc: "20-period volatility envelope (2 std dev)" },
  { id: "rsi", name: "RSI (14)", category: "Oscillators", color: "#ab47bc", desc: "Relative Strength Index momentum oscillator" },
];

export function IndicatorsModal({ activeIndicators, onClose, onToggleIndicator }) {
  const [search, setSearch] = useState("");

  const filtered = AVAILABLE_INDICATORS.filter((ind) =>
    ind.name.toLowerCase().includes(search.toLowerCase()) ||
    ind.category.toLowerCase().includes(search.toLowerCase()) ||
    ind.desc.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="tv-modal-overlay" onClick={onClose}>
      <div className="tv-modal-card indicators-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="tv-modal-header">
          <div className="modal-title-wrap">
            <span className="fx-badge">fx</span>
            <h3>Indicators & Strategies</h3>
          </div>
          <button type="button" className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="tv-search-wrap">
          <input
            autoFocus
            type="text"
            placeholder="Search indicators (e.g. EMA, VWAP, RSI, Bollinger)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="indicators-list">
          {filtered.map((ind) => {
            const isActive = !!activeIndicators[ind.id];
            return (
              <div
                key={ind.id}
                className={`indicator-row ${isActive ? "active" : ""}`}
                onClick={() => onToggleIndicator(ind.id)}
              >
                <div className="ind-info">
                  <div className="ind-name-line">
                    <span className="ind-color-dot" style={{ background: ind.color }} />
                    <b>{ind.name}</b>
                    <span className="ind-cat">{ind.category}</span>
                  </div>
                  <small>{ind.desc}</small>
                </div>
                <button
                  type="button"
                  className={`ind-toggle-btn ${isActive ? "active" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleIndicator(ind.id);
                  }}
                >
                  {isActive ? "Added ✓" : "+ Add"}
                </button>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="empty-state" style={{ padding: "24px 0" }}>
              No matching indicators found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
