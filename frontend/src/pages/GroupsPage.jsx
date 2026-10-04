import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { listGroups } from "../api/endpoints.js";
import { Chip } from "../components/ui/Chip.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";

export function GroupsPage() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [legacySweeps, setLegacySweeps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    document.title = "Groups · Stolgo";
    let cancelled = false;
    setLoading(true);
    setError(null);

    listGroups()
      .then((data) => {
        if (!cancelled) {
          const items = data?.items || [];
          const modern = items.filter((x) => x.kind !== "sweep");
          const legacy = items.filter((x) => x.kind === "sweep");
          setGroups(modern);
          setLegacySweeps(legacy);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load groups");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <div className="muted">Loading groups…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <EmptyState
          title="Could not load groups"
          description={error}
        />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <section>
        <div className="eyebrow">GROUPS</div>
        <h1 style={{ margin: "4px 0 0", fontSize: 28, fontWeight: 600 }}>
          {groups.length} groups
        </h1>
        <div className="muted">
          Aggregated parameter sweeps, timing families, and multi-run experiments
        </div>
      </section>

      {/* Main Groups Table */}
      <section className="panel panel--flush">
        <table className="table">
          <thead>
            <tr>
              <th>Group</th>
              <th className="num">Runs</th>
              <th>Axes</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {groups.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", color: "var(--text-3)", padding: 24 }}>
                  No groups found
                </td>
              </tr>
            ) : (
              groups.map((grp) => {
                const axesKeys = Object.keys(grp.axes || {});
                return (
                  <tr
                    key={grp.id}
                    onClick={() => navigate(`/groups/${grp.id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <div style={{ fontWeight: 600 }}>{grp.label}</div>
                      <div className="mono muted" style={{ fontSize: 11 }}>
                        {grp.id}
                      </div>
                    </td>
                    <td className="num">{grp.runs}</td>
                    <td>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {axesKeys.map((ax) => (
                          <Chip key={ax}>{ax}</Chip>
                        ))}
                      </div>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Link
                        to={`/groups/${grp.id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        Open →
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>

      {/* Legacy sweeps table if any */}
      {legacySweeps.length > 0 && (
        <section className="panel panel--flush">
          <div style={{ padding: "12px 16px" }} className="panel__head">
            <span className="eyebrow">Parameter sweeps (results.parquet)</span>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Sweep</th>
                <th className="num">Runs</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {legacySweeps.map((swp) => (
                <tr key={swp.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{swp.label || swp.id}</div>
                    <div className="mono muted" style={{ fontSize: 11 }}>
                      {swp.id}
                    </div>
                  </td>
                  <td className="num">{swp.runs || "—"}</td>
                  <td className="muted">{JSON.stringify(swp.axes || {})}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
