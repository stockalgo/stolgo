import { useState } from "react";
import { PageHeader } from "../components/PageHeader";

const setupFields = [
  { label: "Strategy Structure", default: "Short Strangle", options: ["Short Strangle", "Short Straddle", "Iron Condor", "EMA Trend Breakout"] },
  { label: "Underlying Index", default: "NIFTY", options: ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"] },
  { label: "DTE (Days to Expiry)", default: "0-DTE (Expiry Day)", options: ["0-DTE (Expiry Day)", "1-DTE", "Positional (7-DTE)"] },
  { label: "Base Timeframe", default: "15m", options: ["1m", "5m", "15m", "1h", "1D"] },
  { label: "Trading Session / Hours", default: "09:20 - 14:30 IST", options: ["09:20 - 14:30 IST", "09:15 - 15:15 IST", "Full Session"] },
  { label: "Initial Capital", default: "₹1,80,000", options: ["₹1,80,000", "₹80,000", "₹5,00,000", "₹10,00,000"] },
  { label: "Leg Stop Loss", default: "25% of leg premium", options: ["25% of leg premium", "50% of leg premium", "100% of leg premium", "None"] },
  { label: "Statutory Fees & Slippage", default: "Indian F&O (STT + GST + SEBI + 0.5% slip)", options: ["Indian F&O (STT + GST + SEBI + 0.5% slip)", "Zero commission (Gross)", "Standard Brokerage ₹20/order"] },
];

export function NewBacktestPage() {
  const [formData, setFormData] = useState(
    setupFields.reduce((acc, field) => ({ ...acc, [field.label]: field.default }), {})
  );
  const [submitted, setSubmitted] = useState(false);

  const handleStart = () => {
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 4000);
  };

  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="New backtest"
        title="Define the run before seeing results"
        description="Focused setup for market indices, option structures, DTE, session hours, risk parameters, and statutory taxes."
        action={
          <button className="primary-button" type="button" onClick={handleStart}>
            {submitted ? "Run Queued..." : "Start run"}
          </button>
        }
      />
      {submitted && (
        <div className="surface-panel" style={{ borderLeft: "4px solid var(--green)", padding: "12px 18px", marginBottom: "16px" }}>
          <b>Backtest run queued:</b> Running <code>{formData["Strategy Structure"]}</code> on <code>{formData["Underlying Index"]} ({formData["DTE (Days to Expiry)"]})</code>. Artifacts will be exported to <code>runs/</code> upon completion.
        </div>
      )}
      <div className="setup-grid">
        <section className="surface-panel setup-main">
          <h2>Run setup</h2>
          <div className="form-grid">
            {setupFields.map((field) => (
              <label key={field.label}>
                <span>{field.label}</span>
                <select
                  value={formData[field.label]}
                  onChange={(e) => setFormData({ ...formData, [field.label]: e.target.value })}
                >
                  {field.options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        </section>
        <aside className="surface-panel setup-side">
          <h2>Pre-run checks</h2>
          {[
            "Options strike lock-in verified",
            "Indian statutory taxes (STT/GST) configured",
            "No lookahead bias on signal bars",
            "Exchange holiday calendars aligned (NSE/BSE)",
          ].map((item) => (
            <div className="check-row" key={item}><span />{item}</div>
          ))}
          <div className="run-estimate"><b>Estimated runtime</b><strong>18s</strong></div>
        </aside>
      </div>
    </div>
  );
}
