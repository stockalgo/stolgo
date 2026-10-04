/**
 * Technical indicators calculation engine for lightweight-charts.
 * Fast, pure, client-side algorithms for SMA, EMA, Bollinger Bands, VWAP, RSI, and Volume MA.
 */

export function calculateSMA(candles, period = 20) {
  if (!candles || candles.length < period) return [];
  const result = [];
  let sum = 0;
  for (let i = 0; i < candles.length; i++) {
    sum += candles[i].close;
    if (i >= period) {
      sum -= candles[i - period].close;
    }
    if (i >= period - 1) {
      result.push({
        time: candles[i].time,
        value: Number((sum / period).toFixed(2)),
      });
    }
  }
  return result;
}

export function calculateEMA(candles, period = 20) {
  if (!candles || candles.length < period) return [];
  const result = [];
  const multiplier = 2 / (period + 1);

  // Initial SMA seed
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += candles[i].close;
  }
  let prevEMA = sum / period;
  result.push({
    time: candles[period - 1].time,
    value: Number(prevEMA.toFixed(2)),
  });

  for (let i = period; i < candles.length; i++) {
    const currentClose = candles[i].close;
    const currentEMA = (currentClose - prevEMA) * multiplier + prevEMA;
    result.push({
      time: candles[i].time,
      value: Number(currentEMA.toFixed(2)),
    });
    prevEMA = currentEMA;
  }
  return result;
}

export function calculateBollingerBands(candles, period = 20, stdDev = 2) {
  if (!candles || candles.length < period) return { upper: [], middle: [], lower: [] };
  const upper = [];
  const middle = [];
  const lower = [];

  for (let i = period - 1; i < candles.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += candles[i - j].close;
    }
    const mean = sum / period;

    let varianceSum = 0;
    for (let j = 0; j < period; j++) {
      varianceSum += Math.pow(candles[i - j].close - mean, 2);
    }
    const sd = Math.sqrt(varianceSum / period);

    const t = candles[i].time;
    middle.push({ time: t, value: Number(mean.toFixed(2)) });
    upper.push({ time: t, value: Number((mean + stdDev * sd).toFixed(2)) });
    lower.push({ time: t, value: Number((mean - stdDev * sd).toFixed(2)) });
  }

  return { upper, middle, lower };
}

export function calculateVWAP(candles, volume = [], timeZone = "Asia/Kolkata") {
  if (!candles || candles.length === 0) return [];
  const result = [];
  const volMap = new Map();
  for (const v of volume) {
    volMap.set(v.time, v.value);
  }

  let currentDay = null;
  let cumTPV = 0;
  let cumVol = 0;

  for (let i = 0; i < candles.length; i++) {
    const bar = candles[i];
    const day = new Date(bar.time * 1000).toLocaleDateString("en-CA", { timeZone });

    if (day !== currentDay) {
      currentDay = day;
      cumTPV = 0;
      cumVol = 0;
    }

    const tp = (bar.high + bar.low + bar.close) / 3;
    const v = volMap.get(bar.time) || 1; // fallback if vol is 0
    cumTPV += tp * v;
    cumVol += v;

    result.push({
      time: bar.time,
      value: Number((cumTPV / (cumVol || 1)).toFixed(2)),
    });
  }
  return result;
}

export function calculateRSI(candles, period = 14) {
  if (!candles || candles.length <= period) return [];
  const result = [];

  let avgGain = 0;
  let avgLoss = 0;

  for (let i = 1; i <= period; i++) {
    const diff = candles[i].close - candles[i - 1].close;
    if (diff >= 0) avgGain += diff;
    else avgLoss += Math.abs(diff);
  }

  avgGain /= period;
  avgLoss /= period;

  let rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  let rsi = 100 - (100 / (1 + rs));
  result.push({ time: candles[period].time, value: Number(rsi.toFixed(2)) });

  for (let i = period + 1; i < candles.length; i++) {
    const diff = candles[i].close - candles[i - 1].close;
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? Math.abs(diff) : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    rsi = 100 - (100 / (1 + rs));
    result.push({ time: candles[i].time, value: Number(rsi.toFixed(2)) });
  }

  return result;
}

export function calculateVolumeMA(volume = [], period = 20) {
  if (!volume || volume.length < period) return [];
  const result = [];
  let sum = 0;
  for (let i = 0; i < volume.length; i++) {
    sum += volume[i].value;
    if (i >= period) {
      sum -= volume[i - period].value;
    }
    if (i >= period - 1) {
      result.push({
        time: volume[i].time,
        value: Number((sum / period).toFixed(0)),
      });
    }
  }
  return result;
}
