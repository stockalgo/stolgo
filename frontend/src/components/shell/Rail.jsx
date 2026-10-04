import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

export function Rail() {
  const location = useLocation();
  const navigate = useNavigate();
  const pathname = location.pathname;

  const lastRunId = typeof window !== "undefined" ? sessionStorage.getItem("stolgo.lastRun") : null;

  const isLibrary = pathname === "/";
  const isRun = pathname.startsWith("/runs/") && !pathname.endsWith("/chart");
  const isCompare = pathname.startsWith("/compare");
  const isGroups = pathname.startsWith("/groups");
  const isNew = pathname === "/new";

  return (
    <nav className="rail" aria-label="Primary">
      <div className="rail__logo" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
        S
      </div>

      <button
        className="rail__btn"
        aria-current={isLibrary ? "page" : undefined}
        aria-label="Library"
        title="Library"
        onClick={() => navigate("/")}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      </button>

      <button
        className="rail__btn"
        aria-current={isRun ? "page" : undefined}
        aria-label="Run"
        title={lastRunId ? `Run (${lastRunId})` : "Run (no run opened yet)"}
        disabled={!lastRunId}
        style={{ opacity: lastRunId ? 1 : 0.4, cursor: lastRunId ? "pointer" : "not-allowed" }}
        onClick={() => lastRunId && navigate(`/runs/${encodeURIComponent(lastRunId)}`)}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="3 17 9 11 13 15 21 7" />
          <polyline points="15 7 21 7 21 13" />
        </svg>
      </button>

      <button
        className="rail__btn"
        aria-current={isCompare ? "page" : undefined}
        aria-label="Compare"
        title="Compare"
        onClick={() => navigate("/compare")}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="8" y1="4" x2="8" y2="20" />
          <line x1="16" y1="4" x2="16" y2="20" />
          <polyline points="4 8 8 4 12 8" />
          <polyline points="12 16 16 20 20 16" />
        </svg>
      </button>

      <button
        className="rail__btn"
        aria-current={isGroups ? "page" : undefined}
        aria-label="Groups"
        title="Groups"
        onClick={() => navigate("/groups")}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="6" cy="6" r="2" />
          <circle cx="18" cy="6" r="2" />
          <circle cx="6" cy="18" r="2" />
          <circle cx="18" cy="18" r="2" />
          <circle cx="12" cy="12" r="2" />
        </svg>
      </button>

      <button
        className="rail__btn"
        aria-current={isNew ? "page" : undefined}
        aria-label="New run"
        title="New run"
        onClick={() => navigate("/new")}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>

      <div className="rail__spacer" />

      <button className="rail__btn" aria-label="Help" title="Help">
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5V14" />
          <line x1="12" y1="17" x2="12" y2="17.01" />
        </svg>
      </button>
    </nav>
  );
}
