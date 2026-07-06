import { useEffect, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { getSweep } from "../data/client";

export function OptimizationPage({ sweeps }) {
  const [selectedSweepId, setSelectedSweepId] = useState("");
  const [sweep, setSweep] = useState(null);

  useEffect(() => {
    setSelectedSweepId((current) => current || sweeps[0]?.id || "");
  }, [sweeps]);

  useEffect(() => {
    if (!selectedSweepId) return undefined;
    let alive = true;
    getSweep(selectedSweepId)
      .then((payload) => {
        if (alive) setSweep(payload);
      })
      .catch(() => {
        if (alive) setSweep(null);
      });
    return () => {
      alive = false;
    };
  }, [selectedSweepId]);

  const columns = sweep?.rows?.[0] ? Object.keys(sweep.rows[0]) : [];

  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="Optimization"
        title="Inspect parameter sweeps without curve fitting blindly"
        description="Sort the real persisted sweep rows and look for stable parameter regions."
        action={<button className="primary-button" type="button">Queue sweep</button>}
      />
      <div className="optimization-grid single">
        <section className="surface-panel candidate-panel">
          <div className="section-heading">
            <div>
              <span>Sweep results</span>
              <h2>{sweep?.strategy ?? "No sweep selected"}</h2>
            </div>
            <select value={selectedSweepId} onChange={(event) => setSelectedSweepId(event.target.value)}>
              {sweeps.map((row) => (
                <option key={row.id} value={row.id}>{row.strategy} · {row.id}</option>
              ))}
            </select>
          </div>
          {!sweep && <div className="empty-state">No completed sweeps found.</div>}
          {sweep && (
            <div className="trade-table-wrap">
              <table className="trade-table">
                <thead>
                  <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
                </thead>
                <tbody>
                  {sweep.rows.map((row, index) => (
                    <tr key={index}>
                      {columns.map((column) => <td key={column}>{String(row[column])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
