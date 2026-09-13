import { useMemo, useState } from "react";
import { dateLabel, money, price } from "../../utils/formatters";

const COLUMNS = [
  { key: "id", label: "#", align: "center" },
  { key: "entryTime", label: "Entry time", align: "left" },
  { key: "exitTime", label: "Exit time", align: "left" },
  { key: "side", label: "Side", align: "center" },
  { key: "entryPrice", label: "Entry premium", align: "right" },
  { key: "exitPrice", label: "Exit premium", align: "right" },
  { key: "qty", label: "Qty", align: "right" },
  { key: "grossPnl", label: "Gross PnL", align: "right" },
  { key: "costs", label: "Costs", align: "right" },
  { key: "pnl", label: "Net PnL", align: "right" },
  { key: "r", label: "R", align: "right" },
  { key: "tag", label: "Strategy Tag", align: "left" },
];

export function TradeTable({ currency, selectedTrade, setSelectedTrade, timeZone, visibleTrades }) {
  const [sortConfig, setSortConfig] = useState({ key: "entryTime", direction: "asc" });

  const getLotInfo = (qty, tag) => {
    if (!qty) return "-";
    const numQty = Number(qty);
    if (tag && tag.toLowerCase().includes("nifty")) {
      if (numQty % 65 === 0) return `${numQty} (${numQty / 65}L)`;
      if (numQty % 50 === 0) return `${numQty} (${numQty / 50}L)`;
      if (numQty % 25 === 0) return `${numQty} (${numQty / 25}L)`;
    }
    if (tag && tag.toLowerCase().includes("sensex")) {
      if (numQty % 10 === 0) return `${numQty} (${numQty / 10}L)`;
      if (numQty % 20 === 0) return `${numQty} (${numQty / 20}L)`;
    }
    return String(numQty);
  };

  const handleSort = (key) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        return { key, direction: prev.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "desc" };
    });
  };

  const sortedTrades = useMemo(() => {
    if (!sortConfig.key) return visibleTrades;

    return [...visibleTrades].sort((a, b) => {
      let aVal;
      let bVal;

      switch (sortConfig.key) {
        case "id":
          aVal = Number(a.id) || 0;
          bVal = Number(b.id) || 0;
          break;
        case "entryTime":
          aVal = Number(a.entryTime) || 0;
          bVal = Number(b.entryTime) || 0;
          break;
        case "exitTime":
          aVal = Number(a.exitTime) || 0;
          bVal = Number(b.exitTime) || 0;
          break;
        case "side":
          aVal = String(a.side || "");
          bVal = String(b.side || "");
          break;
        case "entryPrice":
          aVal = Number(a.entryPrice) || 0;
          bVal = Number(b.entryPrice) || 0;
          break;
        case "exitPrice":
          aVal = Number(a.exitPrice) || 0;
          bVal = Number(b.exitPrice) || 0;
          break;
        case "qty":
          aVal = Number(a.qty) || 0;
          bVal = Number(b.qty) || 0;
          break;
        case "grossPnl":
          aVal = Number(a.grossPnl ?? a.pnl) || 0;
          bVal = Number(b.grossPnl ?? b.pnl) || 0;
          break;
        case "costs":
          aVal = Number(a.commission) || 0;
          bVal = Number(b.commission) || 0;
          break;
        case "pnl":
          aVal = Number(a.pnl) || 0;
          bVal = Number(b.pnl) || 0;
          break;
        case "r":
          aVal = parseFloat(a.r) || 0;
          bVal = parseFloat(b.r) || 0;
          break;
        case "tag":
          aVal = String(a.tag || "");
          bVal = String(b.tag || "");
          break;
        default:
          return 0;
      }

      if (typeof aVal === "string") {
        return sortConfig.direction === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return sortConfig.direction === "asc" ? aVal - bVal : bVal - aVal;
    });
  }, [visibleTrades, sortConfig]);

  return (
    <div className="trade-table-wrap">
      <table className="trade-table">
        <thead>
          <tr>
            {COLUMNS.map((col) => {
              const isActive = sortConfig.key === col.key;
              return (
                <th
                  key={col.key}
                  className={`sortable-th text-${col.align} ${isActive ? "active-sort" : ""}`}
                  onClick={() => handleSort(col.key)}
                  title={`Sort by ${col.label}`}
                >
                  <span className="th-content">
                    {col.label}
                    <span className={`sort-icon ${isActive ? "active" : ""}`}>
                      {isActive ? (sortConfig.direction === "asc" ? " ▲" : " ▼") : " ⇅"}
                    </span>
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedTrades.map((trade) => (
            <tr
              className={selectedTrade?.id === trade.id ? "selected" : ""}
              key={trade.id}
              onClick={() => setSelectedTrade(trade)}
            >
              <td className="text-center mono-cell">{trade.id}</td>
              <td className="mono-cell">{dateLabel(trade.entryTime, timeZone)}</td>
              <td className="mono-cell">{dateLabel(trade.exitTime, timeZone)}</td>
              <td className="text-center">
                <span className={`side-badge ${trade.side === "Short" ? "negative" : "positive"}`}>
                  {trade.side}
                </span>
              </td>
              <td className="text-right num-cell">{price(trade.entryPrice)}</td>
              <td className="text-right num-cell">{price(trade.exitPrice)}</td>
              <td className="text-right num-cell" title={`Quantity: ${trade.qty}`}>
                {getLotInfo(trade.qty, trade.tag)}
              </td>
              <td className={`text-right num-cell ${trade.grossPnl >= 0 ? "positive" : "negative"}`}>
                {money(trade.grossPnl ?? trade.pnl, currency)}
              </td>
              <td className="text-right num-cell cost-cell">
                {trade.commission > 0 ? `-${money(trade.commission, currency)}` : "-"}
              </td>
              <td className={`text-right num-cell ${trade.pnlClass}`}>
                <b>{money(trade.pnl, currency)}</b>
              </td>
              <td className={`text-right num-cell ${trade.pnlClass}`}>
                {trade.r !== undefined && trade.r !== null ? `${trade.r}R` : "-"}
              </td>
              <td className="tag-cell"><code>{trade.tag || "-"}</code></td>
            </tr>
          ))}
          {sortedTrades.length === 0 && (
            <tr>
              <td colSpan="12" className="empty-table-cell">No trades found for this filter.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
