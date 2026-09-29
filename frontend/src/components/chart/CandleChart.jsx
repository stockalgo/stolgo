import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  ColorType,
  CrosshairMode,
  createSeriesMarkers,
} from "lightweight-charts";
import { calculateSMA, calculateEMA, calculateBollingerBands } from "../../lib/indicators.js";
import { COLORS } from "../../lib/colors.js";

export function CandleChart({
  candles = [],
  trades = [],
  market = null,
  selectedTradeId = null,
  onSelectTrade = null,
  activeIndicators = {},
  onHoverBar = null,
  onVisibleRangeChange = null,
  onTimeScaleChange = null,
  height = 262,
}) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const markerPrimitiveRef = useRef(null);
  const indicatorSeriesRef = useRef([]);

  const isTest = typeof process !== "undefined" && process.env?.NODE_ENV === "test";
  const [canvasSupported, setCanvasSupported] = useState(true);

  const onTimeScaleChangeRef = useRef(onTimeScaleChange);
  onTimeScaleChangeRef.current = onTimeScaleChange;

  const emitTimeScaleChange = useCallback(() => {
    if (!chartRef.current || !onTimeScaleChangeRef.current) return;
    try {
      const ts = chartRef.current.timeScale();
      const fn = (time) => {
        try {
          return ts.timeToCoordinate(time);
        } catch {
          return null;
        }
      };
      const w = ts.width ? ts.width() : containerRef.current?.clientWidth || 880;
      onTimeScaleChangeRef.current(fn, w);
    } catch {
      // ignore
    }
  }, []);

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current || isTest) return;

    try {
      const chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth || 900,
        height: typeof height === "number" ? height : containerRef.current.clientHeight || 262,
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: COLORS.marketOther,
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: 10,
        },
        grid: {
          vertLines: { color: "rgba(255, 255, 255, 0.04)" },
          horzLines: { color: "rgba(255, 255, 255, 0.04)" },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
        },
        rightPriceScale: {
          borderColor: "rgba(255, 255, 255, 0.08)",
          scaleMargins: {
            top: 0.1,
            bottom: 0.15,
          },
        },
        timeScale: {
          borderColor: "rgba(255, 255, 255, 0.08)",
          timeVisible: true,
          secondsVisible: false,
        },
      });

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: COLORS.pos,
        downColor: COLORS.neg,
        borderUpColor: COLORS.pos,
        borderDownColor: COLORS.neg,
        wickUpColor: COLORS.pos,
        wickDownColor: COLORS.neg,
      });

      chartRef.current = chart;
      candleSeriesRef.current = candleSeries;

      // Crosshair subscription for OHLC readout
      chart.subscribeCrosshairMove((param) => {
        if (!param || !param.time || !param.seriesData) {
          onHoverBar?.(null);
          return;
        }
        const data = param.seriesData.get(candleSeries);
        if (data) {
          onHoverBar?.({
            time: param.time,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
          });
        }
      });

      // Time range change subscription
      chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
        if (range && onVisibleRangeChange) {
          onVisibleRangeChange(range);
        }
        emitTimeScaleChange();
      });

      // Resize observer
      const resizeObserver = new ResizeObserver((entries) => {
        if (!entries || entries.length === 0) return;
        const { width } = entries[0].contentRect;
        if (width > 0) {
          chart.applyOptions({ width });
          emitTimeScaleChange();
        }
      });
      resizeObserver.observe(containerRef.current);
      emitTimeScaleChange();

      return () => {
        resizeObserver.disconnect();
        chart.remove();
        chartRef.current = null;
        candleSeriesRef.current = null;
        markerPrimitiveRef.current = null;
      };
    } catch {
      // In non-canvas environments (e.g. tests)
      setCanvasSupported(false);
    }
  }, [emitTimeScaleChange]);

  // Set candle data
  useEffect(() => {
    if (!candleSeriesRef.current || candles.length === 0) return;

    // Ensure sorted and valid timestamps
    const sorted = [...candles]
      .filter((c) => c && c.time && c.open !== undefined)
      .sort((a, b) => (a.time < b.time ? -1 : 1));

    candleSeriesRef.current.setData(sorted);
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
      emitTimeScaleChange();
    }
    // Set default hover readout to last candle
    if (sorted.length > 0) {
      onHoverBar?.(sorted[sorted.length - 1]);
    }
  }, [candles]);

  // Set trade markers
  useEffect(() => {
    if (!candleSeriesRef.current || !candles.length) return;

    // Map each trade to its nearest bar
    const candleTimes = new Set(candles.map((c) => c.time));
    const markers = [];

    for (const t of trades) {
      if (market && t.market && t.market !== market) {
        continue;
      }
      let tTime = null;
      if (t.entry_ts) {
        tTime = typeof t.entry_ts === "number" ? t.entry_ts : Math.floor(new Date(t.entry_ts).getTime() / 1000);
      }
      if (!tTime && t.session_date) {
        tTime = Math.floor(new Date(t.session_date).getTime() / 1000);
      }

      if (!tTime) continue;

      // Find closest candle time
      let closestTime = null;
      let minDiff = Infinity;
      for (const cTime of candleTimes) {
        const diff = Math.abs(cTime - tTime);
        if (diff < minDiff) {
          minDiff = diff;
          closestTime = cTime;
        }
      }

      if (closestTime && minDiff < 86400 * 2) {
        const isSelected = selectedTradeId === t.trade_id;
        const isWin = (t.net_pnl || 0) >= 0;

        markers.push({
          time: closestTime,
          position: "belowBar",
          color: isSelected ? COLORS.accent : isWin ? COLORS.pos : COLORS.neg,
          shape: "circle",
          text: "",
          id: t.trade_id,
          size: isSelected ? 2 : 1,
        });
      }
    }

    markers.sort((a, b) => (a.time < b.time ? -1 : 1));

    try {
      if (markerPrimitiveRef.current) {
        markerPrimitiveRef.current.setMarkers(markers);
      } else {
        markerPrimitiveRef.current = createSeriesMarkers(candleSeriesRef.current, markers);
      }
    } catch {
      // ignore
    }
  }, [trades, selectedTradeId, candles, market]);

  // Render indicator overlays
  useEffect(() => {
    if (!chartRef.current || !candles.length) return;

    // Clean up previous indicators
    indicatorSeriesRef.current.forEach((s) => {
      try {
        chartRef.current.removeSeries(s);
      } catch {
        // ignore
      }
    });
    indicatorSeriesRef.current = [];

    const sortedCandles = [...candles].sort((a, b) => (a.time < b.time ? -1 : 1));

    const addLine = (data, color, width = 1.2) => {
      if (!data || data.length === 0) return;
      const s = chartRef.current.addSeries(LineSeries, {
        color,
        lineWidth: width,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      s.setData(data);
      indicatorSeriesRef.current.push(s);
    };

    if (activeIndicators.ema20) addLine(calculateEMA(sortedCandles, 20), COLORS.info);
    if (activeIndicators.ema50) addLine(calculateEMA(sortedCandles, 50), COLORS.accent);
    if (activeIndicators.ema200) addLine(calculateEMA(sortedCandles, 200), COLORS.purple);
    if (activeIndicators.sma20) addLine(calculateSMA(sortedCandles, 20), COLORS.pos);
    if (activeIndicators.sma50) addLine(calculateSMA(sortedCandles, 50), COLORS.negText);

    if (activeIndicators.bollinger) {
      const bb = calculateBollingerBands(sortedCandles, 20, 2);
      addLine(bb.upper, "rgba(124, 196, 255, 0.6)", 1);
      addLine(bb.middle, "rgba(124, 196, 255, 0.3)", 1);
      addLine(bb.lower, "rgba(124, 196, 255, 0.6)", 1);
    }
  }, [activeIndicators, candles]);

  if (isTest || !canvasSupported) {
    return (
      <div
        style={{
          height: typeof height === "number" ? `${height}px` : height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg-app)",
          borderRadius: "4px",
        }}
        className="muted"
      >
        Candlestick chart ({candles.length} bars)
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: typeof height === "number" ? `${height}px` : height,
        position: "relative",
      }}
    />
  );
}
