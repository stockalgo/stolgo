import { describe, it, expect } from "vitest";
import { isBestComparableValue } from "../lib/verdict.js";

describe("compare highlight rule (§8.7, §10)", () => {
  it("a non-comparable run is never highlighted even when its value is the maximum", () => {
    // Non-comparable run has highest Sharpe (4.78) but only 14 trades
    const nonComparableRun = {
      id: "top1",
      status: "low_sample",
      metrics: { num_trades: 14, sharpe: 4.78, max_drawdown: -0.01 },
      window: { sessions: 65 },
    };

    // Comparable run A has Sharpe 0.78 and 157 trades
    const compA = {
      id: "static",
      status: "ok",
      metrics: { num_trades: 157, sharpe: 0.78, max_drawdown: -0.05 },
      window: { sessions: 740 },
    };

    // Comparable run B has Sharpe 0.73 and 157 trades
    const compB = {
      id: "benchmark",
      status: "ok",
      metrics: { num_trades: 157, sharpe: 0.73, max_drawdown: -0.09 },
      window: { sessions: 740 },
    };

    const all = [nonComparableRun, compA, compB];

    // nonComparableRun has highest Sharpe (4.78) but MUST NOT be highlighted
    expect(isBestComparableValue(nonComparableRun, "sharpe", all)).toBe(false);

    // compA has best Sharpe among comparable runs (0.78) -> MUST be highlighted
    expect(isBestComparableValue(compA, "sharpe", all)).toBe(true);

    // compB is not the best -> false
    expect(isBestComparableValue(compB, "sharpe", all)).toBe(false);

    // Test for 'lower is better' (e.g. max_drawdown: closer to 0 is better, but numerically -0.05 > -0.09)
    expect(isBestComparableValue(compA, "max_drawdown", all, "higher")).toBe(true);
  });
});
