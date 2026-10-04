/**
 * Histogram binning logic for trade P&L and R-multiples (UI plan §8.3).
 */

export function computeHistogramBins(values = [], binSize = 1000) {
  const valid = values.filter((v) => v !== null && v !== undefined && !Number.isNaN(v));
  if (valid.length === 0) {
    return { minEdge: 0, maxEdge: 0, binSize, bins: [] };
  }

  const min = Math.min(...valid);
  const max = Math.max(...valid);

  const minEdge = Math.floor(min / binSize) * binSize;
  const maxEdge = Math.ceil(max / binSize) * binSize;

  const numBins = Math.max(1, Math.round((maxEdge - minEdge) / binSize));
  const bins = [];

  for (let i = 0; i < numBins; i++) {
    const start = minEdge + i * binSize;
    const end = start + binSize;
    bins.push({
      start,
      end,
      count: 0,
      isNegative: end <= 0 || (start < 0 && end <= 0) || start < 0,
    });
  }

  for (const v of valid) {
    let idx = Math.floor((v - minEdge) / binSize);
    if (idx < 0) idx = 0;
    if (idx >= numBins) idx = numBins - 1;
    bins[idx].count += 1;
  }

  return {
    minEdge,
    maxEdge,
    binSize,
    bins,
  };
}
