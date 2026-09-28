import React from "react";

export function TopBar({ crumbs, onOpenPalette }) {
  return (
    <header className="topbar">
      <div className="crumbs">{crumbs || <b>Library</b>}</div>
      <label className="cmdk" onClick={onOpenPalette} style={{ cursor: "pointer" }}>
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.5" y2="16.5" />
        </svg>
        <input
          aria-label="Command bar"
          placeholder="Jump to run, trade #, date, metric…"
          readOnly
          style={{ cursor: "pointer" }}
        />
        <span className="kbd">⌘K</span>
      </label>
    </header>
  );
}
