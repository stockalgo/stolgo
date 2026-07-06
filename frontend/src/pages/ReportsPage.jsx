import { PageHeader } from "../components/PageHeader";

export function ReportsPage({ runs }) {
  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="Reports"
        title="Review completed run artifacts"
        description="Each listed report is backed by a completed stolgo run manifest."
        action={<button className="primary-button" type="button">Export report</button>}
      />
      <div className="reports-grid">
        {runs.map((run, index) => (
          <section className="surface-panel report-tile" key={run.id}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <h2>{run.strategy}</h2>
            <p>{run.market} · {run.timeframe} · {run.created_at ? new Date(run.created_at).toLocaleString() : "-"}</p>
          </section>
        ))}
        {runs.length === 0 && <div className="empty-state surface-panel">No completed runs found.</div>}
      </div>
    </div>
  );
}
