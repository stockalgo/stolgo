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

  // Check if incoming volume data has real values or is all zero/empty
  const hasRealVolume = volume && volume.some((v) => v.value > 0);

  const getEffectiveVol = (bar) => {
    if (hasRealVolume) {
      const found = volume.find((v) => v.time === bar.time);
      if (found && found.value > 0) return found.value;
    }
    // Calculate synthetic range volume: True range as a percentage of price * 100,000 lots
    // Ensure minimum base volume of 1,250 so volume bars are always visible
    const range = Math.max(1.5, bar.high - bar.low);
    const typical = (bar.high + bar.low + bar.close) / 3 || 1;
    return Math.max(1250, Math.round((range / typical) * 1000000));
  };

  // If target interval is smaller than base interval, return original
  if (tfConfig.seconds <= baseInterval) {
    if (hasRealVolume) {
      return { candles, volume };
    }
    const derivedVol = candles.map((c) => ({
      time: c.time,
      value: getEffectiveVol(c),
      color: c.close >= c.open ? "rgba(20, 154, 90, 0.28)" : "rgba(200, 63, 58, 0.24)",
    }));
    return { candles, volume: derivedVol };
  }

  const resampledCandles = [];
  const resampledVolume = [];
  const volMap = new Map();
  for (const c of candles) {
    volMap.set(c.time, getEffectiveVol(c));
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
