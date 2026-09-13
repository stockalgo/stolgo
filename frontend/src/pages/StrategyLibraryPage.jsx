import { useMemo, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { percent } from "../utils/formatters";

export function StrategyLibraryPage({ loading, onOpenDetail, runs }) {
  const [query, setQuery] = useState("");
  const [marketFilter, setMarketFilter] = useState("All");
  const [sortBy, setSortBy] = useState("sharpe");

  const filteredRuns = useMemo(() => {
    let list = runs.filter((run) => {
      const q = query.toLowerCase();
      const matchesQuery = !query ||
        run.strategy.toLowerCase().includes(q) ||
        run.market.toLowerCase().includes(q) ||
        run.id.toLowerCase().includes(q) ||
        (run.timeframe && run.timeframe.toLowerCase().includes(q));

      const matchesMarket = marketFilter === "All" || run.market.toUpperCase() === marketFilter.toUpperCase();
      return matchesQuery && matchesMarket;
    });

    return list.sort((a, b) => {
      if (sortBy === "return") return (b.return || 0) - (a.return || 0);
      if (sortBy === "sharpe") return (b.sharpe || 0) - (a.sharpe || 0);
      if (sortBy === "drawdown") return (b.drawdown || 0) - (a.drawdown || 0);
      if (sortBy === "trades") return (b.trades || 0) - (a.trades || 0);
      return 0;
    });
  }, [runs, query, marketFilter, sortBy]);

  return (
    <div className="page-flow">
      <PageHeader
        eyebrow="Strategy library"
        title="Find the strategies worth inspecting"
        description="Filter and sort real backtest runs across NIFTY, SENSEX, and multi-DTE options strategies."
      />
      <section className="library-toolbar surface-panel">
        <input
          aria-label="Search strategies"
          placeholder="Search strategy, index, DTE..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {["All", "NIFTY", "SENSEX"].map((m) => (
          <button
            key={m}
            type="button"
            className={marketFilter === m ? "active" : ""}
            onClick={() => setMarketFilter(m)}
          >
            {m}
          </button>
        ))}
        <button
          type="button"
          className={sortBy === "sharpe" ? "active" : ""}
          onClick={() => setSortBy("sharpe")}
        >
          Sort: Sharpe
        </button>
        <button
          type="button"
          className={sortBy === "return" ? "active" : ""}
          onClick={() => setSortBy("return")}
        >
          Sort: Return
        </button>
        <button
          type="button"
          className={sortBy === "drawdown" ? "active" : ""}
          onClick={() => setSortBy("drawdown")}
        >
          Sort: Drawdown
        </button>
      </section>
      <section className="strategy-table surface-panel">
        <div className="library-row library-head">
          <span>Strategy</span><span>Market</span><span>Return</span><span>Sharpe</span><span>Drawdown</span><span>Trades</span>
        </div>
        {loading && <div className="empty-state">Loading runs...</div>}
        {!loading && filteredRuns.length === 0 && <div className="empty-state">No matching runs found.</div>}
        {filteredRuns.map((run) => (
          <button className="library-row" key={run.id} type="button" onClick={() => onOpenDetail(run.id)}>
            <span><b>{run.strategy}</b><em>Last run {run.created_at ? new Date(run.created_at).toLocaleString() : "-"}</em></span>
            <span>{run.market} · {run.timeframe}</span>
            <span className={run.return >= 0 ? "positive" : "negative"}>{percent(run.return)}</span>
            <span>{Number(run.sharpe).toFixed(2)}</span>
            <span className="negative">{percent(run.drawdown)}</span>
            <span>{run.trades.toLocaleString()}</span>
          </button>
        ))}
      </section>
    </div>
  );
}
