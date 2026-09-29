import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TradesTable } from "../components/trades/TradesTable.jsx";

describe("TradesTable (§Plan 03 R13)", () => {
  const singleMarketTrades = [
    {
      trade_id: 1,
      session_date: "2024-01-02",
      structure: "short_strangle",
      legs_label: "-C21500 -P21500",
      underlying_entry: 21500,
      underlying_exit: null, // exit is null -> no "→ —" subline
      premium_entry: 100,
      premium_exit: 50,
      qty: 50,
      lots: 1,
      gross_pnl: 2500,
      fees: 50,
      slippage: 0,
      net_pnl: 2450,
      r_multiple: 1.2,
      exit_reason: "TARGET",
      data_flag: null,
      market: "NIFTY",
    },
  ];

  it("omits the sub-line when exit value is null (no '→ —')", () => {
    const { container } = render(
      <TradesTable
        trades={singleMarketTrades}
        filteredTrades={singleMarketTrades}
        instrument={{ markets: ["NIFTY"] }}
      />
    );

    // Should NOT contain "→ —"
    expect(container.textContent).not.toContain("→ —");
    expect(container.textContent).not.toContain("&rarr; —");
    // Should NOT have Market column header for single market
    expect(screen.queryByRole("columnheader", { name: "Market" })).toBeNull();
  });

  it("renders Market column when instrument.markets.length > 1", () => {
    const mixedTrades = [
      {
        ...singleMarketTrades[0],
        market: "NIFTY",
      },
      {
        ...singleMarketTrades[0],
        trade_id: 2,
        market: "SENSEX",
      },
    ];

    render(
      <TradesTable
        trades={mixedTrades}
        filteredTrades={mixedTrades}
        instrument={{ markets: ["NIFTY", "SENSEX"] }}
      />
    );

    // Should have Market column header
    expect(screen.getByRole("columnheader", { name: "Market" })).toBeInTheDocument();
    expect(screen.getByText("NIFTY")).toBeInTheDocument();
    expect(screen.getByText("SENSEX")).toBeInTheDocument();
  });
});
