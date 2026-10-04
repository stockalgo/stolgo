import React, { useState, useEffect, useMemo } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { listRuns } from "../api/endpoints.js";
import { LibraryFilters } from "../components/library/LibraryFilters.jsx";
import { LibraryScatter } from "../components/library/LibraryScatter.jsx";
import { Leaders } from "../components/library/Leaders.jsx";
import { RunsTable } from "../components/library/RunsTable.jsx";
import { Button } from "../components/ui/Button.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { Skeleton } from "../components/ui/Skeleton.jsx";
import { Banner } from "../components/ui/Banner.jsx";
import { dateIST } from "../lib/format.js";

export function LibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const { data, loading, error, reload } = useApi("runs:list", listRuns);

  // Toast state
  const [toast, setToast] = useState(null);
  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };

  // Migration report check
  const [hasMigrationReport, setHasMigrationReport] = useState(true);
  useEffect(() => {
    document.title = "Library · Stolgo";
    reload();
    fetch("/api/migration-report", { method: "HEAD" })
      .then((res) => {
        if (!res.ok) setHasMigrationReport(false);
      })
      .catch(() => setHasMigrationReport(false));
  }, [reload]);

  // Compare selection state (persisted in sessionStorage)
  const [selectedIds, setSelectedIds] = useState(() => {
    try {
      const stored = sessionStorage.getItem("stolgo.compare");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const handleToggleSelect = (runId) => {
    setSelectedIds((prev) => {
      let next;
      if (prev.includes(runId)) {
        next = prev.filter((id) => id !== runId);
      } else {
        if (prev.length >= 4) {
          showToast("Compare holds 4 runs");
          return prev;
        }
        next = [...prev, runId];
      }
      try {
        sessionStorage.setItem("stolgo.compare", JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  // Filter params from URL or defaults
  const market = searchParams.get("market") || "All";
  const dte = searchParams.get("dte") || "Any";
  const structure = searchParams.get("structure") || "All";
  const statusParam = searchParams.get("status");
  const statusFilters = useMemo(() => {
    if (statusParam) {
      return statusParam.split(",").filter(Boolean);
    }
    return ["ok", "low_sample", "short_window", "data_issues"];
  }, [statusParam]);
  const groupId = searchParams.get("group") || "Any";
  const minTrades = Number(searchParams.get("min") || 0);
  const sortKey = searchParams.get("sort") || "sharpe";
  const sortDir = searchParams.get("dir") || "desc";
  const page = Number(searchParams.get("page") || 1);
  const q = searchParams.get("q") || "";

  // Helper to update URL params
  const updateParams = (newParams) => {
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      Object.entries(newParams).forEach(([k, v]) => {
        if (v === null || v === undefined || v === "" || (k === "page" && v === 1) || (k === "min" && v === 0)) {
          updated.delete(k);
        } else {
          updated.set(k, String(v));
        }
      });
      return updated;
    });
  };

  // Filter and compute options from raw items
  const allItems = data?.items || [];

  // Group counts and structure counts over all items
  const { groupOptions, structureOptions, statusCounts, largestGroupInfo, latestMigratedAt, migratedCount } = useMemo(() => {
    const sCounts = { ok: 0, low_sample: 0, short_window: 0, data_issues: 0, superseded: 0, empty: 0 };
    const structMap = new Map();
    const groupMap = new Map();
    let latestMigrated = null;
    let migCount = 0;

    for (const item of allItems) {
      const st = item.status;
      if (sCounts[st] !== undefined) {
        sCounts[st] += 1;
      }

      if (item.migrated_changed_basis) {
        migCount += 1;
      }
      if (item.migrated_at) {
        if (!latestMigrated || item.migrated_at > latestMigrated) {
          latestMigrated = item.migrated_at;
        }
      }

      if (item.structure) {
        structMap.set(item.structure, (structMap.get(item.structure) || 0) + 1);
      }

      const g = item.group;
      if (g && g.id) {
        if (!groupMap.has(g.id)) {
          groupMap.set(g.id, { id: g.id, label: g.label || g.id, count: 0, dataIssuesCount: 0 });
        }
        const gEntry = groupMap.get(g.id);
        gEntry.count += 1;
        if (item.status === "data_issues") {
          gEntry.dataIssuesCount += 1;
        }
      }
    }

    const sOptions = Array.from(structMap.entries()).map(([value, count]) => ({
      value,
      label: value.replace(/_/g, " "),
      count,
    }));

    const gOptions = Array.from(groupMap.values());

    let largest = null;
    for (const g of gOptions) {
      if (!largest || g.count > largest.count) {
        largest = g;
      }
    }

    return {
      groupOptions: gOptions,
      structureOptions: sOptions,
      statusCounts: sCounts,
      largestGroupInfo: largest,
      latestMigratedAt: latestMigrated,
      migratedCount: migCount,
    };
  }, [allItems]);

  // Apply filters
  const filteredRuns = useMemo(() => {
    return allItems.filter((run) => {
      // Market filter
      if (market !== "All") {
        const markets = run.markets || [];
        if (!markets.includes(market)) return false;
      }

      // DTE filter
      if (dte !== "Any") {
        const dtes = (run.dte || []).map(String);
        if (!dtes.includes(String(dte))) return false;
      }

      // Structure filter
      if (structure !== "All") {
        if (run.structure !== structure) return false;
      }

      // Status filter
      if (!statusFilters.includes(run.status)) {
        return false;
      }

      // Group filter
      if (groupId !== "Any") {
        if (run.group?.id !== groupId) return false;
      }

      // Min trades filter
      const trades = run.metrics?.num_trades ?? 0;
      if (trades < minTrades) return false;

      // Search query (if provided in URL)
      if (q) {
        const text = `${run.name || ""} ${run.id || ""}`.toLowerCase();
        if (!text.includes(q.toLowerCase())) return false;
      }

      return true;
    });
  }, [allItems, market, dte, structure, statusFilters, groupId, minTrades, q]);

  const clearFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  const handleStatusToggle = (key) => {
    let next;
    if (statusFilters.includes(key)) {
      next = statusFilters.filter((s) => s !== key);
    } else {
      next = [...statusFilters, key];
    }
    updateParams({ status: next.join(","), page: 1 });
  };

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <Skeleton width="200px" height="32px" />
        <Skeleton width="100%" height="48px" />
        <div style={{ display: "grid", gridTemplateColumns: "240px minmax(0,1fr)", gap: "16px" }}>
          <Skeleton width="100%" height="400px" />
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <Skeleton width="100%" height="330px" />
            <Skeleton width="100%" height="300px" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Banner intent="danger">
          Failed to load runs: {error.message || "Unknown error"}
        </Banner>
        <div style={{ marginTop: "16px" }}>
          <Button onClick={reload}>Retry</Button>
        </div>
      </div>
    );
  }

  // Sub-line copy calculation
  const emptyCount = statusCounts.empty || 0;
  const supersededCount = statusCounts.superseded || 0;
  let subLineExtra = "";
  if (largestGroupInfo) {
    const gLabel = largestGroupInfo.label || largestGroupInfo.id;
    const gCount = largestGroupInfo.count;
    const dataIssuesInGroup = largestGroupInfo.dataIssuesCount;
    if (dataIssuesInGroup > 0) {
      if (dataIssuesInGroup === gCount) {
        subLineExtra = ` · ${gCount} belong to the ${gLabel} · all ${gCount} have more than 5% forced data exits`;
      } else {
        subLineExtra = ` · ${gCount} belong to the ${gLabel} · ${dataIssuesInGroup} of them have more than 5% forced data exits`;
      }
    } else {
      subLineExtra = ` · ${gCount} belong to the ${gLabel}`;
    }
  }

  const subLine = `${emptyCount} empty and ${supersededCount} superseded runs hidden${subLineExtra}`;

  return (
    <>
      {/* Toast */}
      {toast && (
        <div
          className="toast"
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 9999,
          }}
        >
          {toast}
        </div>
      )}

      {/* Header row */}
      <section style={{ display: "flex", alignItems: "flex-end", gap: "16px", marginBottom: "16px" }}>
        <div style={{ flex: 1 }}>
          <div className="eyebrow">Library</div>
          <h1 style={{ margin: "4px 0 0", fontSize: "28px", fontWeight: 600 }}>
            {filteredRuns.length} runs
          </h1>
          <div className="muted" style={{ fontSize: "13px" }}>
            {subLine}
          </div>
        </div>
        <button
          className="btn"
          disabled={selectedIds.length < 2}
          onClick={() => navigate(`/compare?ids=${selectedIds.join(",")}`)}
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="8" y1="4" x2="8" y2="20" />
            <line x1="16" y1="4" x2="16" y2="20" />
            <polyline points="4 8 8 4 12 8" />
            <polyline points="12 16 16 20 20 16" />
          </svg>
          Compare selected ({selectedIds.length})
        </button>
        <Link to="/new" className="btn btn--primary">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New run
        </Link>
      </section>

      {/* Migration info banner */}
      {migratedCount > 0 && (
        <div
          className="banner"
          style={{
            borderColor: "rgba(90,176,255,.35)",
            background: "var(--info-bg, rgba(90,176,255,.08))",
            color: "var(--info)",
            marginBottom: "16px",
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="11" x2="12" y2="16" />
            <line x1="12" y1="8" x2="12" y2="8.01" />
          </svg>
          <span>
            All metrics use the <b>calendar_daily</b> basis: every exchange session, idle days included.{" "}
            {migratedCount} older runs were recomputed on {latestMigratedAt ? dateIST(latestMigratedAt) : "—"}.
          </span>
          {hasMigrationReport && (
            <a
              href="/api/migration-report"
              target="_blank"
              rel="noreferrer"
              style={{ marginLeft: "auto" }}
            >
              Migration report →
            </a>
          )}
        </div>
      )}

      {/* Main Grid: Filters + Right column */}
      <div className="grid" style={{ gridTemplateColumns: "240px minmax(0,1fr)", gap: "16px" }}>
        <LibraryFilters
          market={market}
          onMarketChange={(m) => updateParams({ market: m, page: 1 })}
          dte={dte}
          onDteChange={(d) => updateParams({ dte: d, page: 1 })}
          structure={structure}
          onStructureChange={(s) => updateParams({ structure: s, page: 1 })}
          structureOptions={structureOptions}
          statusFilters={statusFilters}
          onStatusToggle={handleStatusToggle}
          statusCounts={statusCounts}
          groupId={groupId}
          onGroupChange={(g) => updateParams({ group: g, page: 1 })}
          groupOptions={groupOptions}
          minTrades={minTrades}
          onMinTradesChange={(min) => updateParams({ min, page: 1 })}
        />

        <div className="grid" style={{ gap: "16px" }}>
          {filteredRuns.length === 0 ? (
            <EmptyState
              title="No runs match these filters"
              description="Try broadening your market, DTE or status filters."
              action={<Button onClick={clearFilters}>Clear filters</Button>}
            />
          ) : (
            <>
              {/* Row A: Scatter + Leaders */}
              <div
                className="grid"
                style={{ gridTemplateColumns: "minmax(0,1fr) 380px", gap: "16px" }}
              >
                <LibraryScatter runs={filteredRuns} />
                <Leaders runs={filteredRuns} />
              </div>

              {/* Row B: RunsTable */}
              <RunsTable
                runs={filteredRuns}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                sortKey={sortKey}
                sortDir={sortDir}
                onSortChange={(k, d) => updateParams({ sort: k, dir: d, page: 1 })}
                page={page}
                pageSize={25}
                onPageChange={(p) => updateParams({ page: p })}
                onMaxSelectedNotice={() => showToast("Compare holds 4 runs")}
              />
            </>
          )}
        </div>
      </div>
    </>
  );
}
