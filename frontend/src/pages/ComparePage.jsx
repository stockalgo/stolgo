import { PageHeader } from "../components/PageHeader";
import { percent } from "../utils/formatters";

export function ComparePage({ onOpenDetail, runs }) {
  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="Compare"
        title="Compare strategy candidates without opening every chart"
        description="Normalize performance, risk, and stability across completed runs."
      />
      <section className="compare-board surface-panel">
        {runs.slice(0, 4).map((run) => (
          <article className="compare-card" key={run.id}>
            <div><h2>{run.strategy}</h2><span>{run.market} · {run.timeframe}</span></div>
            <dl>
              <div><dt>Return</dt><dd className={run.return >= 0 ? "positive" : "negative"}>{percent(run.return)}</dd></div>
              <div><dt>Sharpe</dt><dd>{Number(run.sharpe).toFixed(2)}</dd></div>
              <div><dt>Max DD</dt><dd className="negative">{percent(run.drawdown)}</dd></div>
              <div><dt>Trades</dt><dd>{run.trades.toLocaleString()}</dd></div>
            </dl>
            <button type="button" onClick={() => onOpenDetail(run.id)}>Open</button>
          </article>
        ))}
        {runs.length === 0 && <div className="empty-state">No completed runs to compare.</div>}
      </section>
    </div>
  );
}
