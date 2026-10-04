import React from "react";

export function DataTable({
  columns = [],
  data = [],
  sortKey = null,
  sortDir = "desc",
  onSort = null,
  dense = false,
  rowKey = "id",
  onRowClick = null,
  selectedRowKey = null,
  rowStyle = null,
  expandedRowKey = null,
  expandedRowRender = null,
  className = "",
  tfoot = null,
}) {
  const getRowId = (row, idx) => (typeof rowKey === "function" ? rowKey(row, idx) : row[rowKey] ?? idx);

  const handleHeaderClick = (col) => {
    if (col.sortable && onSort) {
      onSort(col.key);
    }
  };

  return (
    <div className={`table-wrap ${className}`}>
      <table className={`table ${dense ? "table--dense" : ""}`}>
        <thead>
          <tr>
            {columns.map((col) => {
              const isSorted = sortKey === col.key;
              const ariaSort = isSorted ? (sortDir === "asc" ? "ascending" : "descending") : undefined;
              const headerClasses = [
                col.num ? "num" : "",
                col.sortable ? "sortable" : "",
              ]
                .filter(Boolean)
                .join(" ");

              return (
                <th
                  key={col.key}
                  className={headerClasses}
                  style={col.width ? { width: col.width } : undefined}
                  aria-sort={ariaSort}
                  title={col.title}
                  onClick={() => handleHeaderClick(col)}
                >
                  {col.label}
                  {col.sortable && isSorted && (
                    <span style={{ marginLeft: "4px", fontSize: "10px" }}>
                      {sortDir === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
                No records
              </td>
            </tr>
          ) : (
            data.map((row, idx) => {
              const id = getRowId(row, idx);
              const isSelected = selectedRowKey === id;
              const isExpanded = expandedRowKey === id;
              const customStyle = rowStyle ? rowStyle(row, idx) : {};

              return (
                <React.Fragment key={String(id)}>
                  <tr
                    aria-selected={isSelected ? "true" : undefined}
                    style={{
                      cursor: onRowClick ? "pointer" : undefined,
                      ...customStyle,
                    }}
                    onClick={() => onRowClick && onRowClick(row)}
                  >
                    {columns.map((col) => {
                      const cellClasses = col.num ? "num" : "";
                      return (
                        <td key={col.key} className={cellClasses}>
                          {col.render ? col.render(row, idx) : row[col.key]}
                        </td>
                      );
                    })}
                  </tr>
                  {isExpanded && expandedRowRender && (
                    <tr>
                      <td colSpan={columns.length} style={{ padding: 0 }}>
                        {expandedRowRender(row, idx)}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })
          )}
        </tbody>
        {tfoot && <tfoot>{tfoot}</tfoot>}
      </table>
    </div>
  );
}
