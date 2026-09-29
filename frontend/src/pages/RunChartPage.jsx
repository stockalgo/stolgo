import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import { getRun, getTrades, getCandles } from "../api/endpoints.js";
import { CandleChart } from "../components/chart/CandleChart.jsx";
import { IndicatorsMenu } from "../components/chart/IndicatorsMenu.jsx";
import { GoToDateDialog } from "../components/chart/GoToDateDialog.jsx";
import { inr, rmult, sessionShort } from "../lib/format.js";

export function RunChartPage() {
  const { runId } = useParams();
  const navigate = useNavigate();

  const [tf, setTf] = useState("1D");
  const [range, setRange] = useState("1Y");
  const [activeIndicators, setActiveIndicators] = useState({});
  const [isGoToDateOpen, setIsGoToDateOpen] = useState(false);
  const [selectedTradeId, setSelectedTradeId] = useState(null);
  const [visibleRange, setVisibleRange] = useState(null);

  // Esc key goes back to run
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && !isGoToDateOpen) {
        navigate(`/runs/${encodeURIComponent(runId)}`);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate, runId, isGoToDateOpen]);

  // Fetch run metadata
  const fetchRun = useCallback(
    () => (runId ? getRun(runId) : Promise.resolve(null)),
    [runId]
  );
  const { data: run } = useApi(fetchRun);

  // Fetch trades
  const fetchTrades = useCallback(
    () => (runId ? getTrades(runId) : Promise.resolve([])),
    [runId]
  );
  const { data: rawTrades } = useApi(fetchTrades);
  const trades = useMemo(
    () => (Array.isArray(rawTrades) ? rawTrades : rawTrades?.rows || []),
    [rawTrades]
  );

  // Fetch candles (wait for run metadata to check run.has.ohlcv)
  const fetchCandles = useCallback(() => {
    if (!runId || !run) return Promise.resolve(null);
    if (run.has && !run.has.ohlcv) {
      return Promise.resolve({ rows: [], detail: "no_ohlcv" });
    }
    return getCandles(runId, tf);
  }, [runId, run, tf]);

  const { data: candleData } = useApi(fetchCandles);
  const allCandles = useMemo(() => candleData?.rows || [], [candleData]);

  // Filter candles by range [1M 3M 1Y ALL]
  const candles = useMemo(() => {
    if (!allCandles.length || range === "ALL") return allCandles;
    const lastTime = allCandles[allCandles.length - 1].time;
    let days = 365;
    if (range === "1M") days = 30;
    else if (range === "3M") days = 90;
    else if (range === "1Y") days = 365;

    const cutoff = lastTime - days * 86400;
    return allCandles.filter((c) => c.time >= cutoff);
  }, [allCandles, range]);

  // Visible trades in current time range
  const visibleTrades = useMemo(() => {
    if (!visibleRange || !visibleRange.from || !visibleRange.to) {
      return trades;
    }
    return trades.filter((t) => {
      let time = t.entry_ts;
      if (typeof time === "string") {
        time = Math.floor(new Date(time).getTime() / 1000);
      } else if (!time && t.session_date) {
        time = Math.floor(new Date(t.session_date).getTime() / 1000);
      }
      if (!time) return true;
      return time >= visibleRange.from && time <= visibleRange.to;
    });
  }, [trades, visibleRange]);

  const handleGoToDate = (targetDateStr) => {
    // Jump chart range or select closest trade
    const matchTrade = trades.find((t) => t.session_date === targetDateStr);
    if (matchTrade) {
      setSelectedTradeId(matchTrade.trade_id);
    }
  };

  const market =
    run?.has?.ohlcv_market ||
    run?.instrument?.markets?.[0] ||
    (run?.markets && run.markets[0]) ||
    "—";

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        background: "var(--bg-app)",
      }}
    >
      {/* Top Bar */}
      <header className="topbar">
        <button
          type="button"
          className="btn btn--sm"
          onClick={() => navigate(`/runs/${encodeURIComponent(runId)}`)}
        >
          &larr; Back to run
        </button>

        <span className="mono" style={{ fontSize: "13px" }}>
          {market} &middot; {runId}
        </span>

        {/* Timeframe Seg [15m | 1H | 1D] */}
        <div className="seg seg--mono">
          {["15m", "1H", "1D"].map((t) => (
            <button
              key={t}
              type="button"
              className={`seg__item ${tf === t ? "seg__item--active" : ""}`}
              aria-selected={tf === t}
              onClick={() => setTf(t)}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Indicators Menu */}
        <IndicatorsMenu
          activeIndicators={activeIndicators}
          onChangeIndicators={setActiveIndicators}
        />

        {/* Go to Date */}
        <button
          type="button"
          className="btn btn--sm"
          onClick={() => setIsGoToDateOpen(true)}
        >
          Go to date
        </button>

        <div className="crumbs" style={{ flex: 1 }} />

        {/* Range Seg [1M | 3M | 1Y | ALL] */}
        <div className="seg seg--mono">
          {["1M", "3M", "1Y", "ALL"].map((r) => (
            <button
              key={r}
              type="button"
              className={`seg__item ${range === r ? "seg__item--active" : ""}`}
              aria-selected={range === r}
              onClick={() => setRange(r)}
            >
              {r}
            </button>
          ))}
        </div>
      </header>

      {/* Main Grid: CandleChart (left) + Trades in view (right, 320px) */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) 320px",
          gap: 0,
        }}
      >
        <div
          style={{
            padding: "12px 16px",
            display: "flex",
            flexDirection: "column",
            height: "100%",
            overflow: "hidden",
          }}
        >
          {candleData?.detail === "no_ohlcv" || run?.has?.ohlcv === false ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                gap: 16,
              }}
            >
              <div className="muted" style={{ fontSize: 14 }}>
                No price data exported for this run
              </div>
              <button
                type="button"
                className="btn btn--sm"
                onClick={() => navigate(`/runs/${encodeURIComponent(runId)}`)}
              >
                Back to run overview
              </button>
            </div>
          ) : (
            <CandleChart
              candles={candles}
              trades={trades}
              market={run?.has?.ohlcv_market || run?.instrument?.markets?.[0]}
              selectedTradeId={selectedTradeId}
              onSelectTrade={setSelectedTradeId}
              activeIndicators={activeIndicators}
              onVisibleRangeChange={setVisibleRange}
              height="100%"
            />
          )}
        </div>

        {/* Right Sidebar: Trades in view */}
        <aside
          style={{
            borderLeft: "1px solid var(--line)",
            background: "var(--bg-panel)",
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            overflow: "hidden",
          }}
        >
          <div
            style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)" }}
            className="eyebrow"
          >
            Trades in view &middot; {visibleTrades.length}
          </div>

          <div style={{ overflow: "auto", flex: 1 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th className="num">Net</th>
                  <th className="num">R</th>
                </tr>
              </thead>
              <tbody>
                {visibleTrades.map((t) => {
                  const isSelected = t.trade_id === selectedTradeId;
                  const isWin = (t.net_pnl ?? 0) >= 0;

                  return (
                    <tr
                      key={t.trade_id}
                      aria-selected={isSelected}
                      style={{ cursor: "pointer" }}
                      onClick={() => setSelectedTradeId(t.trade_id)}
                    >
                      <td className="mono">{sessionShort(t.session_date)}</td>
                      <td className={`num ${isWin ? "pos" : "neg"}`}>
                        {inr(t.net_pnl, { signed: true })}
                      </td>
                      <td className="num">{rmult(t.r_multiple)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </aside>
      </div>

      <GoToDateDialog
        isOpen={isGoToDateOpen}
        onClose={() => setIsGoToDateOpen(false)}
        onSelectDate={handleGoToDate}
      />
    </div>
  );
}
