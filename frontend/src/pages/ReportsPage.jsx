import { PageHeader } from "../components/PageHeader";
import { percent } from "../utils/formatters";

export function ReportsPage({ onOpenDetail, runs }) {
  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="Reports"
        title="Review completed run artifacts"
        description="Browse and inspect individual reports backed by completed stolgo run manifests."
      />
      <div className="reports-grid">
        {runs.map((run, index) => (
          <section
            className="surface-panel report-tile"
            key={run.id}
            style={{ cursor: "pointer" }}
            onClick={() => onOpenDetail && onOpenDetail(run.id)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <span className={`side-badge ${run.return >= 0 ? "positive" : "negative"}`}>
                {percent(run.return)}
              </span>
            </div>
            <h2>{run.strategy}</h2>
            <p>{run.market} · {run.timeframe} · {run.created_at ? new Date(run.created_at).toLocaleString() : "-"}</p>
            <div style={{ marginTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <small style={{ color: "var(--muted)" }}>Sharpe: {Number(run.sharpe).toFixed(2)} · Trades: {run.trades}</small>
              <button
                type="button"
                className="tf-btn active"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenDetail && onOpenDetail(run.id);
                }}
              >
                Inspect run →
              </button>
            </div>
          </section>
        ))}
        {runs.length === 0 && <div className="empty-state surface-panel">No completed runs found.</div>}
      </div>
    </div>
  );
}
