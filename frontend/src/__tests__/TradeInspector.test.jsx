import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { TradeInspector } from "../components/inspector/TradeInspector.jsx";

const sampleTrades = [
  { trade_id: 151, session_date: "2024-07-28", net_pnl: 500, r_multiple: 0.5 },
  { trade_id: 152, session_date: "2024-08-04", net_pnl: -687, r_multiple: -0.68 },
  { trade_id: 153, session_date: "2024-08-11", net_pnl: 3043, r_multiple: 1.5 },
  { trade_id: 154, session_date: "2024-08-18", net_pnl: -712, r_multiple: -0.7 },
  { trade_id: 155, session_date: "2024-08-25", net_pnl: 810, r_multiple: 0.8 },
  { trade_id: 156, session_date: "2024-09-01", net_pnl: -902, r_multiple: -0.9 },
  { trade_id: 157, session_date: "2024-09-08", net_pnl: 1155, r_multiple: 0.64 },
];

vi.mock("../api/endpoints.js", () => ({
  getTrade: vi.fn((runId, tradeId) =>
    Promise.resolve({
      trade: {
        trade_id: tradeId,
        fees: 142,
        slippage: null,
        net_pnl: 1155,
        r_multiple: 0.64,
        entry_ts: 1725768600,
        exit_ts: 1725787500,
      },
      legs: [
        {
          option_type: "CE",
          action: "SELL",
          strike: 23750,
          entry_premium: 26.7,
          exit_premium: 11.2,
        },
        {
          option_type: "PE",
          action: "SELL",
          strike: 23550,
          entry_premium: 10.2,
          exit_premium: 6.4,
        },
      ],
      bars: [
        { time: 1725768600, open: 23600, high: 23650, low: 23580, close: 23620 },
      ],
    })
  ),
}));

function renderWithRouter(ui) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("TradeInspector", () => {
  it("renders header with current trade id and Open in Trades link", () => {
    renderWithRouter(
      <TradeInspector
        runId="test-run"
        trades={sampleTrades}
        selectedTradeId={157}
      />
    );

    expect(screen.getByText(/Trade inspector · #157 · 15m/i)).toBeInTheDocument();
    const link = screen.getByText(/Open in Trades/i);
    expect(link).toBeInTheDocument();
    expect(link.getAttribute("href")).toBe("/runs/test-run/trades?trade=157");
  });

  it("renders 6 buttons for the last 6 trades", () => {
    renderWithRouter(
      <TradeInspector
        runId="test-run"
        trades={sampleTrades}
        selectedTradeId={157}
      />
    );

    // sampleTrades has 7 items, last 6 are 152 to 157
    expect(screen.getByText("04 Aug")).toBeInTheDocument();
    expect(screen.getByText("11 Aug")).toBeInTheDocument();
    expect(screen.getByText("18 Aug")).toBeInTheDocument();
    expect(screen.getByText("25 Aug")).toBeInTheDocument();
    expect(screen.getByText("01 Sep")).toBeInTheDocument();
    expect(screen.getByText("08 Sep")).toBeInTheDocument();
  });

  it("calls onSelectTrade when a trade button is clicked", () => {
    const handleSelect = vi.fn();
    renderWithRouter(
      <TradeInspector
        runId="test-run"
        trades={sampleTrades}
        selectedTradeId={157}
        onSelectTrade={handleSelect}
      />
    );

    fireEvent.click(screen.getByText("01 Sep").closest("button"));
    expect(handleSelect).toHaveBeenCalledWith(156);
  });

  it("steps previous trade on '[' and next trade on ']'", () => {
    const handleSelect = vi.fn();
    renderWithRouter(
      <TradeInspector
        runId="test-run"
        trades={sampleTrades}
        selectedTradeId={155}
        onSelectTrade={handleSelect}
      />
    );

    // Press '[' -> should select previous (154)
    fireEvent.keyDown(window, { key: "[" });
    expect(handleSelect).toHaveBeenCalledWith(154);

    // Press ']' -> should select next (156)
    fireEvent.keyDown(window, { key: "]" });
    expect(handleSelect).toHaveBeenCalledWith(156);
  });

  it("does not navigate via '[' or ']' when input is focused", () => {
    const handleSelect = vi.fn();
    renderWithRouter(
      <div>
        <input data-testid="search-input" />
        <TradeInspector
          runId="test-run"
          trades={sampleTrades}
          selectedTradeId={155}
          onSelectTrade={handleSelect}
        />
      </div>
    );

    const input = screen.getByTestId("search-input");
    input.focus();

    fireEvent.keyDown(input, { key: "[" });
    expect(handleSelect).not.toHaveBeenCalled();
  });
});
