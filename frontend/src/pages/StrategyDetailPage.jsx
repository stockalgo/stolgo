import { useState } from "react";
import { TradingCharts } from "../components/charts/TradingCharts";
import { RunAnalysisRail } from "../components/detail/RunAnalysisRail";
import { TradeTable } from "../components/detail/TradeTable";
import { MetricCard } from "../components/MetricCard";

export function StrategyDetailPage({
  data,
  detail,
  loading,
  runs,
  selectedRunId,
  selectedTrade,
  setSelectedRunId,
  setSelectedTrade,
  theme,
}) {
  const [tradeFilter, setTradeFilter] = useState("All");
  const selectedRun = runs.find((run) => run.id === selectedRunId);

  const visibleTrades = data.trades.filter((trade) => {
    if (tradeFilter === "All") return true;
    if (tradeFilter === "Winners") return trade.pnl > 0;
    if (tradeFilter === "Losers") return trade.pnl < 0;
    return trade.side === tradeFilter;
  });

  return (
    <>
      <header className="topbar">
        <section className="strategy-identity">
          <div className="status-orb" />
          <div className="strategy-selector-block">
            <div className="strategy-line">
              <label className="strategy-select-label" htmlFor="strategy-switcher">Strategy</label>
              <select
                id="strategy-switcher"
                className="strategy-select"
                value={selectedRunId ?? ""}
                onChange={(event) => setSelectedRunId(event.target.value)}
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>{run.strategy}</option>
                ))}
              </select>
              {selectedRun && <span className="version">{selectedRun.id}</span>}
            </div>
            <p>{selectedRun ? `${selectedRun.market} · ${selectedRun.timeframe}` : "Select a completed run"}</p>
          </div>
        </section>
      </header>

      <section className="metrics-strip" aria-label="Performance summary">
        {detail?.metrics.map((metric) => (
          <MetricCard metric={metric} key={metric.key} />
        ))}
      </section>

      {loading && <div className="empty-state surface-panel">Loading run artifacts...</div>}
      <div className="workspace-grid">
        <div className="primary-column">
          <TradingCharts
            data={data}
            metrics={detail?.rawMetrics}
            onSelectTrade={setSelectedTrade}
            run={selectedRun}
            selectedTrade={selectedTrade}
            theme={theme}
          />
          <section className="trade-analysis">
            <div className="section-heading">
              <div>
                <span>Executed trades</span>
                <h2>Trade analysis</h2>
              </div>
              <div className="filters" aria-label="Trade filters">
                {["All", "Long", "Short", "Winners", "Losers"].map((filter) => (
                  <button
                    className={tradeFilter === filter ? "active" : ""}
                    key={filter}
                    type="button"
                    onClick={() => setTradeFilter(filter)}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>
            <TradeTable visibleTrades={visibleTrades} selectedTrade={selectedTrade} setSelectedTrade={setSelectedTrade} />
          </section>
        </div>
        <RunAnalysisRail
          data={data}
          detail={detail}
          onSelectTrade={setSelectedTrade}
          run={selectedRun}
        />
      </div>
    </>
  );
}
