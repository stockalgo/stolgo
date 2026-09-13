import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { percent } from "../utils/formatters";

export function ComparePage({ onOpenDetail, runs }) {
  const [marketFilter, setMarketFilter] = useState("All");
  const filteredRuns = runs.filter(
    (r) => marketFilter === "All" || r.market.toUpperCase() === marketFilter.toUpperCase()
  );
  const [selectedIds, setSelectedIds] = useState(() =>
    runs.slice(0, 4).map((r) => r.id)
  );

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 4) {
        return [...prev.slice(1), id];
      }
      return [...prev, id];
    });
  };

  const comparedRuns = runs.filter((r) => selectedIds.includes(r.id));

  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="Compare"
        title="Compare strategy candidates without opening every chart"
        description="Normalize performance, risk, and stability across completed NIFTY & SENSEX runs."
      />
      <section className="library-toolbar surface-panel" style={{ marginBottom: "16px" }}>
        <span>Filter index:</span>
        {["All", "NIFTY", "SENSEX"].map((m) => (
          <button
            key={m}
            type="button"
            className={marketFilter === m ? "active" : ""}
            onClick={() => setMarketFilter(m)}
          >
            {m}
          </button>
        ))}
        <span style={{ marginLeft: "auto", color: "var(--muted)", fontSize: "12px" }}>
          Selected ({comparedRuns.length} of 4 max)
        </span>
      </section>

      <section className="surface-panel" style={{ marginBottom: "16px" }}>
        <h3 style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "8px" }}>Select runs to compare:</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {filteredRuns.map((run) => {
            const active = selectedIds.includes(run.id);
            return (
              <button
                key={run.id}
                type="button"
                className={`tf-btn ${active ? "active" : ""}`}
                style={{ padding: "6px 12px", borderRadius: "8px", fontSize: "12px" }}
                onClick={() => toggleSelect(run.id)}
              >
                {active ? "✓ " : "+ "}
                {run.strategy} ({run.market} · {run.timeframe})
              </button>
            );
          })}
        </div>
      </section>

      <section className="compare-board surface-panel">
        {comparedRuns.map((run) => (
          <article className="compare-card" key={run.id}>
            <div>
              <h2>{run.strategy}</h2>
              <span>{run.market} · {run.timeframe}</span>
            </div>
            <dl>
              <div><dt>Net Return</dt><dd className={run.return >= 0 ? "positive" : "negative"}>{percent(run.return)}</dd></div>
              <div><dt>Sharpe Ratio</dt><dd>{Number(run.sharpe).toFixed(2)}</dd></div>
              <div><dt>Max Drawdown</dt><dd className="negative">{percent(run.drawdown)}</dd></div>
              <div><dt>Total Trades</dt><dd>{run.trades.toLocaleString()}</dd></div>
            </dl>
            <button type="button" onClick={() => onOpenDetail(run.id)}>
              Inspect on Chart
            </button>
          </article>
        ))}
        {comparedRuns.length === 0 && (
          <div className="empty-state">No strategies selected. Click any candidate above to compare.</div>
        )}
      </section>
    </div>
  );
}
