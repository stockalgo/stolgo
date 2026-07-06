import { PageHeader } from "../components/PageHeader";
import { percent } from "../utils/formatters";

export function StrategyLibraryPage({ loading, onOpenDetail, runs }) {
  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="Strategy library"
        title="Find the strategies worth inspecting"
        description="Sort by robustness first, then open the few runs that deserve deeper chart review."
        action={<button className="primary-button" type="button">Run backtest</button>}
      />
      <section className="library-toolbar surface-panel">
        <input aria-label="Search strategies" placeholder="Search strategy, instrument, tag..." />
        <button type="button">Instrument</button>
        <button type="button">Timeframe</button>
        <button type="button">Risk</button>
        <button type="button">Recently tested</button>
      </section>
      <section className="strategy-table surface-panel">
        <div className="library-row library-head">
          <span>Strategy</span><span>Market</span><span>Return</span><span>Sharpe</span><span>Drawdown</span><span>Trades</span>
        </div>
        {loading && <div className="empty-state">Loading runs...</div>}
        {!loading && runs.length === 0 && <div className="empty-state">No completed runs found.</div>}
        {runs.map((run) => (
          <button className="library-row" key={run.id} type="button" onClick={() => onOpenDetail(run.id)}>
            <span><b>{run.strategy}</b><em>Last run {run.created_at ? new Date(run.created_at).toLocaleString() : "-"}</em></span>
            <span>{run.market} · {run.timeframe}</span>
            <span className={run.return >= 0 ? "positive" : "negative"}>{percent(run.return)}</span>
            <span>{Number(run.sharpe).toFixed(2)}</span>
            <span className="negative">{percent(run.drawdown)}</span>
            <span>{run.trades.toLocaleString()}</span>
          </button>
        ))}
      </section>
    </div>
  );
}
