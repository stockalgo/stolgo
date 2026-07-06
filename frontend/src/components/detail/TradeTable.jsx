import { dateLabel, money, price } from "../../utils/formatters";

export function TradeTable({ selectedTrade, setSelectedTrade, visibleTrades }) {
  return (
    <div className="trade-table-wrap">
      <table className="trade-table">
        <thead>
          <tr>
            <th>#</th><th>Entry time</th><th>Exit time</th><th>Side</th><th>Entry price</th><th>Exit price</th><th>Qty</th><th>Net PnL</th><th>R</th><th>Tag</th>
          </tr>
        </thead>
        <tbody>
          {visibleTrades.map((trade) => (
            <tr className={selectedTrade?.id === trade.id ? "selected" : ""} key={trade.id} onClick={() => setSelectedTrade(trade)}>
              <td>{trade.id}</td><td>{dateLabel(trade.entryTime)}</td><td>{dateLabel(trade.exitTime)}</td>
              <td className={trade.side === "Long" ? "positive" : "negative"}>{trade.side}</td>
              <td>{price(trade.entryPrice)}</td><td>{price(trade.exitPrice)}</td><td>{trade.qty}</td>
              <td className={trade.pnlClass}>{money(trade.pnl)}</td><td className={trade.pnlClass}>{trade.r}R</td><td>{trade.tag}</td>
            </tr>
          ))}
          {visibleTrades.length === 0 && (
            <tr>
              <td colSpan="10">No trades for this run.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
