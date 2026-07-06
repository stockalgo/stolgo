import { PageHeader } from "../components/PageHeader";

const setupFields = ["Strategy", "Instrument", "Timeframe", "Date range", "Initial capital", "Commission", "Slippage", "Position sizing"];
const setupValues = ["EMA Trend Breakout", "ES", "5m", "2022-01-01 to 2024-12-31", "$100,000", "$2.10 / side", "1 tick", "Fixed risk 0.5%"];

export function NewBacktestPage() {
  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="New backtest"
        title="Define the run before seeing results"
        description="A focused setup flow for market, data range, strategy parameters, fees, slippage, and risk assumptions."
        action={<button className="primary-button" type="button">Start run</button>}
      />
      <div className="setup-grid">
        <section className="surface-panel setup-main">
          <h2>Run setup</h2>
          <div className="form-grid">
            {setupFields.map((label, index) => (
              <label key={label}>
                <span>{label}</span>
                <input defaultValue={setupValues[index]} />
              </label>
            ))}
          </div>
        </section>
        <aside className="surface-panel setup-side">
          <h2>Pre-run checks</h2>
          {["Data has no gaps", "Fees included", "No lookahead fields", "Minimum trades target set"].map((item) => (
            <div className="check-row" key={item}><span />{item}</div>
          ))}
          <div className="run-estimate"><b>Estimated runtime</b><strong>42s</strong></div>
        </aside>
      </div>
    </div>
  );
}
