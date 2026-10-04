import React, { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { listRuns } from "../../api/endpoints.js";

const STATIC_ACTIONS = [
  { id: "action-library", title: "Go to Library", category: "Action", path: "/" },
  { id: "action-compare", title: "Open Compare", category: "Action", path: "/compare" },
  { id: "action-groups", title: "Open Groups", category: "Action", path: "/groups" },
  { id: "action-new", title: "New run", category: "Action", path: "/new" },
];

export function CommandPalette({ isOpen, onClose }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [runs, setRuns] = useState([]);
  const inputRef = useRef(null);

  // Fetch runs once
  useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((data) => {
        if (!cancelled && data?.items) {
          setRuns(data.items);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Reset query and focus on open
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  // Check if currently on a run page
  const currentRunId = useMemo(() => {
    const m = location.pathname.match(/^\/runs\/([^/]+)/);
    return m ? m[1] : null;
  }, [location.pathname]);

  // Compute results (max 8)
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const items = [];

    // 1. Trade jump if on a run page and query is e.g. "#157" or "157"
    if (currentRunId && (q.startsWith("#") || /^\d+$/.test(q))) {
      const tradeNum = q.replace(/^#/, "");
      if (tradeNum) {
        items.push({
          id: `trade-${tradeNum}`,
          title: `Trade #${tradeNum}`,
          subtitle: `Jump to trade in run ${currentRunId}`,
          category: "Trade",
          onSelect: () => {
            navigate(`/runs/${currentRunId}/trades?trade=${tradeNum}`);
            onClose();
          },
        });
      }
    }

    if (!q) {
      // Default: static actions + top 4 runs
      STATIC_ACTIONS.forEach((act) => {
        items.push({
          id: act.id,
          title: act.title,
          category: act.category,
          onSelect: () => {
            navigate(act.path);
            onClose();
          },
        });
      });

      runs.slice(0, 4).forEach((r) => {
        items.push({
          id: `run-${r.id}`,
          title: r.name || r.id,
          subtitle: r.id,
          category: "Run",
          onSelect: () => {
            navigate(`/runs/${r.id}`);
            onClose();
          },
        });
      });

      return items.slice(0, 8);
    }

    // Filter static actions
    STATIC_ACTIONS.forEach((act) => {
      if (act.title.toLowerCase().includes(q)) {
        items.push({
          id: act.id,
          title: act.title,
          category: act.category,
          score: act.title.toLowerCase().indexOf(q),
          onSelect: () => {
            navigate(act.path);
            onClose();
          },
        });
      }
    });

    // Filter runs
    const matchedRuns = [];
    runs.forEach((r) => {
      const name = (r.name || "").toLowerCase();
      const id = (r.id || "").toLowerCase();
      const grp = (r.group?.label || r.group?.id || "").toLowerCase();

      let score = Infinity;
      const idxName = name.indexOf(q);
      const idxId = id.indexOf(q);
      const idxGrp = grp.indexOf(q);

      if (idxName !== -1) score = Math.min(score, idxName);
      if (idxId !== -1) score = Math.min(score, idxId);
      if (idxGrp !== -1) score = Math.min(score, idxGrp + 5);

      if (score !== Infinity) {
        matchedRuns.push({
          id: `run-${r.id}`,
          title: r.name || r.id,
          subtitle: r.id,
          category: "Run",
          score,
          onSelect: () => {
            navigate(`/runs/${r.id}`);
            onClose();
          },
        });
      }
    });

    // Rank runs by position
    matchedRuns.sort((a, b) => a.score - b.score);

    const combined = [...items, ...matchedRuns];
    return combined.slice(0, 8);
  }, [query, runs, currentRunId, navigate, onClose]);

  // Adjust selectedIndex when results change
  useEffect(() => {
    if (selectedIndex >= results.length) {
      setSelectedIndex(Math.max(0, results.length - 1));
    }
  }, [results, selectedIndex]);

  // Key navigation
  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[selectedIndex]) {
        results[selectedIndex].onSelect();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="command-palette-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "var(--bg-overlay, rgba(4, 6, 8, 0.72))",
        zIndex: 9999,
        display: "flex",
        justifyContent: "center",
        paddingTop: 100,
      }}
      onClick={onClose}
    >
      <div
        className="panel command-palette"
        style={{
          width: 580,
          maxHeight: 460,
          padding: 0,
          display: "flex",
          flexDirection: "column",
          borderRadius: "var(--r-md)",
          boxShadow: "var(--shadow-pop)",
          background: "var(--bg-panel)",
          border: "1px solid var(--line-strong)",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 16px",
            borderBottom: "1px solid var(--line)",
          }}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-3)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.5" y2="16.5" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            className="input"
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              fontSize: 15,
              color: "var(--text-1)",
              padding: 0,
            }}
            placeholder="Jump to run, trade #, action…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <span className="kbd" style={{ fontSize: 10, padding: "2px 5px" }}>
            ESC
          </span>
        </div>

        {/* Results List */}
        <div
          style={{
            padding: 6,
            overflowY: "auto",
            maxHeight: 380,
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          {results.length === 0 ? (
            <div
              className="muted"
              style={{ padding: "24px 16px", textAlign: "center", fontSize: 13 }}
            >
              No results found for “{query}”
            </div>
          ) : (
            results.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  role="option"
                  aria-selected={isSelected}
                  style={{
                    padding: "8px 12px",
                    borderRadius: "var(--r-sm)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    cursor: "pointer",
                    background: isSelected ? "var(--bg-raised)" : "transparent",
                    outline: isSelected ? "1px solid var(--accent)" : "none",
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  onClick={item.onSelect}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-1)" }}>
                      {item.title}
                    </div>
                    {item.subtitle && (
                      <div className="mono muted" style={{ fontSize: 11 }}>
                        {item.subtitle}
                      </div>
                    )}
                  </div>
                  <span
                    className="muted"
                    style={{
                      fontSize: 10,
                      textTransform: "uppercase",
                      letterSpacing: 0.5,
                      padding: "2px 6px",
                      borderRadius: 3,
                      background: "var(--line-faint)",
                    }}
                  >
                    {item.category}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
