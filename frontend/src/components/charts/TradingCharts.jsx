import { useEffect, useRef, useState } from "react";
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  createChart,
  createSeriesMarkers,
} from "lightweight-charts";
import { chartColors } from "../../data/constants";
import { dateLabel, money, percent, price, timeLabel } from "../../utils/formatters";

export function TradingCharts({ data, metrics, onSelectTrade, run, selectedTrade, theme }) {
  const priceRef = useRef(null);
  const equityRef = useRef(null);
  const drawdownRef = useRef(null);
  const overlayRef = useRef(null);
  const chartsRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);
  const [drawing, setDrawing] = useState(null);
  const [tools, setTools] = useState({ crosshair: true, tradePath: true });

  useEffect(() => {
    if (!priceRef.current || !equityRef.current || !drawdownRef.current) return undefined;
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
        scaleMargins: { top: 0.12, bottom: 0.18 },
      },
      timeScale: {
        borderColor: chartTheme.border,
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time) => timeLabel(time),
      },
      crosshair: {
        mode: tools.crosshair ? CrosshairMode.Normal : CrosshairMode.Magnet,
        vertLine: { color: "rgba(15, 142, 168, 0.72)", style: 2, width: 1 },
        horzLine: { color: "rgba(15, 142, 168, 0.42)", style: 2, width: 1 },
      },
      handleScroll: true,
      handleScale: true,
    };

    const priceChart = createChart(priceRef.current, {
      ...baseOptions,
      localization: {
        priceFormatter: (value) => price(value),
        timeFormatter: (time) => `${dateLabel(time)} ET`,
      },
    });
    const candleSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: chartColors.green,
      downColor: chartColors.red,
      wickUpColor: chartColors.green,
      wickDownColor: chartColors.red,
      borderVisible: false,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    candleSeries.setData(data.candles);

    const volumeSeries = priceChart.addSeries(HistogramSeries, {
      priceScaleId: "",
      priceFormat: { type: "volume" },
      base: 0,
    });
    volumeSeries.setData(data.volume);
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    createSeriesMarkers(
      candleSeries,
      data.trades.flatMap((trade) => [
        {
          time: trade.entryTime,
          position: trade.side === "Long" ? "belowBar" : "aboveBar",
          color: trade.side === "Long" ? chartColors.green : chartColors.red,
          shape: trade.side === "Long" ? "arrowUp" : "arrowDown",
          text: trade.side,
        },
        {
          time: trade.exitTime,
          position: trade.side === "Long" ? "aboveBar" : "belowBar",
          color: trade.pnl >= 0 ? chartColors.green : chartColors.red,
          shape: "circle",
          text: "Exit",
        },
      ]),
    );

    const equityChart = createChart(equityRef.current, {
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

    const drawdownChart = createChart(drawdownRef.current, {
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

    const updateDrawing = () => {
      const trade = selectedTradeRef.current;
      if (!trade || !overlayRef.current) return;
      const x1 = priceChart.timeScale().timeToCoordinate(trade.entryTime);
      const x2 = priceChart.timeScale().timeToCoordinate(trade.exitTime);
      const y1 = candleSeries.priceToCoordinate(trade.entryPrice);
      const y2 = candleSeries.priceToCoordinate(trade.exitPrice);
      if ([x1, x2, y1, y2].some((point) => point === null)) return;

      const left = Math.min(x1, x2);
      const top = Math.min(y1, y2);
      const width = Math.max(1, Math.abs(x2 - x1));
      const height = Math.max(1, Math.abs(y2 - y1));
      const length = Math.sqrt(width ** 2 + height ** 2);
      const angle = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;

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
        entry: { left: x1, top: y1, label: `Entry ${price(trade.entryPrice)}` },
        exit: { left: x2, top: y2, label: `Exit ${price(trade.exitPrice)}` },
      });
    };

    const selectedTradeRef = { current: selectedTrade };
    const syncRange = (source, targets) => {
      source.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (!range || syncing) return;
        syncing = true;
        targets.forEach((chart) => chart.timeScale().setVisibleLogicalRange(range));
        syncing = false;
        requestAnimationFrame(updateDrawing);
      });
    };

    chartsRef.current = {
      priceChart,
      equityChart,
      drawdownChart,
      candleSeries,
      updateDrawing: () => updateDrawing(),
      selectedTradeRef,
    };

    syncRange(priceChart, [equityChart, drawdownChart]);
    syncRange(equityChart, [priceChart, drawdownChart]);
    syncRange(drawdownChart, [priceChart, equityChart]);

    priceChart.timeScale().fitContent();
    equityChart.timeScale().fitContent();
    drawdownChart.timeScale().fitContent();

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
        return;
      }
      const candle = data.candles.find((item) => item.time === param.time);
      if (!candle) return;
      const hoverTrade = data.trades.find((trade) => param.time >= trade.entryTime && param.time <= trade.exitTime);
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
      window.removeEventListener("resize", updateDrawing);
      priceChart.remove();
      equityChart.remove();
      drawdownChart.remove();
      chartsRef.current = null;
    };
  }, [data, onSelectTrade, selectedTrade, theme, tools.crosshair]);

  useEffect(() => {
    if (!chartsRef.current) return;
    chartsRef.current.selectedTradeRef.current = selectedTrade;
    requestAnimationFrame(chartsRef.current.updateDrawing);
  }, [selectedTrade]);

  const lastCandle = data.candles.at(-1);
  const priorCandle = data.candles.at(-2);
  const finalEquity = data.equity.at(-1)?.value;
  const currentDrawdown = data.drawdown.at(-1)?.value;
  const maxDrawdown = data.drawdown.reduce((lowest, point) => Math.min(lowest, point.value), 0);
  const change = lastCandle && priorCandle ? lastCandle.close - priorCandle.close : 0;
  const changePct = priorCandle ? change / priorCandle.close : 0;

  return (
    <section className="chart-stack" aria-label="Strategy chart workspace">
      <div className="chart-toolbar">
        <div>
          <span className="chart-title">{run?.market ?? "-"} {run?.timeframe ?? "-"}</span>
          {lastCandle && (
            <>
              <span className="ohlc">O {price(lastCandle.open)}</span>
              <span className="ohlc">H {price(lastCandle.high)}</span>
              <span className="ohlc">L {price(lastCandle.low)}</span>
              <span className="ohlc">C {price(lastCandle.close)}</span>
              <span className={change >= 0 ? "positive" : "negative"}>{price(change)} ({percent(changePct)})</span>
            </>
          )}
        </div>
        <div className="tool-group" aria-label="Chart tools">
          {["crosshair", "tradePath"].map((tool) => (
            <button
              className={tools[tool] ? "active" : ""}
              key={tool}
              type="button"
              onClick={() => setTools((current) => ({ ...current, [tool]: !current[tool] }))}
            >
              {tool === "tradePath" ? "Trade path" : tool.charAt(0).toUpperCase() + tool.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="price-chart-wrap">
        <div className="price-chart" ref={priceRef} />
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
        {tooltip && (
          <div className="chart-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
            <div className="tooltip-date">{dateLabel(tooltip.candle.time)}</div>
            <div><span>Open</span><b>{price(tooltip.candle.open)}</b></div>
            <div><span>High</span><b>{price(tooltip.candle.high)}</b></div>
            <div><span>Low</span><b>{price(tooltip.candle.low)}</b></div>
            <div><span>Close</span><b>{price(tooltip.candle.close)}</b></div>
            {tooltip.trade && (
              <div className="tooltip-trade">
                <strong>Trade {tooltip.trade.id}</strong>
                <span className={tooltip.trade.pnlClass}>{money(tooltip.trade.pnl)} · {tooltip.trade.r}R</span>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="subchart">
        <div className="panel-label">
          Equity curve
          {finalEquity !== undefined && <span>Final: {money(finalEquity)}</span>}
          <strong>Net {percent(metrics?.total_return ?? 0)}</strong>
        </div>
        <div className="subchart-canvas" ref={equityRef} />
      </div>
      <div className="subchart compact">
        <div className="panel-label">
          Drawdown
          <span>Max: {maxDrawdown.toFixed(2)}%</span>
          <strong className="negative">Current {(currentDrawdown ?? 0).toFixed(2)}%</strong>
        </div>
        <div className="subchart-canvas" ref={drawdownRef} />
      </div>
    </section>
  );
}
