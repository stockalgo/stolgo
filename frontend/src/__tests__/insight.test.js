import { describe, it, expect } from "vitest";
import { getAutoInsight } from "../lib/verdict.js";

describe("auto-insight rules (§7.4)", () => {
  it("rule 1: right-tail strategy", () => {
    const run = {
      metrics: {
        hit_rate: 0.35,
        payoff: 1.8,
        num_trades: 157,
        fees: 100,
        gross_pnl: 1000,
      },
    };
    const insight = getAutoInsight(run);
    expect(insight).toBe(
      "Right-tail strategy: 35% hit rate, payoff 1.80×. Cutting costs by ₹50 per trade adds ₹7,850."
    );
  });

  it("rule 2: left-tail strategy", () => {
    const run = {
      metrics: {
        hit_rate: 0.65,
        payoff: 0.5,
        num_trades: 100,
        worst_day: -4500,
        fees: 100,
        gross_pnl: 1000,
      },
    };
    const insight = getAutoInsight(run);
    expect(insight).toBe(
      "Left-tail strategy: wins 65% of trades but a loss costs 2.0× a win. Watch the worst day (₹4,500)."
    );
  });

  it("rule 3: high fees relative to gross profit", () => {
    const run = {
      metrics: {
        hit_rate: 0.5,
        payoff: 1.2,
        num_trades: 100,
        fees: 450,
        gross_pnl: 1000,
      },
    };
    const insight = getAutoInsight(run);
    expect(insight).toBe("Costs take 45% of gross profit.");
  });

  it("rule 4: otherwise null (no callout)", () => {
    const run = {
      metrics: {
        hit_rate: 0.5,
        payoff: 1.2,
        num_trades: 100,
        fees: 100,
        gross_pnl: 1000,
      },
    };
    expect(getAutoInsight(run)).toBeNull();
  });
});
