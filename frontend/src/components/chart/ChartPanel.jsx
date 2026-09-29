import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { useApi } from "../../hooks/useApi.js";
import { getCandles, getDaily } from "../../api/endpoints.js";
import { CandleChart } from "./CandleChart.jsx";
import { PnlStepChart } from "./PnlStepChart.jsx";
import { EquityChart } from "./EquityChart.jsx";
import { DrawdownChart } from "./DrawdownChart.jsx";
import { IndicatorsMenu } from "./IndicatorsMenu.jsx";
import { sessionShort } from "../../lib/format.js";
import { Tooltip } from "../ui/Tooltip.jsx";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function ChartPanel({ run, trades = [], onSelectTrade = null, selectedTradeId = null }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const hasOhlcv = Boolean(run?.has?.ohlcv);
  const viewParam = searchParams.get("view");

  // If !hasOhlcv, default is equity. Otherwise default is price
  const activeView = !hasOhlcv ? "equity" : viewParam === "equity" ? "equity" : "price";

  const handleViewChange = (v) => {
    if (v === "price" && !hasOhlcv) return;
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (v === "price") {
        next.delete("view");
      } else {
        next.set("view", "equity");
      }
      return next;
    });
  };

  // Price view state
  const [tf, setTf] = useState("1D");
  const [activeIndicators, setActiveIndicators] = useState({});
  const [hoveredBar, setHoveredBar] = useState(null);
  const [visibleRange, setVisibleRange] = useState(null);

  // Equity view state
  const [range, setRange] = useState("ALL");

  // Fetch candles when in price view
  const fetchCandles = useCallback(() => {
    if (!run?.id || !hasOhlcv) return Promise.resolve({ rows: [] });
    return getCandles(run.id, tf);
  }, [run?.id, hasOhlcv, tf]);

  const { data: candleData } = useApi(fetchCandles);
  const candles = useMemo(() => candleData?.rows || [], [candleData]);

  // Fetch daily series for equity view
  const fetchDaily = useCallback(() => {
    if (!run?.id) return Promise.resolve({ rows: [] });
    return getDaily(run.id);
  }, [run?.id]);

  const { data: dailyData } = useApi(fetchDaily);
  const daily = useMemo(() => dailyData?.rows || [], [dailyData]);

  const toggleIndicator = (key) => {
    setActiveIndicators((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Symbol label
  const symbol = run?.instrument?.markets?.[0] || run?.markets?.[0] || "NIFTY";

  // OHLC readout
  const ohlcReadout = useMemo(() => {
    if (!hoveredBar) return null;
    let dateStr = "";
    if (hoveredBar.time) {
      const d = new Date(hoveredBar.time * 1000);
      const day = d.getDate().toString().padStart(2, "0");
      const mon = MONTH_NAMES[d.getMonth()];
      dateStr = `${day} ${mon}`;
    }

    const fmt = (v) => (v != null ? Math.round(v).toLocaleString() : "—");
    const isUp = (hoveredBar.close ?? 0) >= (hoveredBar.open ?? 0);
    const closeColor = isUp ? "var(--pos, #3ddc97)" : "var(--neg, #e5484d)";

    return (
      <span className="mono" style={{ fontSize: "12px", color: "var(--text-3)" }}>
        {dateStr} · O <b style={{ color: "var(--text-1)", fontWeight: 500 }}>{fmt(hoveredBar.open)}</b>{" "}
        H <b style={{ color: "var(--text-1)", fontWeight: 500 }}>{fmt(hoveredBar.high)}</b>{" "}
        L <b style={{ color: "var(--text-1)", fontWeight: 500 }}>{fmt(hoveredBar.low)}</b>{" "}
        C <b style={{ color: closeColor, fontWeight: 500 }}>{fmt(hoveredBar.close)}</b>
      </span>
    );
  }, [hoveredBar]);

  return (
    <section className="panel" style={{ padding: "12px 16px 10px" }}>
      {/* Panel Head */}
      <div className="panel__head" style={{ marginBottom: "8px", alignItems: "center" }}>
        {/* Main Segment Switch: Price vs Equity */}
        <div className="seg">
          <Tooltip content={!hasOhlcv ? "No price data exported for this run" : null}>
            <button
              className={`seg__item ${activeView === "price" ? "seg__item--active" : ""}`}
              aria-selected={activeView === "price"}
              disabled={!hasOhlcv}
              onClick={() => handleViewChange("price")}
            >
              Price · candles
            </button>
          </Tooltip>
          <button
            className={`seg__item ${activeView === "equity" ? "seg__item--active" : ""}`}
            aria-selected={activeView === "equity"}
            onClick={() => handleViewChange("equity")}
          >
            Equity · drawdown
          </button>
        </div>

        {activeView === "price" ? (
          <>
            <span
              style={{
                width: "1px",
                height: "18px",
                background: "var(--line-strong)",
                margin: "0 6px",
              }}
            />
            <span className="mono" style={{ fontSize: "12px", color: "var(--text-2)" }}>
              {symbol}
            </span>

            {/* Timeframe Seg */}
            <div className="seg seg--mono" style={{ marginLeft: "4px" }}>
              {["15m", "1H", "1D"].map((t) => (
                <button
                  key={t}
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
              onToggleIndicator={toggleIndicator}
              hasVolume={candles.some((c) => (c.volume || 0) > 0)}
            />

            <div style={{ flex: 1 }} />

            {/* OHLC readout */}
            {ohlcReadout}

            {/* Full-screen icon */}
            <Link
              to={`/runs/${run?.id}/chart`}
              className="btn btn--sm icon-btn"
              aria-label="Full screen"
              title="Full screen chart"
              style={{ marginLeft: "6px" }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <polyline points="15 3 21 3 21 9" />
                <polyline points="9 21 3 21 3 15" />
                <line x1="21" y1="3" x2="14" y2="10" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
            </Link>
          </>
        ) : (
          <>
            <div style={{ flex: 1 }} />
            {/* Top 5 trades legend */}
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "12px",
                color: "var(--text-3)",
              }}
            >
              <span
                style={{
                  width: "9px",
                  height: "9px",
                  borderRadius: "50%",
                  border: "2px solid var(--accent, #f5a524)",
                }}
              />
              Top 5 trades
            </span>

            {/* Range Seg [1Y | ALL] */}
            <div className="seg seg--mono" style={{ marginLeft: "8px" }}>
              {["1Y", "ALL"].map((r) => (
                <button
                  key={r}
                  className={`seg__item ${range === r ? "seg__item--active" : ""}`}
                  aria-selected={range === r}
                  onClick={() => setRange(r)}
                >
                  {r}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Chart Body */}
      {activeView === "price" ? (
        <div>
          <CandleChart
            candles={candles}
            trades={trades}
            market={run?.has?.ohlcv_market || run?.instrument?.markets?.[0]}
            selectedTradeId={selectedTradeId}
            onSelectTrade={onSelectTrade}
            activeIndicators={activeIndicators}
            onHoverBar={setHoveredBar}
            onVisibleRangeChange={setVisibleRange}
          />
          <PnlStepChart trades={trades} visibleRange={visibleRange} />
        </div>
      ) : (
        <div>
          <EquityChart
            daily={daily}
            capital={run?.capital ?? run?.config?.capital ?? 0}
            trades={trades}
            range={range}
          />
          <DrawdownChart daily={daily} run={run} range={range} />
        </div>
      )}
    </section>
  );
}
