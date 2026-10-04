import { describe, it, expect } from "vitest";
import { getVerdict, isComparable, getStatusBadge } from "../lib/verdict.js";

describe("verdict rules (§7.1, §7.2, §7.3)", () => {
  it("isComparable checks trades and sessions threshold and status", () => {
    const base = {
      status: "ok",
      metrics: { num_trades: 100 },
      window: { sessions: 252 },
    };
    expect(isComparable(base)).toBe(true);

    expect(isComparable({ ...base, metrics: { num_trades: 99 } })).toBe(false);
    expect(isComparable({ ...base, window: { sessions: 251 } })).toBe(false);
    expect(isComparable({ ...base, status: "empty" })).toBe(false);
    expect(isComparable({ ...base, status: "superseded" })).toBe(false);
    expect(isComparable({ ...base, status: "data_issues" })).toBe(true);
  });

  it("verdict rule 1: num_trades === 0", () => {
    const r = { metrics: { num_trades: 0, net_pnl: 0 } };
    const v = getVerdict(r);
    expect(v.label).toBe("NO TRADES");
    expect(v.style).toBe("muted");
    expect(v.text).toBe("Nothing to evaluate");
  });

  it("verdict rule 2: num_trades < 30", () => {
    const r = { metrics: { num_trades: 25, net_pnl: 1000 } };
    const v = getVerdict(r);
    expect(v.label).toBe("EDGE · UNPROVEN");
    expect(v.style).toBe("amber");
    expect(v.text).toBe("Fewer than 30 trades");
  });

  it("verdict rule 3: net_pnl <= 0 or p_net_positive < 0.80", () => {
    const rLoss = { metrics: { num_trades: 50, net_pnl: -100 } };
    const vLoss = getVerdict(rLoss);
    expect(vLoss.label).toBe("NO EDGE");
    expect(vLoss.style).toBe("red");
    expect(vLoss.text).toBe("Net P&L is not positive");

    const rLowP = {
      metrics: { num_trades: 50, net_pnl: 1000 },
      robustness: { p_net_positive: 0.75 },
    };
    const vLowP = getVerdict(rLowP);
    expect(vLowP.label).toBe("NO EDGE");
    expect(vLowP.style).toBe("red");
    expect(vLowP.text).toBe("P(net > 0) below 80%");
  });

  it("verdict rule 4: net_without_top5 <= 0", () => {
    const r = {
      metrics: { num_trades: 50, net_pnl: 1000 },
      robustness: { p_net_positive: 0.96, net_without_top5: -50 },
    };
    const v = getVerdict(r);
    expect(v.label).toBe("EDGE · FRAGILE");
    expect(v.style).toBe("amber");
    expect(v.text).toBe("Profitable, but the best 5 trades carry it");
  });

  it("verdict rule 5: p_net_positive < 0.95 or fragile status", () => {
    const rDataIssues = {
      status: "data_issues",
      metrics: { num_trades: 100, net_pnl: 5000 },
      robustness: { p_net_positive: 0.98, net_without_top5: 2000 },
      data_quality: { trades_with_missing_data: 12 },
    };
    const vData = getVerdict(rDataIssues);
    expect(vData.label).toBe("EDGE · FRAGILE");
    expect(vData.text).toBe("12% forced data exits");

    const rLowSample = {
      status: "low_sample",
      metrics: { num_trades: 50, net_pnl: 5000 },
      robustness: { p_net_positive: 0.98, net_without_top5: 2000 },
    };
    expect(getVerdict(rLowSample).text).toBe("Only 50 trades");

    const rLowProb = {
      status: "ok",
      metrics: { num_trades: 120, net_pnl: 5000 },
      robustness: { p_net_positive: 0.91, net_without_top5: 2000 },
    };
    expect(getVerdict(rLowProb).text).toBe("P(net > 0) is 91%");
  });

  it("verdict rule 6: otherwise EDGE · ROBUST", () => {
    const r = {
      status: "ok",
      metrics: { num_trades: 150, net_pnl: 50000 },
      robustness: { p_net_positive: 0.98, net_without_top5: 20000 },
      window: { sessions: 500 },
    };
    const v = getVerdict(r);
    expect(v.label).toBe("EDGE · ROBUST");
    expect(v.style).toBe("green");
    expect(v.text).toBe("Survives bootstrap and top-5 removal");
  });

  it("getStatusBadge returns correct labels and classes", () => {
    expect(getStatusBadge("ok")).toEqual({ label: "OK", className: "badge--ok" });
    expect(getStatusBadge("low_sample")).toEqual({ label: "Low sample", className: "badge--low" });
    expect(getStatusBadge("data_issues")).toEqual({ label: "Data issues", className: "badge--warn" });
    expect(getStatusBadge("empty")).toEqual({ label: "Empty", className: "badge--muted" });
  });
});
