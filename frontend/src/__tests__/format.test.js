import { describe, it, expect } from "vitest";
import {
  inr,
  inrCompact,
  pct,
  ratio,
  count,
  sessions,
  rmult,
  premium,
  level,
  dateIST,
  timeIST,
  sessionLabel,
  sessionShort,
  formatMetric,
} from "../lib/format.js";

describe("format library (§5)", () => {
  it("inr formats correctly", () => {
    expect(inr(30330.69)).toBe("₹30,331");
    expect(inr(30330.69, { signed: true })).toBe("+₹30,331");
    expect(inr(-6014)).toBe("−₹6,014");
    expect(inr(123456789)).toBe("₹12,34,56,789");
    expect(inr(null)).toBe("—");
    expect(inr(NaN)).toBe("—");
  });

  it("inrCompact formats correctly", () => {
    expect(inrCompact(53787)).toBe("₹53.8k");
    expect(inrCompact(1234567)).toBe("₹12.3L");
    expect(inrCompact(-8000)).toBe("−₹8k");
    expect(inrCompact(null)).toBe("—");
  });

  it("pct formats correctly", () => {
    expect(pct(0.168504)).toBe("+16.9%");
    expect(pct(-0.095192)).toBe("−9.5%");
    expect(pct(0)).toBe("0.0%");
    expect(pct(null)).toBe("—");
  });

  it("ratio formats correctly", () => {
    expect(ratio(0.733478)).toBe("0.73");
    expect(ratio(-0.004)).toBe("0.00");
    expect(ratio(null)).toBe("—");
  });

  it("count and sessions format correctly", () => {
    expect(count(157)).toBe("157");
    expect(count(12000)).toBe("12,000");
    expect(count(null)).toBe("—");

    expect(sessions(347)).toBe("347 sessions");
    expect(sessions(null)).toBe("—");
  });

  it("rmult formats correctly", () => {
    expect(rmult(0.6416)).toBe("+0.64R");
    expect(rmult(-0.25)).toBe("−0.25R");
    expect(rmult(null)).toBe("—");
  });

  it("premium and level format correctly", () => {
    expect(premium(26.7)).toBe("26.7");
    expect(premium(null)).toBe("—");

    expect(level(23671.8)).toBe("23,671.8");
    expect(level(null)).toBe("—");
  });

  it("dateIST and timeIST format correctly", () => {
    // 1788858000 = 2026-09-08 09:00:00 UTC = 14:30:00 IST
    expect(dateIST(1788858000)).toBe("08 Sep 2026");
    // 1788771600 = 2026-09-07 09:00:00 UTC = 14:30:00 IST
    expect(dateIST(1788771600)).toBe("07 Sep 2026");
    // 1788840000 = 2026-09-08 04:00:00 UTC = 09:30:00 IST
    expect(timeIST(1788840000)).toBe("09:30");
  });

  it("sessionLabel and sessionShort format correctly", () => {
    expect(sessionLabel("2026-09-08")).toBe("08 Sep 2026");
    expect(sessionShort("2026-09-08")).toBe("08 Sep");
  });

  it("formatMetric dispatches by unit", () => {
    const defs = [
      { key: "net_pnl", unit: "inr", better: "higher" },
      { key: "fees", unit: "inr", better: "lower" },
      { key: "sharpe", unit: "ratio", decimals: 2, better: "higher" },
      { key: "total_return", unit: "fraction", better: "higher" },
    ];
    expect(formatMetric("net_pnl", 5000, defs)).toBe("+₹5,000");
    expect(formatMetric("fees", 200, defs)).toBe("₹200");
    expect(formatMetric("sharpe", 1.25, defs)).toBe("1.25");
    expect(formatMetric("total_return", 0.05, defs)).toBe("+5.0%");
  });
});
