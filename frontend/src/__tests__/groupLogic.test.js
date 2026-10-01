import { describe, it, expect } from "vitest";
import {
  deriveRows,
  deriveCols,
  aggregateHeatGrid,
  calculateGridExtremes,
  deriveRemainingAxes,
  pickTop4Runs,
  calculateWindowRange,
  calculateKnobEffects,
} from "../lib/groupLogic.js";

describe("groupLogic", () => {
  describe("deriveRows", () => {
    it("sorts family rows by predefined canonical order", () => {
      const axes = { family: ["CUT", "STATIC", "A", "UNKNOWN"] };
      const rows = deriveRows(axes, "family");
      expect(rows).toEqual(["STATIC", "A", "CUT", "UNKNOWN"]);
    });

    it("sorts numeric and string rows consistently", () => {
      const axes = { dte: [3, 0, 1] };
      expect(deriveRows(axes, "dte")).toEqual([0, 1, 3]);

      const axesStr = { tag: ["beta", "alpha"] };
      expect(deriveRows(axesStr, "tag")).toEqual(["alpha", "beta"]);
    });
  });

  describe("deriveCols", () => {
    it("builds composite market × dte columns", () => {
      const axes = { market: ["NIFTY"], dte: [0, 1] };
      const cols = deriveCols(axes, "market × dte");
      expect(cols).toEqual([
        { key: "NIFTY 0-DTE", label: "NIFTY 0-DTE", market: "NIFTY", dte: 0 },
        { key: "NIFTY 1-DTE", label: "NIFTY 1-DTE", market: "NIFTY", dte: 1 },
      ]);
    });

    it("builds standard single-axis columns", () => {
      const axes = { dte: [0, 1] };
      const cols = deriveCols(axes, "dte");
      expect(cols).toEqual([
        { key: "0", label: "dte 0", val: 0 },
        { key: "1", label: "dte 1", val: 1 },
      ]);
    });
  });

  describe("aggregateHeatGrid", () => {
    it("aggregates runs into grid cells correctly", () => {
      const rows = ["A", "B"];
      const cols = [{ key: "NIFTY 0-DTE" }, { key: "NIFTY 1-DTE" }];
      const runs = [
        {
          id: "r1",
          group: { axes: { family: "A", market: "NIFTY", dte: 0 } },
          metrics: { total_return: 0.1, sharpe: 1.0, max_drawdown: -0.05 },
        },
        {
          id: "r2",
          group: { axes: { family: "A", market: "NIFTY", dte: 0 } },
          metrics: { total_return: 0.3, sharpe: 2.0, max_drawdown: -0.02 },
        },
      ];

      const grid = aggregateHeatGrid(runs, rows, cols, "family", "market × dte");
      const cellA0 = grid.get("A__NIFTY 0-DTE");
      expect(cellA0.count).toBe(2);
      expect(cellA0.meanReturn).toBeCloseTo(0.2);
      expect(cellA0.meanSharpe).toBeCloseTo(1.5);
      expect(cellA0.worstDD).toBe(-0.05);
      expect(cellA0.posRatio).toBe(1.0);

      const cellEmpty = grid.get("B__NIFTY 1-DTE");
      expect(cellEmpty.count).toBe(0);
      expect(cellEmpty.runs).toEqual([]);
    });
  });

  describe("calculateGridExtremes", () => {
    it("computes min and max strings across grid cells", () => {
      const map = new Map();
      map.set("c1", { count: 1, meanReturn: 0.12, meanSharpe: 1.2, worstDD: -0.08, posRatio: 0.5 });
      map.set("c2", { count: 1, meanReturn: -0.04, meanSharpe: 0.4, worstDD: -0.15, posRatio: 0.2 });

      const returnExtremes = calculateGridExtremes(map, "return");
      expect(returnExtremes.minStr).toBe("−4%");
      expect(returnExtremes.maxStr).toBe("+12%");

      const sharpeExtremes = calculateGridExtremes(map, "sharpe");
      expect(sharpeExtremes.minStr).toBe("0.40");
      expect(sharpeExtremes.maxStr).toBe("1.20");
    });
  });

  describe("deriveRemainingAxes", () => {
    it("excludes row and col axes properly", () => {
      const axes = { family: ["A"], market: ["NIFTY"], dte: [0], sl: [1.5, 2.0] };
      const rem = deriveRemainingAxes(axes, "family", "market × dte");
      expect(rem).toEqual(["sl"]);

      const remSingle = deriveRemainingAxes(axes, "family", "market");
      expect(remSingle).toEqual(["dte", "sl"]);
    });
  });

  describe("pickTop4Runs", () => {
    it("filters and sorts runs according to metric", () => {
      const runs = [
        { id: "r1", status: "ok", metrics: { num_trades: 120, total_return: 0.1, sharpe: 0.5 }, window: { sessions: 300 } },
        { id: "r2", status: "ok", metrics: { num_trades: 120, total_return: 0.4, sharpe: 1.8 }, window: { sessions: 300 } },
        { id: "r3", status: "ok", metrics: { num_trades: 120, total_return: 0.2, sharpe: 1.2 }, window: { sessions: 300 } },
        { id: "r4", status: "ok", metrics: { num_trades: 120, total_return: 0.3, sharpe: 0.9 }, window: { sessions: 300 } },
        { id: "r5", status: "ok", metrics: { num_trades: 120, total_return: 0.5, sharpe: 0.1 }, window: { sessions: 300 } },
      ];

      const topBySharpe = pickTop4Runs(runs, "sharpe");
      expect(topBySharpe).toEqual(["r2", "r3", "r4", "r1"]);

      const topByReturn = pickTop4Runs(runs, "return");
      expect(topByReturn).toEqual(["r5", "r2", "r4", "r3"]);
    });
  });

  describe("calculateWindowRange", () => {
    it("finds the overall span across runs", () => {
      const runs = [
        { window: { start: "2024-01-01", end: "2024-06-01" } },
        { window: { start: "2023-01-01", end: "2024-12-31" } },
      ];
      expect(calculateWindowRange(runs)).toBe("2023-01-01 → 2024-12-31");
      expect(calculateWindowRange([])).toBe("—");
    });
  });

  describe("calculateKnobEffects", () => {
    it("calculates column stats and callout text", () => {
      const runs = [
        {
          id: "r1",
          group: { axes: { family: "A", market: "NIFTY", dte: 0, sl: "1.5" } },
          metrics: { total_return: 0.1 },
        },
        {
          id: "r2",
          group: { axes: { family: "B", market: "NIFTY", dte: 0, sl: "2.0" } },
          metrics: { total_return: -0.05 },
        },
      ];
      const axes = { family: ["A", "B"], market: ["NIFTY"], dte: [0], sl: ["1.5", "2.0"] };
      const cols = [{ key: "NIFTY 0-DTE", label: "NIFTY 0-DTE" }];
      const rows = ["A", "B"];

      const res = calculateKnobEffects({
        runs,
        axes,
        cols,
        rows,
        rowAxis: "family",
        colAxis: "market × dte",
      });

      expect(res).not.toBeNull();
      expect(res.colStats).toHaveLength(1);
      expect(res.colStats[0].total).toBe(2);
      expect(res.colStats[0].pos).toBe(1);
      expect(res.calloutText).toBeDefined();
    });
  });
});
