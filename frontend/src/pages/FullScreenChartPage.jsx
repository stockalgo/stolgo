import { TradingCharts } from "../components/charts/TradingCharts";

export function FullScreenChartPage({
  currency,
  data,
  detail,
  loading,
  onBackToDashboard,
  onToggleCurrency,
  onToggleTheme,
  runs,
  selectedRunId,
  selectedTrade,
  setSelectedRunId,
  setSelectedTrade,
  theme,
  timeZone,
}) {
  const selectedRun = runs.find((run) => run.id === selectedRunId);

  return (
    <div className={`fullscreen-chart-layout ${theme}`}>
      <header className="fullscreen-header">
        <div className="fs-brand-group">
          <button
            type="button"
            className="fs-back-btn"
            onClick={onBackToDashboard}
            title="Back to Backtest Dashboard"
          >
            ← Dashboard
          </button>
          <div className="status-orb" />
          <div className="fs-strategy-select-wrap">
            <select
              className="strategy-select"
              value={selectedRunId ?? ""}
              onChange={(e) => setSelectedRunId(e.target.value)}
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.strategy} ({r.market} · {r.timeframe})
                </option>
              ))}
            </select>
          </div>
          {selectedRun && <span className="version">{selectedRun.id}</span>}
        </div>

        <div className="fs-controls-group">
          {detail?.rawMetrics && (
            <div className="fs-quick-metrics">
              <span>Return: <b>{(detail.rawMetrics.total_return * 100).toFixed(1)}%</b></span>
              <span>Sharpe: <b>{Number(detail.rawMetrics.sharpe || 0).toFixed(2)}</b></span>
              <span>Max DD: <b className="negative">{(detail.rawMetrics.max_drawdown * 100).toFixed(1)}%</b></span>
              <span>Trades: <b>{detail.rawMetrics.num_trades || 0}</b></span>
            </div>
          )}

          <button
            type="button"
            className="nav-btn"
            onClick={onToggleCurrency}
            title="Toggle INR / USD"
          >
            {currency === "INR" ? "₹ INR" : "$ USD"}
          </button>
          <button
            type="button"
            className="nav-btn"
            onClick={onToggleTheme}
            title="Toggle Light / Dark theme"
          >
            {theme === "light" ? "🌙 Dark" : "☀️ Light"}
          </button>
        </div>
      </header>

      <div className="fullscreen-chart-body">
        {loading && <div className="empty-state surface-panel">Loading full chart dataset...</div>}
        <TradingCharts
          data={data}
          isFullscreen
          metrics={detail?.rawMetrics}
          onSelectTrade={setSelectedTrade}
          run={selectedRun}
          selectedTrade={selectedTrade}
          theme={theme}
        />
      </div>
    </div>
  );
}
