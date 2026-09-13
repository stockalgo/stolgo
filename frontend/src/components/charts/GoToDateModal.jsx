import { useState } from "react";
import { dateLabel, money } from "../../utils/formatters";

export function GoToDateModal({ candles, onClose, onGoToDate, onSelectTrade, selectedTrade, trades = [] }) {
  const firstCandle = candles[0];
  const lastCandle = candles.at(-1);

  const minDateStr = firstCandle
    ? new Date(firstCandle.time * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" })
    : "2024-01-01";
  const maxDateStr = lastCandle
    ? new Date(lastCandle.time * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" })
    : "2026-12-31";

  const [dateInput, setDateInput] = useState(maxDateStr);

  const handleGo = () => {
    if (!dateInput) return;
    onGoToDate(dateInput);
    onClose();
  };

  const handleSelectTradeJump = (tradeId) => {
    const tr = trades.find((t) => String(t.id) === String(tradeId));
    if (tr) {
      onSelectTrade(tr);
      const dateStr = new Date(tr.entryTime * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
      onGoToDate(dateStr, tr.entryTime);
      onClose();
    }
  };

  return (
    <div className="tv-modal-overlay" onClick={onClose}>
      <div className="tv-modal-card goto-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="tv-modal-header">
          <div className="modal-title-wrap">
            <span className="cal-icon">📅</span>
            <h3>Go to Date / Trade</h3>
          </div>
          <button type="button" className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="goto-body">
          <div className="goto-section">
            <label className="field-label">Select calendar date (IST)</label>
            <div className="goto-input-row">
              <input
                type="date"
                min={minDateStr}
                max={maxDateStr}
                value={dateInput}
                onChange={(e) => setDateInput(e.target.value)}
              />
              <button type="button" className="primary-button" onClick={handleGo}>
                Go to Date →
              </button>
            </div>
            <small className="field-hint">Available data: {minDateStr} to {maxDateStr}</small>
          </div>

          {trades.length > 0 && (
            <div className="goto-section">
              <label className="field-label">Or jump directly to executed trade</label>
              <select
                value={selectedTrade?.id ?? ""}
                onChange={(e) => handleSelectTradeJump(e.target.value)}
              >
                <option value="">-- Choose from {trades.length} strategy trades --</option>
                {trades.map((tr) => (
                  <option key={tr.id} value={tr.id}>
                    Trade #{tr.id} · {dateLabel(tr.entryTime)} ({tr.side}) · PnL: {money(tr.pnl)}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="goto-quick-actions">
            <button
              type="button"
              className="tf-btn"
              onClick={() => {
                onGoToDate(minDateStr);
                onClose();
              }}
            >
              ⏮ First Bar ({minDateStr})
            </button>
            <button
              type="button"
              className="tf-btn"
              onClick={() => {
                onGoToDate(maxDateStr);
                onClose();
              }}
            >
              Latest Bar ({maxDateStr}) ⏭
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
