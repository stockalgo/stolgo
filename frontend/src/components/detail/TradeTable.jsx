import { dateLabel, money, price } from "../../utils/formatters";

export function TradeTable({ currency, selectedTrade, setSelectedTrade, timeZone, visibleTrades }) {
  const getLotInfo = (qty, tag) => {
    if (!qty) return "-";
    // NIFTY lot sizes commonly 25, 50, 65, 75. SENSEX commonly 10, 20.
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

  return (
    <div className="trade-table-wrap">
      <table className="trade-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Entry time</th>
            <th>Exit time</th>
            <th>Side</th>
            <th>Entry premium</th>
            <th>Exit premium</th>
            <th>Qty</th>
            <th>Gross PnL</th>
            <th>Costs</th>
            <th>Net PnL</th>
            <th>R</th>
            <th>Strategy Tag</th>
          </tr>
        </thead>
        <tbody>
          {visibleTrades.map((trade) => (
            <tr
              className={selectedTrade?.id === trade.id ? "selected" : ""}
              key={trade.id}
              onClick={() => setSelectedTrade(trade)}
            >
              <td>{trade.id}</td>
              <td>{dateLabel(trade.entryTime, timeZone)}</td>
              <td>{dateLabel(trade.exitTime, timeZone)}</td>
              <td>
                <span className={`side-badge ${trade.side === "Short" ? "negative" : "positive"}`}>
                  {trade.side}
                </span>
              </td>
              <td>{price(trade.entryPrice)}</td>
              <td>{price(trade.exitPrice)}</td>
              <td title={`Quantity: ${trade.qty}`}>{getLotInfo(trade.qty, trade.tag)}</td>
              <td className={trade.grossPnl >= 0 ? "positive" : "negative"}>
                {money(trade.grossPnl ?? trade.pnl, currency)}
              </td>
              <td className="cost-cell">
                {trade.commission > 0 ? `-${money(trade.commission, currency)}` : "-"}
              </td>
              <td className={trade.pnlClass}>
                <b>{money(trade.pnl, currency)}</b>
              </td>
              <td className={trade.pnlClass}>{trade.r}R</td>
              <td><code>{trade.tag || "-"}</code></td>
            </tr>
          ))}
          {visibleTrades.length === 0 && (
            <tr>
              <td colSpan="12">No trades found for this filter.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
