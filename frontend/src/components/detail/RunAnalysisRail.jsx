import { dateLabel, money } from "../../utils/formatters";

function Stat({ label, value, tone = "neutral" }) {
  return (
    <div className="rail-stat">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  );
}

function signedMoney(value) {
  return value >= 0 ? money(value) : `-${money(Math.abs(value))}`;
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function tradeDistribution(trades) {
  const wins = trades.filter((trade) => trade.pnl > 0);
  const losses = trades.filter((trade) => trade.pnl < 0);
  const best = trades.reduce((current, trade) => (trade.pnl > current.pnl ? trade : current), trades[0]);
  const worst = trades.reduce((current, trade) => (trade.pnl < current.pnl ? trade : current), trades[0]);

  return {
    wins,
    losses,
    best,
    worst,
    avgWinner: average(wins.map((trade) => trade.pnl)),
    avgLoser: average(losses.map((trade) => trade.pnl)),
  };
}

function distributionBars(trades) {
  if (!trades.length) return [];
  const maxAbs = Math.max(...trades.map((trade) => Math.abs(trade.pnl)), 1);
  return trades.slice(0, 24).map((trade) => ({
    id: trade.id,
    height: Math.max(8, (Math.abs(trade.pnl) / maxAbs) * 58),
    tone: trade.pnl >= 0 ? "positive" : "negative",
  }));
}

function drawdownStats(drawdown) {
  if (!drawdown.length) return { max: 0, current: 0, underwater: 0 };
  const max = drawdown.reduce((min, point) => Math.min(min, point.value), 0);
  const current = drawdown.at(-1)?.value ?? 0;
  const underwater = drawdown.filter((point) => point.value < 0).length;
  return { max, current, underwater };
}

export function RunAnalysisRail({ data, detail, onSelectTrade, run }) {
  const trades = data.trades ?? [];
  const candles = data.candles ?? [];
  const equity = data.equity ?? [];
  const drawdown = data.drawdown ?? [];
  const distribution = trades.length ? tradeDistribution(trades) : null;
  const bars = distributionBars(trades);
  const dd = drawdownStats(drawdown);
  const firstCandle = candles[0];
  const lastCandle = candles.at(-1);
  const finalEquity = equity.at(-1)?.value;

  return (
    <aside className="analysis-rail" aria-label="Run analysis">
      <section className="rail-panel">
        <div className="rail-heading">
          <span>Run facts</span>
          <h2>{run?.market ?? "-"} {run?.timeframe ?? "-"}</h2>
        </div>
        <div className="rail-stat-grid">
          <Stat label="Candles" value={candles.length.toLocaleString()} />
          <Stat label="Trades" value={trades.length.toLocaleString()} />
          <Stat label="Final equity" value={finalEquity === undefined ? "-" : money(finalEquity)} />
          <Stat label="Profit factor" value={Number(detail?.rawMetrics?.profit_factor ?? 0).toFixed(2)} />
        </div>
        {firstCandle && lastCandle && (
          <p className="rail-note">{dateLabel(firstCandle.time)} to {dateLabel(lastCandle.time)}</p>
        )}
      </section>

      <section className="rail-panel">
        <div className="rail-heading">
          <span>Trade distribution</span>
          <h2>Realized PnL</h2>
        </div>
        {trades.length === 0 ? (
          <p className="rail-note">No closed trades in this run.</p>
        ) : (
          <>
            <div className="rail-bars" aria-hidden="true">
              {bars.map((bar) => (
                <span className={bar.tone} key={bar.id} style={{ height: `${bar.height}px` }} />
              ))}
            </div>
            <div className="rail-stat-grid">
              <Stat label="Winners" value={distribution.wins.length.toLocaleString()} tone="positive" />
              <Stat label="Losers" value={distribution.losses.length.toLocaleString()} tone="negative" />
              <Stat label="Avg winner" value={signedMoney(distribution.avgWinner)} tone="positive" />
              <Stat label="Avg loser" value={signedMoney(distribution.avgLoser)} tone="negative" />
            </div>
          </>
        )}
      </section>

      <section className="rail-panel">
        <div className="rail-heading">
          <span>Drawdown</span>
          <h2>Equity pressure</h2>
        </div>
        <div className="rail-stat-grid">
          <Stat label="Max" value={`${dd.max.toFixed(2)}%`} tone="negative" />
          <Stat label="Current" value={`${dd.current.toFixed(2)}%`} tone={dd.current < 0 ? "negative" : "neutral"} />
          <Stat label="Underwater bars" value={dd.underwater.toLocaleString()} />
          <Stat label="Equity points" value={equity.length.toLocaleString()} />
        </div>
      </section>

      <section className="rail-panel">
        <div className="rail-heading">
          <span>Extremes</span>
          <h2>Best / worst trades</h2>
        </div>
        {distribution ? (
          <div className="extreme-list">
            <button type="button" onClick={() => onSelectTrade(distribution.best)}>
              <span>Best trade #{distribution.best.id}</span>
              <strong className="positive">{signedMoney(distribution.best.pnl)}</strong>
            </button>
            <button type="button" onClick={() => onSelectTrade(distribution.worst)}>
              <span>Worst trade #{distribution.worst.id}</span>
              <strong className="negative">{signedMoney(distribution.worst.pnl)}</strong>
            </button>
          </div>
        ) : (
          <p className="rail-note">No trade extremes available.</p>
        )}
      </section>
    </aside>
  );
}
