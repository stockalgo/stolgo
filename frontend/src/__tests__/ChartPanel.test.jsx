import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ChartPanel } from "../components/chart/ChartPanel.jsx";

const sampleRunOhlcv = {
  id: "nifty-benchmark",
  markets: ["NIFTY"],
  has: { ohlcv: true },
};

const sampleRunNoOhlcv = {
  id: "validated-timing-static",
  markets: ["SENSEX"],
  has: { ohlcv: false },
};

function renderWithRouter(ui) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("ChartPanel", () => {
  it("renders with Price view by default when has.ohlcv is true", () => {
    renderWithRouter(<ChartPanel run={sampleRunOhlcv} />);

    const priceBtn = screen.getByText("Price · candles");
    const equityBtn = screen.getByText("Equity · drawdown");

    expect(priceBtn).toBeInTheDocument();
    expect(equityBtn).toBeInTheDocument();
    expect(priceBtn).toHaveAttribute("aria-selected", "true");
    expect(priceBtn).not.toBeDisabled();
  });

  it("defaults to Equity view and disables Price view when has.ohlcv is false", () => {
    renderWithRouter(<ChartPanel run={sampleRunNoOhlcv} />);

    const priceBtn = screen.getByText("Price · candles");
    const equityBtn = screen.getByText("Equity · drawdown");

    expect(priceBtn).toBeDisabled();
    expect(equityBtn).toHaveAttribute("aria-selected", "true");
  });

  it("switches to Equity view when Equity segment button is clicked", () => {
    renderWithRouter(<ChartPanel run={sampleRunOhlcv} />);

    const equityBtn = screen.getByText("Equity · drawdown");
    fireEvent.click(equityBtn);

    expect(screen.getByText("Top 5 trades")).toBeInTheDocument();
    expect(screen.getByText("1Y")).toBeInTheDocument();
    expect(screen.getByText("ALL")).toBeInTheDocument();
  });
});
