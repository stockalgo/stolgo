import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TradesFooter } from "../components/trades/TradesFooter.jsx";

describe("TradesFooter", () => {
  it("renders reconciliation checkmark (✓) when gross − fees − slippage = net", () => {
    const reconcilingTrades = [
      {
        trade_id: 1,
        gross_pnl: 1000,
        fees: 100,
        slippage: 50,
        net_pnl: 850,
        r_multiple: 1.0,
      },
      {
        trade_id: 2,
        gross_pnl: 500,
        fees: 50,
        slippage: 20,
        net_pnl: 430,
        r_multiple: 0.5,
      },
    ];

    render(
      <table>
        <TradesFooter trades={reconcilingTrades} filterDesc="all" />
      </table>
    );

    expect(
      screen.getByText("Gross − fees − slippage = net ✓")
    ).toBeInTheDocument();
    expect(screen.getByText(/2 trades · 2 W \/ 0 L/)).toBeInTheDocument();
    expect(screen.getByText("+0.75")).toBeInTheDocument();
  });

  it("renders warning (⚠) with difference when trades do not reconcile", () => {
    const brokenTrades = [
      {
        trade_id: 1,
        gross_pnl: 1000,
        fees: 100,
        slippage: 0,
        net_pnl: 500, // missing 400
        r_multiple: 0.5,
      },
    ];

    render(
      <table>
        <TradesFooter trades={brokenTrades} filterDesc="winners" />
      </table>
    );

    expect(
      screen.getByText(/⚠ does not reconcile by ₹400/)
    ).toBeInTheDocument();
  });
});
