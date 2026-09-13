import { useEffect, useMemo, useRef, useState } from "react";
import {
  AreaSeries,
  BarSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  createChart,
  createSeriesMarkers,
} from "lightweight-charts";
import { chartColors } from "../../data/constants";
import { dateLabel, getFormattingConfig, money, percent, price, signedMoney, timeLabel } from "../../utils/formatters";
import { TIMEFRAMES, detectBaseInterval, resampleCandles } from "../../utils/resample";
import {
  calculateBollingerBands,
  calculateEMA,
  calculateRSI,
  calculateSMA,
  calculateVWAP,
  calculateVolumeMA,
} from "../../utils/indicators";
import { AVAILABLE_INDICATORS, IndicatorsModal } from "./IndicatorsModal";
import { GoToDateModal } from "./GoToDateModal";
import { ChartLegend } from "./ChartLegend";
import { RANGE_PRESETS, RangeBar } from "./RangeBar";

export function TradingCharts({
  data,
  isFullscreen = false,
  metrics,
  onSelectTrade,
  run,
  selectedTrade,
  theme,
}) {
  const priceRef = useRef(null);
  const equityRef = useRef(null);
  const drawdownRef = useRef(null);
  const rsiRef = useRef(null);
  const overlayRef = useRef(null);
  const chartsRef = useRef(null);

  const [tooltip, setTooltip] = useState(null);
  const [hoverData, setHoverData] = useState({ candle: null, vol: null, indicators: {} });
  const [drawing, setDrawing] = useState(null);
  const [tools, setTools] = useState({ crosshair: true, tradePath: true });
  const [timeframe, setTimeframe] = useState("15m");
  const [chartType, setChartType] = useState("candles");
  const [activeRange, setActiveRange] = useState("ALL");
  const [showIndicatorsModal, setShowIndicatorsModal] = useState(false);
  const [showGoToDateModal, setShowGoToDateModal] = useState(false);
  const [subcharts, setSubcharts] = useState({ equity: true, drawdown: true, volume: true });
  const [chartHeight, setChartHeight] = useState(() => {
    try {
      const saved = localStorage.getItem("stolgo_chart_height");
      return saved ? Math.max(280, Math.min(850, Number(saved))) : 460;
    } catch {
      return 460;
    }
  });
  const [isResizing, setIsResizing] = useState(false);

  const handleResizerMouseDown = (e) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = chartHeight;
    setIsResizing(true);

    const onMouseMove = (moveEvent) => {
      const deltaY = moveEvent.clientY - startY;
      const newHeight = Math.max(280, Math.min(850, startHeight + deltaY));
      setChartHeight(newHeight);
      if (chartsRef.current?.priceChart) {
        chartsRef.current.priceChart.applyOptions({ height: newHeight });
      }
    };

    const onMouseUp = () => {
      setIsResizing(false);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      try {
        localStorage.setItem("stolgo_chart_height", String(chartHeight));
      } catch {}
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  const handleResizerReset = () => {
    setChartHeight(460);
    if (chartsRef.current?.priceChart) {
      chartsRef.current.priceChart.applyOptions({ height: 460 });
    }
    try {
      localStorage.setItem("stolgo_chart_height", "460");
    } catch {}
  };

  const [activeIndicators, setActiveIndicators] = useState({
    volume: { id: "volume", hidden: false },
    ema20: { id: "ema20", hidden: false },
    vwap: { id: "vwap", hidden: false },
    volumeMa: { id: "volumeMa", hidden: false },
  });

  const baseInterval = useMemo(() => detectBaseInterval(data.candles), [data.candles]);
  const activeTf = timeframe;

  const { candles: activeCandles, volume: activeVolume } = useMemo(() => {
    return resampleCandles(data.candles, data.volume, activeTf, getFormattingConfig().timeZone);
  }, [data.candles, data.volume, activeTf]);

  // Compute indicators data
  const indicatorSeriesData = useMemo(() => {
    if (!activeCandles || activeCandles.length === 0) return {};
    const out = {};
    if (activeIndicators.ema20 && !activeIndicators.ema20.hidden) out.ema20 = calculateEMA(activeCandles, 20);
    if (activeIndicators.ema50 && !activeIndicators.ema50.hidden) out.ema50 = calculateEMA(activeCandles, 50);
    if (activeIndicators.ema200 && !activeIndicators.ema200.hidden) out.ema200 = calculateEMA(activeCandles, 200);
    if (activeIndicators.sma20 && !activeIndicators.sma20.hidden) out.sma20 = calculateSMA(activeCandles, 20);
    if (activeIndicators.sma50 && !activeIndicators.sma50.hidden) out.sma50 = calculateSMA(activeCandles, 50);
    if (activeIndicators.vwap && !activeIndicators.vwap.hidden) out.vwap = calculateVWAP(activeCandles, activeVolume, getFormattingConfig().timeZone);
    if (activeIndicators.bollinger && !activeIndicators.bollinger.hidden) out.bollinger = calculateBollingerBands(activeCandles, 20, 2);
    if (activeIndicators.rsi && !activeIndicators.rsi.hidden) out.rsi = calculateRSI(activeCandles, 14);
    if (activeIndicators.volumeMa && !activeIndicators.volumeMa.hidden) out.volumeMa = calculateVolumeMA(activeVolume, 20);
    return out;
  }, [activeCandles, activeVolume, activeIndicators]);

  useEffect(() => {
    if (!priceRef.current) return undefined;

    const chartTheme = theme === "dark"
      ? {
          panel: "#101820",
          text: "#98a5b2",
          grid: "rgba(226, 236, 244, 0.045)",
          border: "rgba(226, 236, 244, 0.07)",
        }
      : {
          panel: "#fbfcfd",
          text: chartColors.muted,
          grid: chartColors.grid,
          border: "rgba(23, 33, 43, 0.07)",
        };

    let syncing = false;

    const baseOptions = {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: chartTheme.panel },
        textColor: chartTheme.text,
        fontFamily: "IBM Plex Sans",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: chartTheme.grid },
        horzLines: { color: chartTheme.grid },
      },
      rightPriceScale: {
        borderColor: chartTheme.border,
        scaleMargins: { top: 0.12, bottom: subcharts.volume ? 0.22 : 0.12 },
        autoScale: true,
      },
      timeScale: {
        borderColor: chartTheme.border,
        timeVisible: !["1D", "1W"].includes(activeTf),
        secondsVisible: false,
        tickMarkFormatter: (time) => {
          if (["1D", "1W"].includes(activeTf)) {
            return new Date(time * 1000).toLocaleDateString("en-IN", { month: "short", day: "2-digit" });
          }
          return timeLabel(time);
        },
      },
      crosshair: {
        mode: tools.crosshair ? CrosshairMode.Normal : CrosshairMode.Magnet,
        vertLine: { color: "rgba(15, 142, 168, 0.72)", style: 2, width: 1 },
        horzLine: { color: "rgba(15, 142, 168, 0.42)", style: 2, width: 1 },
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    };

    const priceChart = createChart(priceRef.current, {
      ...baseOptions,
      localization: {
        priceFormatter: (value) => price(value),
        timeFormatter: (time) => `${dateLabel(time)} ${getFormattingConfig().timeZoneName}`,
      },
    });

    // Create Main Price Series based on chartType
    let mainSeries;
    if (chartType === "line") {
      mainSeries = priceChart.addSeries(LineSeries, {
        color: chartColors.cyan,
        lineWidth: 2,
      });
      mainSeries.setData(activeCandles.map((c) => ({ time: c.time, value: c.close })));
    } else if (chartType === "area") {
      mainSeries = priceChart.addSeries(AreaSeries, {
        lineColor: chartColors.cyan,
        topColor: "rgba(15, 142, 168, 0.28)",
        bottomColor: "rgba(15, 142, 168, 0.02)",
        lineWidth: 2,
      });
      mainSeries.setData(activeCandles.map((c) => ({ time: c.time, value: c.close })));
    } else if (chartType === "bars") {
      mainSeries = priceChart.addSeries(BarSeries, {
        upColor: chartColors.green,
        downColor: chartColors.red,
      });
      mainSeries.setData(activeCandles);
    } else {
      mainSeries = priceChart.addSeries(CandlestickSeries, {
        upColor: chartColors.green,
        downColor: chartColors.red,
        wickUpColor: chartColors.green,
        wickDownColor: chartColors.red,
        borderVisible: false,
        priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      });
      mainSeries.setData(activeCandles);
    }

    // Volume Series
    let volumeSeries = null;
    let volumeMaSeries = null;
    if (subcharts.volume) {
      volumeSeries = priceChart.addSeries(HistogramSeries, {
        priceScaleId: "volume-scale",
        priceFormat: { type: "volume" },
        base: 0,
      });
      volumeSeries.setData(activeVolume);
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
      });

      if (indicatorSeriesData.volumeMa && indicatorSeriesData.volumeMa.length) {
        volumeMaSeries = priceChart.addSeries(LineSeries, {
          priceScaleId: "volume-scale",
          color: "#29b6f6",
          lineWidth: 1,
        });
        volumeMaSeries.setData(indicatorSeriesData.volumeMa);
      }
    }

    // Add Overlay Indicator Series
    const addedIndicatorSeries = {};
    if (indicatorSeriesData.ema20) {
      const s = priceChart.addSeries(LineSeries, { color: "#2962ff", lineWidth: 1.5 });
      s.setData(indicatorSeriesData.ema20);
      addedIndicatorSeries.ema20 = s;
    }
    if (indicatorSeriesData.ema50) {
      const s = priceChart.addSeries(LineSeries, { color: "#ff6d00", lineWidth: 1.5 });
      s.setData(indicatorSeriesData.ema50);
      addedIndicatorSeries.ema50 = s;
    }
    if (indicatorSeriesData.ema200) {
      const s = priceChart.addSeries(LineSeries, { color: "#9c27b0", lineWidth: 2 });
      s.setData(indicatorSeriesData.ema200);
      addedIndicatorSeries.ema200 = s;
    }
    if (indicatorSeriesData.sma20) {
      const s = priceChart.addSeries(LineSeries, { color: "#26a69a", lineWidth: 1.5 });
      s.setData(indicatorSeriesData.sma20);
      addedIndicatorSeries.sma20 = s;
    }
    if (indicatorSeriesData.sma50) {
      const s = priceChart.addSeries(LineSeries, { color: "#e91e63", lineWidth: 1.5 });
      s.setData(indicatorSeriesData.sma50);
      addedIndicatorSeries.sma50 = s;
    }
    if (indicatorSeriesData.vwap) {
      const s = priceChart.addSeries(LineSeries, { color: "#ffd600", lineWidth: 1.5 });
      s.setData(indicatorSeriesData.vwap);
      addedIndicatorSeries.vwap = s;
    }
    if (indicatorSeriesData.bollinger) {
      const upperS = priceChart.addSeries(LineSeries, { color: "#00bcd4", lineWidth: 1, lineStyle: 2 });
      const midS = priceChart.addSeries(LineSeries, { color: "#00bcd4", lineWidth: 1 });
      const lowerS = priceChart.addSeries(LineSeries, { color: "#00bcd4", lineWidth: 1, lineStyle: 2 });
      upperS.setData(indicatorSeriesData.bollinger.upper);
      midS.setData(indicatorSeriesData.bollinger.middle);
      lowerS.setData(indicatorSeriesData.bollinger.lower);
      addedIndicatorSeries.bollinger = midS;
    }

    // Trade Markers (must be strictly sorted ascending by time for lightweight-charts)
    const tradeMarkers = data.trades
      .flatMap((trade) => [
        {
          time: trade.entryTime,
          position: trade.side === "Short" ? "aboveBar" : "belowBar",
          color: trade.side === "Short" ? chartColors.red : chartColors.green,
          shape: trade.side === "Short" ? "arrowDown" : "arrowUp",
          text: trade.side === "Short" ? "Sell" : "Buy",
        },
        {
          time: trade.exitTime,
          position: trade.side === "Short" ? "belowBar" : "aboveBar",
          color: trade.pnl >= 0 ? chartColors.green : chartColors.red,
          shape: trade.side === "Short" ? "arrowUp" : "circle",
          text: trade.side === "Short" ? "Cover" : "Exit",
        },
      ])
      .filter((m) => m.time && !Number.isNaN(m.time))
      .sort((a, b) => a.time - b.time);

    createSeriesMarkers(mainSeries, tradeMarkers);

    // Optional Subchart: RSI (14)
    let rsiChart = null;
    if (indicatorSeriesData.rsi && rsiRef.current) {
      rsiChart = createChart(rsiRef.current, {
        ...baseOptions,
        height: 110,
        rightPriceScale: {
          borderColor: chartTheme.border,
          scaleMargins: { top: 0.15, bottom: 0.15 },
        },
      });
      const rsiLine = rsiChart.addSeries(LineSeries, {
        color: "#ab47bc",
        lineWidth: 1.5,
      });
      rsiLine.setData(indicatorSeriesData.rsi);

      // Overbought / Oversold threshold lines
      const obLine = rsiChart.addSeries(LineSeries, { color: "rgba(200, 63, 58, 0.4)", lineWidth: 1, lineStyle: 2 });
      const osLine = rsiChart.addSeries(LineSeries, { color: "rgba(20, 154, 90, 0.4)", lineWidth: 1, lineStyle: 2 });
      obLine.setData(activeCandles.map((c) => ({ time: c.time, value: 70 })));
      osLine.setData(activeCandles.map((c) => ({ time: c.time, value: 30 })));
    }

    // Subchart: Equity
    let equityChart = null;
    if (subcharts.equity && equityRef.current) {
      equityChart = createChart(equityRef.current, {
        ...baseOptions,
        height: 110,
        rightPriceScale: {
          borderColor: chartTheme.border,
          scaleMargins: { top: 0.15, bottom: 0.12 },
        },
      });
      const equitySeries = equityChart.addSeries(AreaSeries, {
        lineColor: chartColors.green,
        topColor: chartColors.greenSoft,
        bottomColor: "rgba(20, 154, 90, 0.02)",
        lineWidth: 2,
        priceFormat: { type: "price", precision: 0, minMove: 1 },
      });
      equitySeries.setData(data.equity);
    }

    // Subchart: Drawdown
    let drawdownChart = null;
    if (subcharts.drawdown && drawdownRef.current) {
      drawdownChart = createChart(drawdownRef.current, {
        ...baseOptions,
        height: 94,
        rightPriceScale: {
          borderColor: chartTheme.border,
          scaleMargins: { top: 0.12, bottom: 0.18 },
        },
        localization: { priceFormatter: (value) => `${value.toFixed(0)}%` },
      });
      const drawdownSeries = drawdownChart.addSeries(AreaSeries, {
        lineColor: chartColors.red,
        topColor: "rgba(200, 63, 58, 0.02)",
        bottomColor: chartColors.redSoft,
        lineWidth: 2,
        priceFormat: { type: "price", precision: 1, minMove: 0.1 },
      });
      drawdownSeries.setData(data.drawdown);
    }

    const updateDrawing = () => {
      const trade = selectedTradeRef.current;
      if (!trade || !overlayRef.current || !activeCandles.length) return;
      const x1 = priceChart.timeScale().timeToCoordinate(trade.entryTime);
      const x2 = priceChart.timeScale().timeToCoordinate(trade.exitTime);

      const samplePrice = activeCandles[0]?.close || 1;
      const isOptionsOnSpot = Math.abs(trade.entryPrice - samplePrice) > samplePrice * 0.4;
      let y1;
      let y2;
      if (isOptionsOnSpot) {
        const entryBar = activeCandles.find((c) => Math.abs(c.time - trade.entryTime) <= 1800) || activeCandles[0];
        const exitBar = activeCandles.find((c) => Math.abs(c.time - trade.exitTime) <= 1800) || activeCandles.at(-1);
        y1 = mainSeries.priceToCoordinate(entryBar ? entryBar.high : samplePrice);
        y2 = mainSeries.priceToCoordinate(exitBar ? exitBar.low : samplePrice);
      } else {
        y1 = mainSeries.priceToCoordinate(trade.entryPrice);
        y2 = mainSeries.priceToCoordinate(trade.exitPrice);
      }
      if ([x1, x2, y1, y2].some((point) => point === null || point === undefined)) return;

      const left = Math.min(x1, x2);
      const top = Math.min(y1, y2);
      const width = Math.max(1, Math.abs(x2 - x1));
      const height = Math.max(1, Math.abs(y2 - y1));
      const length = Math.sqrt(width ** 2 + height ** 2);
      const angle = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;

      const entryVerb = trade.side === "Short" ? "Sell" : "Buy";
      const exitVerb = trade.side === "Short" ? "Cover" : "Exit";

      setDrawing({
        region: {
          left,
          top,
          width,
          height,
          borderColor: trade.pnl >= 0 ? chartColors.green : chartColors.red,
          background: trade.pnl >= 0 ? chartColors.greenSoft : chartColors.redSoft,
        },
        line: {
          left: x1,
          top: y1,
          width: length,
          transform: `rotate(${angle}deg)`,
          background: trade.pnl >= 0 ? chartColors.cyan : chartColors.red,
        },
        entry: { left: x1, top: y1, label: `${entryVerb} ${money(trade.entryPrice)}` },
        exit: { left: x2, top: y2, label: `${exitVerb} ${money(trade.exitPrice)} (${signedMoney(trade.pnl)})` },
      });
    };

    const selectedTradeRef = { current: selectedTrade };

    // TIME-BASED SYNCHRONIZATION (Fixes the Zoom-Out Clamping Bug!)
    const allCharts = [priceChart, rsiChart, equityChart, drawdownChart].filter(Boolean);
    const unsubs = [];

    allCharts.forEach((src) => {
      const handler = (range) => {
        if (!range || syncing) return;
        syncing = true;
        allCharts.forEach((target) => {
          if (target !== src) {
            try {
              target.timeScale().setVisibleRange(range);
            } catch {}
          }
        });
        syncing = false;
        requestAnimationFrame(updateDrawing);
      };
      src.timeScale().subscribeVisibleTimeRangeChange(handler);
      unsubs.push(() => {
        try {
          src.timeScale().unsubscribeVisibleTimeRangeChange(handler);
        } catch {}
      });
    });

    chartsRef.current = {
      priceChart,
      rsiChart,
      equityChart,
      drawdownChart,
      mainSeries,
      updateDrawing: () => updateDrawing(),
      selectedTradeRef,
    };

    priceChart.timeScale().fitContent();
    if (rsiChart) rsiChart.timeScale().fitContent();
    if (equityChart) equityChart.timeScale().fitContent();
    if (drawdownChart) drawdownChart.timeScale().fitContent();

    priceChart.subscribeClick((param) => {
      if (!param.time) return;
      const nearest = data.trades.reduce((best, trade) => {
        const distance = Math.min(Math.abs(trade.entryTime - param.time), Math.abs(trade.exitTime - param.time));
        return distance < best.distance ? { trade, distance } : best;
      }, { trade: selectedTrade, distance: Number.POSITIVE_INFINITY });
      if (nearest.distance < 1800 && nearest.trade) onSelectTrade(nearest.trade);
    });

    priceChart.subscribeCrosshairMove((param) => {
      if (!param.point || !param.time || !priceRef.current) {
        setTooltip(null);
        setHoverData({ candle: null, vol: null, indicators: {} });
        return;
      }
      const candle = activeCandles.find((item) => item.time === param.time);
      if (!candle) return;
      const hoverTrade = data.trades.find((trade) => param.time >= trade.entryTime && param.time <= trade.exitTime);
      const hoverVol = activeVolume.find((item) => item.time === param.time)?.value;

      // Extract hover values for active indicators
      const indVals = {};
      Object.keys(indicatorSeriesData).forEach((indKey) => {
        const seriesData = indicatorSeriesData[indKey];
        if (Array.isArray(seriesData)) {
          const pt = seriesData.find((p) => p.time === param.time);
          if (pt) indVals[indKey] = pt.value;
        } else if (seriesData && seriesData.middle) {
          const pt = seriesData.middle.find((p) => p.time === param.time);
          if (pt) indVals[indKey] = pt.value;
        }
      });

      setHoverData({ candle, vol: hoverVol, indicators: indVals });

      setTooltip({
        x: Math.min(param.point.x + 18, priceRef.current.clientWidth - 220),
        y: Math.max(param.point.y - 16, 16),
        candle,
        trade: hoverTrade,
      });
    });

    window.addEventListener("resize", updateDrawing);
    requestAnimationFrame(updateDrawing);

    return () => {
      unsubs.forEach((fn) => fn());
      window.removeEventListener("resize", updateDrawing);
      priceChart.remove();
      if (rsiChart) rsiChart.remove();
      if (equityChart) equityChart.remove();
      if (drawdownChart) drawdownChart.remove();
      chartsRef.current = null;
    };
  }, [
    activeCandles,
    activeVolume,
    chartType,
    data.drawdown,
    data.equity,
    data.trades,
    indicatorSeriesData,
    onSelectTrade,
    selectedTrade,
    subcharts,
    theme,
    tools.crosshair,
    activeTf,
  ]);

  useEffect(() => {
    if (!chartsRef.current) return;
    chartsRef.current.selectedTradeRef.current = selectedTrade;
    requestAnimationFrame(chartsRef.current.updateDrawing);
  }, [selectedTrade]);

  const lastCandle = activeCandles.at(-1);
  const priorCandle = activeCandles.at(-2);
  const finalEquity = data.equity.at(-1)?.value;
  const currentDrawdown = data.drawdown.at(-1)?.value;
  const maxDrawdown = data.drawdown.reduce((lowest, point) => Math.min(lowest, point.value), 0);

  // Jump To Date Handler
  const handleGoToDate = (dateStr, exactTs) => {
    if (!chartsRef.current || !chartsRef.current.priceChart) return;
    const targetTs = exactTs || Math.floor(new Date(`${dateStr}T09:15:00+05:30`).getTime() / 1000);
    const windowSecs = 86400 * 4;
    try {
      chartsRef.current.priceChart.timeScale().setVisibleRange({
        from: targetTs - windowSecs,
        to: targetTs + windowSecs,
      });
    } catch {
      chartsRef.current.priceChart.timeScale().fitContent();
    }
  };

  // Range Presets Handler
  const handleSelectRange = (rangeId) => {
    setActiveRange(rangeId);
    if (!chartsRef.current || !chartsRef.current.priceChart || !lastCandle) return;
    if (rangeId === "ALL") {
      chartsRef.current.priceChart.timeScale().fitContent();
      return;
    }
    const preset = RANGE_PRESETS.find((p) => p.id === rangeId);
    if (!preset || !preset.days) return;

    const endTs = lastCandle.time + 3600 * 4;
    const startTs = lastCandle.time - preset.days * 86400;
    try {
      chartsRef.current.priceChart.timeScale().setVisibleRange({ from: startTs, to: endTs });
    } catch {
      chartsRef.current.priceChart.timeScale().fitContent();
    }
  };

  const handleFitContent = () => {
    if (chartsRef.current && chartsRef.current.priceChart) {
      chartsRef.current.priceChart.timeScale().fitContent();
      setActiveRange("ALL");
    }
  };

  const toggleIndicator = (id) => {
    setActiveIndicators((prev) => {
      if (prev[id]) {
        const next = { ...prev };
        delete next[id];
        if (id === "volume") setSubcharts((s) => ({ ...s, volume: false }));
        return next;
      }
      if (id === "volume") setSubcharts((s) => ({ ...s, volume: true }));
      return { ...prev, [id]: { id, hidden: false } };
    });
  };

  const toggleIndicatorVisibility = (id) => {
    setActiveIndicators((prev) => {
      if (!prev[id]) return prev;
      const willHide = !prev[id].hidden;
      if (id === "volume") setSubcharts((s) => ({ ...s, volume: !willHide }));
      return { ...prev, [id]: { ...prev[id], hidden: willHide } };
    });
  };

  const removeIndicator = (id) => {
    setActiveIndicators((prev) => {
      const next = { ...prev };
      delete next[id];
      if (id === "volume") setSubcharts((s) => ({ ...s, volume: false }));
      return next;
    });
  };

  return (
    <section
      className={`chart-stack tv-workspace ${isFullscreen ? "is-fullscreen" : ""}`}
      aria-label="TradingView strategy chart workspace"
    >
          {/* TradingView Top Toolbar */}
          <div className="chart-toolbar tv-topbar">
            <div className="chart-info-bar">
              <span className="chart-title">{run?.market ?? "-"}</span>

              {/* Timeframe Selector */}
              <div className="timeframe-group" role="group" aria-label="Chart timeframes">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.id}
                type="button"
                className={`tf-btn ${activeTf === tf.id ? "active" : ""}`}
                onClick={() => setTimeframe(tf.id)}
                title={tf.seconds < baseInterval ? `Base resolution is ${run?.timeframe || '15m'}` : `Switch to ${tf.label}`}
              >
                {tf.label}
              </button>
            ))}
          </div>

          {/* Chart Type Selector */}
          <div className="tv-chart-types" role="group" aria-label="Chart types">
            {[
              ["candles", "🕯️", "Candlestick"],
              ["line", "📈", "Line"],
              ["area", "🏔️", "Area"],
              ["bars", "📊", "Bars (OHLC)"],
            ].map(([typeId, icon, label]) => (
              <button
                key={typeId}
                type="button"
                className={`tv-icon-btn ${chartType === typeId ? "active" : ""}`}
                onClick={() => setChartType(typeId)}
                title={label}
              >
                {icon}
              </button>
            ))}
          </div>

          {/* Subchart Quick Toggles: Volume, Equity, Drawdown */}
          <div className="subchart-toggles" role="group" aria-label="Subchart toggles">
            <button
              type="button"
              className={`tv-icon-btn ${subcharts.volume ? "active" : ""}`}
              onClick={() => {
                const nextVol = !subcharts.volume;
                setSubcharts((s) => ({ ...s, volume: nextVol }));
                setActiveIndicators((prev) => {
                  if (!nextVol) {
                    const next = { ...prev };
                    delete next.volume;
                    return next;
                  }
                  return { ...prev, volume: { id: "volume", hidden: false } };
                });
              }}
              title={subcharts.volume ? "Hide Volume Histogram" : "Show Volume Histogram"}
            >
              Vol
            </button>
            <button
              type="button"
              className={`tv-icon-btn ${subcharts.equity ? "active" : ""}`}
              onClick={() => setSubcharts((s) => ({ ...s, equity: !s.equity }))}
              title={subcharts.equity ? "Hide Equity Curve Subchart" : "Show Equity Curve Subchart"}
            >
              Equity
            </button>
            <button
              type="button"
              className={`tv-icon-btn ${subcharts.drawdown ? "active" : ""}`}
              onClick={() => setSubcharts((s) => ({ ...s, drawdown: !s.drawdown }))}
              title={subcharts.drawdown ? "Hide Drawdown Subchart" : "Show Drawdown Subchart"}
            >
              Drawdown
            </button>
          </div>

          {/* Indicators Button */}
          <button
            type="button"
            className="tv-fx-btn"
            onClick={() => setShowIndicatorsModal(true)}
            title="Add technical indicators"
          >
            <span className="fx-symbol">fx</span>
            <span>Indicators</span>
            {Object.keys(activeIndicators).length > 0 && (
              <span className="active-ind-badge">{Object.keys(activeIndicators).length}</span>
            )}
          </button>
        </div>

        <div className="tool-group" aria-label="Chart tools">
          <button
            type="button"
            className="ghost-button"
            onClick={() => setShowGoToDateModal(true)}
            title="Go to specific date or trade"
          >
            📅 Go to
          </button>

          {["tradePath", "crosshair"].map((tool) => (
            <button
              className={tools[tool] ? "active" : ""}
              key={tool}
              type="button"
              onClick={() => setTools((current) => ({ ...current, [tool]: !current[tool] }))}
            >
              {tool === "tradePath" ? "Trade path" : tool.charAt(0).toUpperCase() + tool.slice(1)}
            </button>
          ))}

          <button
            type="button"
            className="ghost-button"
            onClick={handleFitContent}
            title="Fit content to view (Reset zoom)"
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
              title="Open full screen chart in new tab"
            >
              ⛶ Fullscreen
            </button>
          )}
        </div>
      </div>

      {/* Main Chart Area */}
      <div
        className={`price-chart-wrap ${isFullscreen ? "is-fullscreen" : ""}`}
        style={isFullscreen ? undefined : { height: `${chartHeight}px` }}
        onDoubleClick={handleFitContent}
      >
        {/* TradingView Top-Left Legend */}
        <ChartLegend
          activeIndicators={activeIndicators}
          hoverCandle={hoverData.candle}
          hoverVol={hoverData.vol !== null && hoverData.vol !== undefined ? hoverData.vol : activeVolume.at(-1)?.value}
          indicatorValues={hoverData.indicators}
          lastCandle={lastCandle}
          onRemoveIndicator={removeIndicator}
          onToggleIndicatorVisibility={toggleIndicatorVisibility}
          priorCandle={priorCandle}
          run={run}
          timeframe={activeTf}
        />

        <div className="price-chart" ref={priceRef} />

        {/* Drawing Overlay */}
        <div className="drawing-layer" ref={overlayRef}>
          {drawing && tools.tradePath && (
            <>
              <div className="trade-region" style={drawing.region} />
              <div className="trade-line" style={drawing.line} />
              <div className="trade-point entry-point" style={drawing.entry} />
              <div className="trade-point exit-point" style={drawing.exit} />
              <div className="trade-label entry-label" style={drawing.entry}>{drawing.entry.label}</div>
              <div className="trade-label exit-label" style={drawing.exit}>{drawing.exit.label}</div>
            </>
          )}
        </div>

        {/* Hover Tooltip */}
        {tooltip && (
          <div className="chart-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
            <div className="tooltip-date">{dateLabel(tooltip.candle.time)}</div>
            <div><span>Open</span><b>{price(tooltip.candle.open)}</b></div>
            <div><span>High</span><b>{price(tooltip.candle.high)}</b></div>
            <div><span>Low</span><b>{price(tooltip.candle.low)}</b></div>
            <div><span>Close</span><b>{price(tooltip.candle.close)}</b></div>
            {tooltip.trade && (
              <div className="tooltip-trade">
                <strong>Trade #{tooltip.trade.id} ({tooltip.trade.side})</strong>
                <span className={tooltip.trade.pnlClass}>{money(tooltip.trade.pnl)} · {tooltip.trade.r}R</span>
                {tooltip.trade.commission > 0 && (
                  <small className="tooltip-cost">Cost: {money(tooltip.trade.commission)}</small>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* TradingView Bottom Range Presets Bar */}
      <RangeBar
        activeRange={activeRange}
        onFitContent={handleFitContent}
        onOpenGoToDate={() => setShowGoToDateModal(true)}
        onSelectRange={handleSelectRange}
      />

      {/* RSI (14) Sub-Pane */}
      {indicatorSeriesData.rsi && (
        <div className="subchart">
          <div className="panel-label">
            <span>RSI (14)</span>
            <span className="rsi-badge">Overbought 70 · Oversold 30</span>
            <button
              type="button"
              className="ind-action-btn delete"
              onClick={() => removeIndicator("rsi")}
              title="Close RSI pane"
            >
              ✕
            </button>
          </div>
          <div className="subchart-canvas" ref={rsiRef} />
        </div>
      )}

      {/* Equity Curve Subchart (Dismissible) */}
      {subcharts.equity && (
        <div className="subchart">
          <div className="panel-label">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span>Equity curve</span>
              {finalEquity !== undefined && <span className="subchart-meta">Final: {money(finalEquity)}</span>}
              <strong className="subchart-meta">Net {percent(metrics?.total_return ?? 0)}</strong>
            </div>
            <button
              type="button"
              className="ind-action-btn delete"
              onClick={() => setSubcharts((prev) => ({ ...prev, equity: false }))}
              title="Hide Equity curve subchart"
            >
              ✕
            </button>
          </div>
          <div className="subchart-canvas" ref={equityRef} />
        </div>
      )}

      {/* Drawdown Subchart (Dismissible) */}
      {subcharts.drawdown && (
        <div className="subchart compact">
          <div className="panel-label">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span>Drawdown</span>
              <span className="subchart-meta">Max: {maxDrawdown.toFixed(2)}%</span>
              <strong className="subchart-meta negative">Current {(currentDrawdown ?? 0).toFixed(2)}%</strong>
            </div>
            <button
              type="button"
              className="ind-action-btn delete"
              onClick={() => setSubcharts((prev) => ({ ...prev, drawdown: false }))}
              title="Hide Drawdown subchart"
            >
              ✕
            </button>
          </div>
          <div className="subchart-canvas" ref={drawdownRef} />
        </div>
      )}

      {/* Interactive Chart Height Resizer */}
      {!isFullscreen && (
        <div
          className={`chart-resizer ${isResizing ? "resizing" : ""}`}
          onMouseDown={handleResizerMouseDown}
          onDoubleClick={handleResizerReset}
          title="Drag up/down to adjust chart height · Double-click to reset"
        >
          <span className="resizer-grip" />
        </div>
      )}

      {/* Indicators Picker Modal */}
      {showIndicatorsModal && (
        <IndicatorsModal
          activeIndicators={activeIndicators}
          onClose={() => setShowIndicatorsModal(false)}
          onToggleIndicator={toggleIndicator}
        />
      )}

      {/* Go To Date Modal */}
      {showGoToDateModal && (
        <GoToDateModal
          candles={activeCandles}
          onClose={() => setShowGoToDateModal(false)}
          onGoToDate={handleGoToDate}
          onSelectTrade={onSelectTrade}
          selectedTrade={selectedTrade}
          trades={data.trades}
        />
      )}
    </section>
  );
}
