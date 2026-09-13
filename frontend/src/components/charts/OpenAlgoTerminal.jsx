import { useEffect, useMemo, useRef, useState } from "react";
import { createChart, darkTheme, lightTheme } from "openalgo-charts";
import "openalgo-charts/indicators";
import { BUILTIN_INDICATORS } from "openalgo-charts/indicators";
import { BUILTIN_DRAWING_TOOLS, DrawingController } from "openalgo-charts/draw";
import { VolumeProfile, computeVolumeProfileSessions } from "openalgo-charts/profile";
import { chartColors } from "../../data/constants";
import { dateLabel, getFormattingConfig, price, timeLabel } from "../../utils/formatters";
import { TIMEFRAMES, detectBaseInterval, resampleCandles } from "../../utils/resample";

// Quick-access drawing tool groups for the pro terminal rail
const QUICK_DRAWING_TOOLS = [
  { id: "cursor", name: "Cursor / Pan", icon: "✋", category: "Standard" },
  { id: "trend-line", name: "Trend Line", icon: "╱", category: "Lines" },
  { id: "ray", name: "Ray", icon: "↗", category: "Lines" },
  { id: "horizontal-line", name: "Horizontal Line", icon: "―", category: "Lines" },
  { id: "vertical-line", name: "Vertical Line", icon: "│", category: "Lines" },
  { id: "parallel-channel", name: "Channel", icon: "⫽", category: "Channels" },
  { id: "fib-retracement", name: "Fib Retracement", icon: "≡", category: "Fibonacci" },
  { id: "fib-extension", name: "Fib Extension", icon: "≢", category: "Fibonacci" },
  { id: "rectangle", name: "Rectangle", icon: "▭", category: "Shapes" },
  { id: "circle", name: "Circle", icon: "◯", category: "Shapes" },
  { id: "long-position", name: "Long Position", icon: "⇡", category: "Trading" },
  { id: "short-position", name: "Short Position", icon: "⇣", category: "Trading" },
  { id: "measure", name: "Measure / Ruler", icon: "📐", category: "Measurement" },
  { id: "brush", name: "Freehand Brush", icon: "✎", category: "Annotation" },
  { id: "text", name: "Text Note", icon: "T", category: "Annotation" },
  { id: "callout", name: "Callout", icon: "💬", category: "Annotation" },
];

export function OpenAlgoTerminal({
  data,
  isFullscreen = false,
  metrics,
  onSelectTrade,
  run,
  selectedTrade,
  theme = "dark",
}) {
  const containerRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const drawControllerRef = useRef(null);
  const mainSeriesRef = useRef(null);
  const volumeProfileRef = useRef(null);
  const indicatorInstancesRef = useRef({});

  // UI state
  const [activeTool, setActiveTool] = useState("cursor");
  const [magnetMode, setMagnetMode] = useState(false);
  const [timeframe, setTimeframe] = useState("15m");
  const [chartType, setChartType] = useState("candlestick");
  const [showVolume, setShowVolume] = useState(true);
  const [showVolumeProfile, setShowVolumeProfile] = useState(false);
  const [showIndicatorModal, setShowIndicatorModal] = useState(false);
  const [showToolsDrawer, setShowToolsDrawer] = useState(false);
  const [indicatorSearch, setIndicatorSearch] = useState("");
  const [indicatorCategory, setIndicatorCategory] = useState("All");
  const [activeIndicators, setActiveIndicators] = useState({
    ema: { id: "ema", name: "EMA (20)", settings: { period: 20 } },
    vwap: { id: "vwap", name: "VWAP", settings: {} },
  });
  const [hoverData, setHoverData] = useState(null);

  const baseInterval = useMemo(() => detectBaseInterval(data.candles), [data.candles]);
  const activeTf = timeframe;

  // Resample candles according to active timeframe
  const { candles: activeCandles, volume: activeVolume } = useMemo(() => {
    return resampleCandles(data.candles, data.volume, activeTf, getFormattingConfig().timeZone);
  }, [data.candles, data.volume, activeTf]);

  // Transform to OpenAlgo bar format { time, open, high, low, close, volume }
  const formattedBars = useMemo(() => {
    if (!activeCandles || activeCandles.length === 0) return [];
    const volMap = new Map();
    if (activeVolume && activeVolume.length) {
      activeVolume.forEach((v) => volMap.set(v.time, v.value));
    }
    return activeCandles.map((c) => ({
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
      volume: volMap.get(c.time) || Math.max(500, Math.round((c.high - c.low) * 10000)),
    }));
  }, [activeCandles, activeVolume]);

  // Initialize and mount OpenAlgo Chart
  useEffect(() => {
    if (!containerRef.current) return undefined;

    const isDark = theme === "dark";
    const basePalette = isDark ? darkTheme : lightTheme;

    // Custom OpenAlgo theme matched with Stolgo color tokens
    const chartPalette = {
      ...basePalette,
      background: isDark ? "#101820" : "#ffffff",
      grid: isDark ? "rgba(226, 236, 244, 0.045)" : "rgba(23, 33, 43, 0.06)",
      axisText: isDark ? "#98a5b2" : "#687582",
      axisLine: isDark ? "rgba(226, 236, 244, 0.08)" : "rgba(23, 33, 43, 0.08)",
      upColor: chartColors.green,
      downColor: chartColors.red,
      wickUpColor: chartColors.green,
      wickDownColor: chartColors.red,
      lineColor: chartColors.cyan,
      crosshair: "rgba(15, 142, 168, 0.6)",
    };

    // Instantiate OpenAlgo Chart
    const chart = createChart(containerRef.current, {
      theme: chartPalette,
      timezone: getFormattingConfig().timeZone || "Asia/Kolkata",
      priceFormatter: (p) => price(p),
      timeFormatter: (sec) => {
        if (["1D", "1W"].includes(activeTf)) {
          return new Date(sec * 1000).toLocaleDateString("en-IN", { month: "short", day: "2-digit" });
        }
        return timeLabel(sec);
      },
      timeNavigator: true,
      branding: false,
    });

    chartInstanceRef.current = chart;

    // Attach DrawingController (51 tools)
    const drawCtrl = new DrawingController(chart, {
      magnet: magnetMode ? "strong" : "off",
      stayInDrawingMode: false,
    });
    drawControllerRef.current = drawCtrl;

    // Add Primary Candlestick Series
    const primarySeries = chart.addSeries(chartType, {
      paneIndex: 0,
      priceScaleId: "right",
    });
    mainSeriesRef.current = primarySeries;
    primarySeries.setData(formattedBars);

    // Optional Volume Histogram Series in bottom overlay
    let volSeries = null;
    if (showVolume && formattedBars.length > 0) {
      volSeries = chart.addSeries("histogram", {
        paneIndex: 0,
        priceScaleId: "", // Overlay scale inside main pane
        style: {
          color: "rgba(15, 142, 168, 0.28)",
          base: 0,
        },
      });
      const volBars = formattedBars.map((b) => ({
        time: b.time,
        value: b.volume,
        color: b.close >= b.open ? "rgba(20, 154, 90, 0.28)" : "rgba(200, 63, 58, 0.24)",
      }));
      volSeries.setData(volBars);
      volSeries.priceScale().setOptions({
        marginTop: 0.82,
        marginBottom: 0,
      });
    }

    // Trade Signal Markers
    if (data.trades && data.trades.length > 0) {
      const markersLayer = primarySeries.createMarkers();
      const openAlgoMarkers = data.trades
        .flatMap((trade) => [
          {
            time: trade.entryTime,
            position: trade.side === "Short" ? "aboveBar" : "belowBar",
            shape: trade.side === "Short" ? "arrowDown" : "arrowUp",
            size: "medium",
            color: trade.side === "Short" ? chartColors.red : chartColors.green,
            text: trade.side === "Short" ? "Sell Entry" : "Buy Entry",
            id: `entry-${trade.id}`,
          },
          {
            time: trade.exitTime,
            position: trade.side === "Short" ? "belowBar" : "aboveBar",
            shape: trade.side === "Short" ? "arrowUp" : "circle",
            size: "medium",
            color: trade.pnl >= 0 ? chartColors.green : chartColors.red,
            text: `${trade.side === "Short" ? "Cover" : "Exit"} (${trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(0)})`,
            id: `exit-${trade.id}`,
          },
        ])
        .filter((m) => m.time && !Number.isNaN(m.time))
        .sort((a, b) => a.time - b.time);

      markersLayer.setMarkers(openAlgoMarkers);
    }

    // Optional Volume Profile
    if (showVolumeProfile && formattedBars.length > 1) {
      try {
        const vpData = computeVolumeProfileSessions(formattedBars, {
          rowTicks: 10,
          valueAreaPercent: 70,
        });
        const vp = new VolumeProfile(vpData, {
          displayMode: "total",
          side: "right",
          width: 120,
          opacity: 0.7,
        });
        chart.addPrimitive(vp, 0);
        volumeProfileRef.current = vp;
      } catch (err) {
        console.warn("OpenAlgo VolumeProfile notice:", err);
      }
    }

    // Mount Active Built-in Indicators
    const mountedIndicators = {};
    Object.keys(activeIndicators).forEach((indKey) => {
      const cfg = activeIndicators[indKey];
      try {
        const inst = chart.addIndicator(cfg.id, cfg.settings || {});
        mountedIndicators[indKey] = inst;
      } catch (err) {
        console.warn(`Failed to mount indicator ${cfg.id}:`, err);
      }
    });
    indicatorInstancesRef.current = mountedIndicators;

    // Crosshair listener for live HUD inspection
    chart.on("crosshair", (info) => {
      if (!info || !info.bar) {
        setHoverData(null);
        return;
      }
      setHoverData({
        time: info.time,
        open: info.bar.open,
        high: info.bar.high,
        low: info.bar.low,
        close: info.bar.close,
        volume: info.bar.volume,
      });
    });

    // Fit content
    chart.timeScale.fitContent();

    // Auto resize observer
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          chart.applySize(rect.width, rect.height);
        }
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      if (drawControllerRef.current) {
        try {
          drawControllerRef.current.destroy();
        } catch (_) {}
      }
      try {
        chart.destroy();
      } catch (_) {}
      chartInstanceRef.current = null;
      drawControllerRef.current = null;
      mainSeriesRef.current = null;
      volumeProfileRef.current = null;
    };
  }, [
    formattedBars,
    chartType,
    theme,
    showVolume,
    showVolumeProfile,
    activeIndicators,
    activeTf,
    data.trades,
  ]);

  // Tool change handler
  const handleSelectTool = (toolId) => {
    setActiveTool(toolId);
    if (!drawControllerRef.current) return;
    if (toolId === "cursor") {
      drawControllerRef.current.setTool(null);
    } else {
      drawControllerRef.current.setTool(toolId);
    }
  };

  // Toggle magnet mode
  const handleToggleMagnet = () => {
    const next = !magnetMode;
    setMagnetMode(next);
    if (drawControllerRef.current) {
      drawControllerRef.current.setOptions({ magnet: next ? "strong" : "off" });
    }
  };

  // Clear drawings
  const handleClearDrawings = () => {
    if (drawControllerRef.current) {
      drawControllerRef.current.clear();
    }
  };

  // Undo drawing
  const handleUndo = () => {
    if (drawControllerRef.current) {
      drawControllerRef.current.undo();
    }
  };

  // Redo drawing
  const handleRedo = () => {
    if (drawControllerRef.current) {
      drawControllerRef.current.redo();
    }
  };

  // Fit content
  const handleFit = () => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.timeScale.fitContent();
    }
  };

  // Toggle indicator
  const handleToggleIndicator = (indId, name) => {
    setActiveIndicators((prev) => {
      const next = { ...prev };
      if (next[indId]) {
        delete next[indId];
      } else {
        next[indId] = { id: indId, name: name || indId.toUpperCase(), settings: {} };
      }
      return next;
    });
  };

  // Filter indicators list for modal
  const filteredIndicators = useMemo(() => {
    return BUILTIN_INDICATORS.filter((ind) => {
      const matchesSearch =
        ind.name.toLowerCase().includes(indicatorSearch.toLowerCase()) ||
        ind.id.toLowerCase().includes(indicatorSearch.toLowerCase());
      const matchesCategory =
        indicatorCategory === "All" || ind.category === indicatorCategory;
      return matchesSearch && matchesCategory;
    });
  }, [indicatorSearch, indicatorCategory]);

  const lastBar = formattedBars.at(-1);
  const priorBar = formattedBars.at(-2);
  const hudBar = hoverData || lastBar;
  const change = hudBar && priorBar ? hudBar.close - priorBar.close : 0;
  const changePct = hudBar && priorBar && priorBar.close ? (change / priorBar.close) * 100 : 0;

  return (
    <section className={`chart-stack tv-workspace pro-terminal-workspace ${isFullscreen ? "is-fullscreen" : ""}`}>
      {/* Top Pro Terminal Bar */}
      <div className="chart-toolbar tv-topbar pro-topbar">
        <div className="chart-info-bar">
          <div className="pro-badge" title="OpenAlgo Canvas Charting Engine">
            <span className="pro-badge-dot" />
            <b>PRO TERMINAL</b>
          </div>

          <span className="chart-title">{run?.market ?? "NIFTY"}</span>

          {/* Timeframes */}
          <div className="timeframe-group" role="group" aria-label="Timeframes">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.id}
                type="button"
                className={`tf-btn ${activeTf === tf.id ? "active" : ""}`}
                onClick={() => setTimeframe(tf.id)}
                title={tf.seconds < baseInterval ? `Base is ${run?.timeframe || "15m"}` : `Switch to ${tf.label}`}
              >
                {tf.label}
              </button>
            ))}
          </div>

          {/* Chart Type */}
          <div className="tv-chart-types" role="group" aria-label="Chart Types">
            {[
              ["candlestick", "🕯️", "Candles"],
              ["hollow-candle", "🪔", "Hollow Candles"],
              ["bar", "📊", "OHLC Bars"],
              ["line", "📈", "Line"],
              ["area", "🏔️", "Area"],
            ].map(([tId, icon, label]) => (
              <button
                key={tId}
                type="button"
                className={`tv-icon-btn ${chartType === tId ? "active" : ""}`}
                onClick={() => setChartType(tId)}
                title={label}
              >
                {icon}
              </button>
            ))}
          </div>

          {/* Volume Toggle */}
          <button
            type="button"
            className={`tv-icon-btn ${showVolume ? "active" : ""}`}
            onClick={() => setShowVolume((v) => !v)}
            title={showVolume ? "Hide Volume Histogram" : "Show Volume Histogram"}
          >
            Vol
          </button>

          {/* Volume Profile Toggle */}
          <button
            type="button"
            className={`tv-icon-btn ${showVolumeProfile ? "active" : ""}`}
            onClick={() => setShowVolumeProfile((v) => !v)}
            title={showVolumeProfile ? "Hide Volume Profile" : "Show Volume Profile (TPO/VAH/VAL)"}
          >
            VP
          </button>

          {/* Indicators Modal Trigger */}
          <button
            type="button"
            className="tv-fx-btn"
            onClick={() => setShowIndicatorModal(true)}
            title="Open 102 Technical Indicators catalog"
          >
            <span className="fx-symbol">fx</span>
            <span>Indicators</span>
            {Object.keys(activeIndicators).length > 0 && (
              <span className="active-ind-badge">{Object.keys(activeIndicators).length}</span>
            )}
          </button>
        </div>

        <div className="tool-group">
          <button
            type="button"
            className={`ghost-button ${magnetMode ? "active" : ""}`}
            onClick={handleToggleMagnet}
            title={magnetMode ? "Magnet snap ON (snaps to O/H/L/C)" : "Magnet snap OFF"}
          >
            🧲 Magnet
          </button>

          <button
            type="button"
            className="ghost-button"
            onClick={handleUndo}
            title="Undo last drawing"
          >
            ↶ Undo
          </button>

          <button
            type="button"
            className="ghost-button"
            onClick={handleRedo}
            title="Redo drawing"
          >
            ↷ Redo
          </button>

          <button
            type="button"
            className="ghost-button"
            onClick={handleClearDrawings}
            title="Clear all drawings"
          >
            🗑 Clear
          </button>

          <button
            type="button"
            className="ghost-button"
            onClick={handleFit}
            title="Fit content to view"
          >
            ⤢ Fit
          </button>

          {!isFullscreen && (
            <button
              type="button"
              className="ghost-button tv-fullscreen-btn"
              onClick={() => {
                const runId = run?.id || "";
                const url = runId ? `/?view=chart&run=${encodeURIComponent(runId)}` : `/?view=chart`;
                window.open(url, "_blank");
              }}
              title="Open full screen terminal in new tab"
            >
              ⛶ Fullscreen
            </button>
          )}
        </div>
      </div>

      {/* Main Terminal Workspace Layout (Drawing Rail + Canvas) */}
      <div className="pro-terminal-stage">
        {/* Left Drawing Tools Rail */}
        <aside className="pro-drawing-rail" aria-label="Drawing Tools">
          {QUICK_DRAWING_TOOLS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`rail-tool-btn ${activeTool === t.id ? "active" : ""}`}
              onClick={() => handleSelectTool(t.id)}
              title={`${t.name} (${t.category})`}
            >
              <span className="rail-icon">{t.icon}</span>
            </button>
          ))}
          <div className="rail-divider" />
          <button
            type="button"
            className="rail-tool-btn all-tools-btn"
            onClick={() => setShowToolsDrawer((d) => !d)}
            title="More Drawing Tools (51 built-ins)"
          >
            ⋯
          </button>
        </aside>

        {/* Chart Canvas Area */}
        <div className="pro-chart-canvas-wrap">
          {/* Real-time OHLC Legend Overlay */}
          <div className="pro-hud-legend">
            <span className="hud-symbol">{run?.market || "NIFTY"}</span>
            <span className="hud-tf">{activeTf}</span>
            {hudBar && (
              <>
                <span className="hud-item">O <b>{hudBar.open?.toFixed(2)}</b></span>
                <span className="hud-item">H <b>{hudBar.high?.toFixed(2)}</b></span>
                <span className="hud-item">L <b>{hudBar.low?.toFixed(2)}</b></span>
                <span className="hud-item">C <b>{hudBar.close?.toFixed(2)}</b></span>
                <span className={`hud-item ${change >= 0 ? "positive" : "negative"}`}>
                  {change >= 0 ? "+" : ""}{change.toFixed(2)} ({changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%)
                </span>
                {hudBar.volume && <span className="hud-item">Vol <b>{hudBar.volume.toLocaleString("en-IN")}</b></span>}
              </>
            )}
            <div className="hud-indicators-list">
              {Object.keys(activeIndicators).map((k) => (
                <span key={k} className="hud-ind-chip">
                  {activeIndicators[k].name}
                  <button
                    type="button"
                    className="ind-del-btn"
                    onClick={() => handleToggleIndicator(k)}
                    title={`Remove ${activeIndicators[k].name}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Primary Canvas Container */}
          <div ref={containerRef} className="pro-canvas-container" />
        </div>
      </div>

      {/* 51 Drawing Tools Modal Drawer */}
      {showToolsDrawer && (
        <div className="tv-modal-overlay" onClick={() => setShowToolsDrawer(false)}>
          <div className="tv-modal-card tools-drawer-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="tv-modal-header">
              <h3>51 Drawing Tools (OpenAlgo)</h3>
              <button type="button" className="close-btn" onClick={() => setShowToolsDrawer(false)}>✕</button>
            </div>
            <div className="tools-grid">
              {BUILTIN_DRAWING_TOOLS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`drawer-tool-card ${activeTool === t.id ? "active" : ""}`}
                  onClick={() => {
                    handleSelectTool(t.id);
                    setShowToolsDrawer(false);
                  }}
                >
                  <b>{t.name}</b>
                  <small>{t.id}</small>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 102 Technical Indicators Dialog */}
      {showIndicatorModal && (
        <div className="tv-modal-overlay" onClick={() => setShowIndicatorModal(false)}>
          <div className="tv-modal-card indicators-dialog pro-indicators-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="tv-modal-header">
              <div className="modal-title-wrap">
                <span className="fx-badge">fx</span>
                <h3>OpenAlgo Indicators (102 Built-ins)</h3>
              </div>
              <button type="button" className="close-btn" onClick={() => setShowIndicatorModal(false)}>✕</button>
            </div>

            <div className="pro-ind-tabs">
              {["All", "Trend", "Momentum", "Volatility", "Volume"].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`ind-tab-btn ${indicatorCategory === cat ? "active" : ""}`}
                  onClick={() => setIndicatorCategory(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="tv-search-wrap">
              <input
                autoFocus
                type="text"
                placeholder="Search indicators (e.g. Supertrend, Bollinger, RSI, VWAP, Ichimoku, HalfTrend)..."
                value={indicatorSearch}
                onChange={(e) => setIndicatorSearch(e.target.value)}
              />
            </div>

            <div className="indicators-list">
              {filteredIndicators.map((ind) => {
                const isActive = !!activeIndicators[ind.id];
                return (
                  <div
                    key={ind.id}
                    className={`indicator-row ${isActive ? "active" : ""}`}
                    onClick={() => handleToggleIndicator(ind.id, ind.name)}
                  >
                    <div className="ind-info">
                      <div className="ind-name-line">
                        <span className="ind-color-dot" style={{ background: isActive ? "#20b86c" : "#687582" }} />
                        <b>{ind.name}</b>
                        <span className="ind-cat">{ind.category || "General"}</span>
                      </div>
                      <small>Plots: {ind.plots?.length || 1} · ID: {ind.id}</small>
                    </div>
                    <button
                      type="button"
                      className={`ind-add-btn ${isActive ? "active" : ""}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleIndicator(ind.id, ind.name);
                      }}
                    >
                      {isActive ? "Active ✓" : "+ Add"}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
