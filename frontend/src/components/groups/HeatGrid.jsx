import React from "react";
import { pct, ratio } from "../../lib/format.js";

export function HeatGrid({
  rows = [],
  cols = [],
  cellData,
  cellMetric = "return",
  selectedCell = null,
  onSelectCell,
}) {
  const getCellStyle = (cell) => {
    if (!cell || cell.count === 0) {
      return {
        bg: "#111418",
        color: "var(--text-3)",
        label: "—",
        count: 0,
      };
    }

    let alpha = 0.5;
    let isPos = true;
    let label = "—";

    if (cellMetric === "return") {
      const v = (cell.meanReturn || 0) * 100;
      isPos = v >= 0;
      alpha = Math.min(0.95, 0.12 + Math.abs(v) / 18);
      label = pct(cell.meanReturn, { signed: true });
    } else if (cellMetric === "sharpe") {
      const v = cell.meanSharpe || 0;
      isPos = v >= 0;
      alpha = Math.min(0.95, 0.12 + Math.abs(v) / 1.0);
      label = ratio(cell.meanSharpe);
    } else if (cellMetric === "max_dd") {
      const v = Math.abs((cell.worstDD || 0) * 100);
      isPos = false; // adverse
      alpha = Math.min(0.95, 0.12 + v / 25);
      label = pct(cell.worstDD);
    } else if (cellMetric === "pct_pos") {
      const ratioVal = cell.posRatio || 0;
      isPos = ratioVal >= 0.5;
      alpha = Math.min(0.95, 0.12 + Math.abs(ratioVal - 0.5) * 1.5);
      label = `${(ratioVal * 100).toFixed(1)}%`;
    }

    const bg = isPos
      ? `rgba(90, 176, 255, ${alpha.toFixed(2)})`
      : `rgba(224, 122, 69, ${alpha.toFixed(2)})`;
    const color = alpha > 0.6 ? "#0a0c0e" : "#e6e8ea";

    return { bg, color, label, count: cell.count };
  };

  const colCount = Math.max(1, cols.length);

  return (
    <div
      className="heat"
      style={{
        gridTemplateColumns: `110px repeat(${colCount}, minmax(0, 1fr))`,
        gap: 4,
        fontSize: 12,
      }}
    >
      {/* Header row */}
      <span></span>
      {cols.map((col) => (
        <span
          key={col.key}
          className="mono"
          style={{
            textAlign: "center",
            color: "var(--text-2)",
            paddingBottom: 4,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={col.label}
        >
          {col.label}
        </span>
      ))}

      {/* Rows */}
      {rows.map((row) => (
        <React.Fragment key={row}>
          <span
            className="mono"
            style={{
              color: "var(--text-2)",
              alignSelf: "center",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={row}
          >
            {row}
          </span>
          {cols.map((col) => {
            const cell = cellData(row, col.key);
            const { bg, color, label, count } = getCellStyle(cell);
            const isSelected =
              selectedCell &&
              selectedCell.row === row &&
              selectedCell.col === col.key;

            return (
              <div
                key={`${row}-${col.key}`}
                role="button"
                tabIndex={0}
                className="heat__cell"
                style={{
                  height: 38,
                  background: bg,
                  color: color,
                  cursor: cell && cell.count > 0 ? "pointer" : "default",
                  ...(isSelected
                    ? {
                        outline: "2px solid var(--accent)",
                        outlineOffset: 1,
                      }
                    : {}),
                }}
                onClick={() => {
                  if (onSelectCell && cell && cell.count > 0) {
                    onSelectCell(row, col.key);
                  }
                }}
                onKeyDown={(e) => {
                  if (
                    (e.key === "Enter" || e.key === " ") &&
                    onSelectCell &&
                    cell &&
                    cell.count > 0
                  ) {
                    e.preventDefault();
                    onSelectCell(row, col.key);
                  }
                }}
              >
                {count > 0 ? (
                  <span>
                    {label}
                    <span style={{ opacity: 0.7, fontSize: 10 }}>
                      {" "}
                      ·{count}
                    </span>
                  </span>
                ) : (
                  <span>—</span>
                )}
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
}
