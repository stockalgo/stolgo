import React from "react";
import { Button } from "./Button.jsx";

export function Pagination({
  page = 1,
  pageSize = 25,
  total = 0,
  onPageChange,
  label = "",
  sortDir = "desc",
}) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  const totalPages = Math.ceil(total / pageSize) || 1;

  const hasPrev = page > 1;
  const hasNext = page < totalPages;

  return (
    <div
      className="pagination"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 16px",
        fontSize: "12px",
        color: "var(--text-muted)",
        borderTop: "1px solid var(--line)",
      }}
    >
      <div>
        Showing {start}–{end} of {total}
        {label ? ` · sorted by ${label} ${sortDir === "asc" ? "↑" : "↓"}` : ""}
      </div>
      <div style={{ display: "flex", gap: "6px" }}>
        <Button size="sm" disabled={!hasPrev} onClick={() => onPageChange && onPageChange(page - 1)}>
          Prev
        </Button>
        <Button size="sm" disabled={!hasNext} onClick={() => onPageChange && onPageChange(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
