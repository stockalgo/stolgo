import React, { useState, useEffect, useCallback } from "react";
import { useParams, Outlet, Link } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { getRun } from "../api/endpoints.js";
import { RunHeader } from "../components/run/RunHeader.jsx";
import { RunTabs } from "../components/run/RunTabs.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { Skeleton } from "../components/ui/Skeleton.jsx";
import { useBreadcrumbs } from "../context/BreadcrumbContext.jsx";

export function RunLayout() {
  const { runId } = useParams();
  const { setCrumbs } = useBreadcrumbs();
  const [toast, setToast] = useState(null);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };

  const fetchRun = useCallback(() => getRun(runId), [runId]);
  const { data: run, loading, error } = useApi(fetchRun);

  useEffect(() => {
    if (runId) {
      try {
        sessionStorage.setItem("stolgo.lastRun", runId);
      } catch {
        // ignore
      }
    }
  }, [runId]);

  useEffect(() => {
    if (run) {
      const marketsStr = (run.markets || []).join("+");
      const structStr = (run.structure || "").replace(/_/g, " ");
      const groupLabel =
        run.group?.label ||
        (run.group?.id ? run.group.id.replace(/-/g, " ") : null) ||
        (marketsStr && structStr ? `${marketsStr} · ${structStr}` : marketsStr || "Run");

      setCrumbs(
        <>
          <Link to="/" style={{ color: "inherit", textDecoration: "none" }}>
            Library
          </Link>
          <span className="sep">/</span>
          <span>{groupLabel}</span>
          <span className="sep">/</span>
          <b>{run.id}</b>
        </>
      );
    }
    return () => {
      setCrumbs(null);
    };
  }, [run, setCrumbs]);

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <Skeleton width="340px" height="36px" />
        <Skeleton width="100%" height="42px" />
        <Skeleton width="100%" height="400px" />
      </div>
    );
  }

  if (error || !run) {
    return (
      <EmptyState
        title={`Run "${runId}" not found`}
        description="The requested run could not be loaded or does not exist."
        action={
          <Link to="/" className="btn btn--primary">
            Go to Library
          </Link>
        }
      />
    );
  }

  return (
    <>
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

      <RunHeader run={run} />
      <RunTabs run={run} onToast={showToast} />
      <Outlet context={{ run, onToast: showToast }} />
    </>
  );
}
