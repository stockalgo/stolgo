/**
 * Resamples OHLCV candle and volume series to higher timeframes.
 * Supports: '5m', '15m', '1h', '1D', '1W'.
 */

export const TIMEFRAMES = [
  { id: "5m", label: "5m", seconds: 300 },
  { id: "15m", label: "15m", seconds: 900 },
  { id: "1h", label: "1h", seconds: 3600 },
  { id: "1D", label: "1D", seconds: 86400 },
  { id: "1W", label: "1W", seconds: 604800 },
];

export function detectBaseInterval(candles) {
  if (!candles || candles.length < 2) return 900; // default 15m
  const diffs = [];
  const limit = Math.min(candles.length - 1, 30);
  for (let i = 0; i < limit; i++) {
    const diff = candles[i + 1].time - candles[i].time;
    if (diff > 0 && diff <= 86400) diffs.push(diff);
  }
  if (!diffs.length) return 900;
  diffs.sort((a, b) => a - b);
  return diffs[Math.floor(diffs.length / 2)];
}

export function resampleCandles(candles, volume = [], targetTf = "15m", timeZone = "Asia/Kolkata") {
  if (!candles || candles.length === 0) {
    return { candles: [], volume: [] };
  }

  const tfConfig = TIMEFRAMES.find((tf) => tf.id === targetTf) || TIMEFRAMES[1];
  const baseInterval = detectBaseInterval(candles);

  // If target interval is smaller than base interval, return original
  if (tfConfig.seconds <= baseInterval) {
    return { candles, volume };
  }

  const resampledCandles = [];
  const resampledVolume = [];
  const volMap = new Map();
  for (const v of volume) {
    volMap.set(v.time, v.value);
  }

  const getBucketKey = (ts) => {
    const d = new Date(ts * 1000);
    if (targetTf === "1D") {
      return d.toLocaleDateString("en-CA", { timeZone }); // YYYY-MM-DD
    }
    if (targetTf === "1W") {
      const day = d.getDay() || 7;
      const monday = new Date(d);
      monday.setDate(d.getDate() - day + 1);
      return monday.toLocaleDateString("en-CA", { timeZone });
    }
    return Math.floor(ts / tfConfig.seconds) * tfConfig.seconds;
  };

  let currentBucketKey = null;
  let currentCandle = null;
  let currentVol = 0;

  for (let i = 0; i < candles.length; i++) {
    const bar = candles[i];
    const key = getBucketKey(bar.time);
    const barVol = volMap.get(bar.time) || 0;

    if (key !== currentBucketKey) {
      if (currentCandle) {
        resampledCandles.push(currentCandle);
        resampledVolume.push({
          time: currentCandle.time,
          value: currentVol,
          color: currentCandle.close >= currentCandle.open ? "rgba(20, 154, 90, 0.2)" : "rgba(200, 63, 58, 0.18)",
        });
      }
      currentBucketKey = key;
      currentCandle = {
        time: typeof key === "number" ? key : bar.time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      };
      currentVol = barVol;
    } else {
      currentCandle.high = Math.max(currentCandle.high, bar.high);
      currentCandle.low = Math.min(currentCandle.low, bar.low);
      currentCandle.close = bar.close;
      currentVol += barVol;
    }
  }

  if (currentCandle) {
    resampledCandles.push(currentCandle);
    resampledVolume.push({
      time: currentCandle.time,
      value: currentVol,
      color: currentCandle.close >= currentCandle.open ? "rgba(20, 154, 90, 0.2)" : "rgba(200, 63, 58, 0.18)",
    });
  }

  return { candles: resampledCandles, volume: resampledVolume };
}
