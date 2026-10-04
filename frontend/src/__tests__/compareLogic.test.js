import { describe, it, expect } from "vitest";
import {
  formatMonthYear,
  parseRunIds,
  getMetricValue,
  isBestValue,
  COMPARE_METRICS,
} from "../lib/compareLogic.js";

describe("compareLogic", () => {
  describe("formatMonthYear", () => {
    it("formats YYYY-MM-DD correctly", () => {
      expect(formatMonthYear("2024-01-15")).toBe("Jan 2024");
      expect(formatMonthYear("2023-11-30")).toBe("Nov 2023");
      expect(formatMonthYear("")).toBe("");
      expect(formatMonthYear(null)).toBe("");
      expect(formatMonthYear("invalid")).toBe("invalid");
    });
  });

  describe("parseRunIds", () => {
    it("parses empty or missing params into empty array", () => {
      expect(parseRunIds("")).toEqual([]);
      expect(parseRunIds(null)).toEqual([]);
    });

    it("parses comma-separated IDs and trims whitespace", () => {
      expect(parseRunIds("run-1, run-2 ,run-3")).toEqual(["run-1", "run-2", "run-3"]);
    });

    it("limits to 4 run IDs", () => {
      expect(parseRunIds("r1,r2,r3,r4,r5,r6")).toEqual(["r1", "r2", "r3", "r4"]);
    });
  });

  describe("getMetricValue", () => {
    it("fetches metrics from metrics dict", () => {
      const run = { metrics: { sharpe: 1.5, net_pnl: 1000 } };
      expect(getMetricValue(run, "sharpe")).toBe(1.5);
      expect(getMetricValue(run, "net_pnl")).toBe(1000);
    });

    it("falls back to robustness dict for p_net_positive and net_without_top5", () => {
      const runWithRobustness = {
        metrics: {},
        robustness: { p_net_positive: 0.95, net_without_top5: 850 },
      };
      expect(getMetricValue(runWithRobustness, "p_net_positive")).toBe(0.95);
      expect(getMetricValue(runWithRobustness, "net_without_top5")).toBe(850);

      const runWithMetrics = {
        metrics: { p_net_positive: 0.88, net_without_top5: 700 },
      };
      expect(getMetricValue(runWithMetrics, "p_net_positive")).toBe(0.88);
      expect(getMetricValue(runWithMetrics, "net_without_top5")).toBe(700);
    });

    it("handles null or undefined run", () => {
      expect(getMetricValue(null, "sharpe")).toBeUndefined();
    });
  });

  describe("isBestValue", () => {
    it("highlights best value among comparable runs only", () => {
      const runs = [
        {
          id: "r1",
          status: "ok",
          metrics: { num_trades: 120, total_return: 0.25 },
          window: { sessions: 300 },
        },
        {
          id: "r2",
          status: "ok",
          metrics: { num_trades: 150, total_return: 0.35 },
          window: { sessions: 300 },
        },
        {
          id: "r3_short",
          status: "low_sample",
          metrics: { num_trades: 20, total_return: 0.85 }, // highest but not comparable
          window: { sessions: 40 },
        },
      ];

      expect(isBestValue(runs[0], "total_return", runs)).toBe(false);
      expect(isBestValue(runs[1], "total_return", runs)).toBe(true);
      expect(isBestValue(runs[2], "total_return", runs)).toBe(false);
    });

    it("correctly identifies best robustness metrics", () => {
      const runs = [
        {
          id: "r1",
          status: "ok",
          metrics: { num_trades: 120 },
          robustness: { net_without_top5: 500 },
          window: { sessions: 300 },
        },
        {
          id: "r2",
          status: "ok",
          metrics: { num_trades: 150 },
          robustness: { net_without_top5: 750 },
          window: { sessions: 300 },
        },
      ];

      expect(isBestValue(runs[0], "net_without_top5", runs)).toBe(false);
      expect(isBestValue(runs[1], "net_without_top5", runs)).toBe(true);
    });
  });

  describe("COMPARE_METRICS configuration", () => {
    it("contains all expected comparison metrics", () => {
      const keys = COMPARE_METRICS.map((m) => m.key);
      expect(keys).toContain("net_pnl");
      expect(keys).toContain("total_return");
      expect(keys).toContain("cagr");
      expect(keys).toContain("sharpe");
      expect(keys).toContain("sortino");
      expect(keys).toContain("max_drawdown");
      expect(keys).toContain("profit_factor");
      expect(keys).toContain("hit_rate");
      expect(keys).toContain("p_net_positive");
      expect(keys).toContain("net_without_top5");
    });

    it("flags cagr warning when annualised from short window", () => {
      const cagrDef = COMPARE_METRICS.find((m) => m.key === "cagr");
      const shortRun = {
        metrics: { annualised_from_short_window: true, num_trades: 20 },
        window: { sessions: 40 },
      };
      const normalRun = {
        metrics: { annualised_from_short_window: false, num_trades: 200 },
        window: { sessions: 500 },
      };
      expect(cagrDef.warnIf(shortRun)).toBe(true);
      expect(cagrDef.warnIf(normalRun)).toBe(false);
    });
  });
});
