import { describe, it, expect } from "vitest";
import { computeHistogramBins } from "../lib/histogram.js";

describe("computeHistogramBins", () => {
  it("computes bin edges for [-4282.4, 10570.6] as -5000...11000", () => {
    const values = [-4282.4, 10570.6];
    const result = computeHistogramBins(values, 1000);

    expect(result.minEdge).toBe(-5000);
    expect(result.maxEdge).toBe(11000);
    expect(result.bins.length).toBe(16);
    expect(result.bins[0].start).toBe(-5000);
    expect(result.bins[0].end).toBe(-4000);
    expect(result.bins[0].count).toBe(1);
    expect(result.bins[15].start).toBe(10000);
    expect(result.bins[15].end).toBe(11000);
    expect(result.bins[15].count).toBe(1);
  });

  it("handles R-multiple bins with 0.5 step", () => {
    const values = [-1.5, 2.3, 0.4];
    const result = computeHistogramBins(values, 0.5);

    expect(result.minEdge).toBe(-1.5);
    expect(result.maxEdge).toBe(2.5);
    expect(result.bins.length).toBe(8);
  });

  it("handles empty values gracefully", () => {
    const result = computeHistogramBins([], 1000);
    expect(result.bins).toEqual([]);
    expect(result.minEdge).toBe(0);
    expect(result.maxEdge).toBe(0);
  });
});
