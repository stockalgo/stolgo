import React, { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { RunsTable } from "../components/library/RunsTable.jsx";

const sampleRuns = [
  {
    id: "run-a",
    name: "Strategy Alpha",
    markets: ["NIFTY"],
    dte: [0],
    status: "ok",
    metrics: { num_trades: 120, total_return: 0.12, cagr: 0.04, sharpe: 0.85, max_drawdown: -0.05, profit_factor: 1.5 },
  },
  {
    id: "run-b",
    name: "Strategy Beta",
    markets: ["SENSEX"],
    dte: [0],
    status: "low_sample",
    metrics: { num_trades: 50, total_return: 0.18, cagr: 0.06, sharpe: 1.25, max_drawdown: -0.03, profit_factor: 2.1 },
  },
  {
    id: "run-c",
    name: "Strategy Gamma",
    markets: ["NIFTY"],
    dte: [1],
    status: "ok",
    metrics: { num_trades: 200, total_return: 0.08, cagr: 0.02, sharpe: 0.45, max_drawdown: -0.09, profit_factor: 1.1 },
  },
  {
    id: "run-d",
    name: "Strategy Delta",
    markets: ["SENSEX"],
    dte: [1],
    status: "data_issues",
    metrics: { num_trades: 150, total_return: 0.15, cagr: 0.05, sharpe: 0.70, max_drawdown: -0.07, profit_factor: 1.3 },
  },
  {
    id: "run-e",
    name: "Strategy Epsilon",
    markets: ["NIFTY"],
    dte: [0],
    status: "ok",
    metrics: { num_trades: 110, total_return: 0.10, cagr: 0.03, sharpe: 0.60, max_drawdown: -0.06, profit_factor: 1.2 },
  },
];

function renderWithRouter(ui) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("RunsTable", () => {
  it("sorts by Sharpe descending by default", () => {
    renderWithRouter(
      <RunsTable
        runs={sampleRuns}
        sortKey="sharpe"
        sortDir="desc"
      />
    );

    // Order should be: Beta (1.25), Alpha (0.85), Delta (0.70), Epsilon (0.60), Gamma (0.45)
    const rows = screen.getAllByRole("row").slice(1); // exclude header row
    expect(rows[0]).toHaveTextContent("Strategy Beta");
    expect(rows[1]).toHaveTextContent("Strategy Alpha");
    expect(rows[2]).toHaveTextContent("Strategy Delta");
    expect(rows[3]).toHaveTextContent("Strategy Epsilon");
    expect(rows[4]).toHaveTextContent("Strategy Gamma");
  });

  it("clicking the Trades header sorts asc then desc", () => {
    function ControlledTable() {
      const [sort, setSort] = useState({ key: "sharpe", dir: "desc" });
      return (
        <RunsTable
          runs={sampleRuns}
          sortKey={sort.key}
          sortDir={sort.dir}
          onSortChange={(k, d) => setSort({ key: k, dir: d })}
        />
      );
    }

    renderWithRouter(<ControlledTable />);

    const tradesHeader = screen.getByText("Trades");

    // First click on Trades: defaults to desc
    fireEvent.click(tradesHeader);
    let rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Strategy Gamma"); // 200 trades
    expect(rows[4]).toHaveTextContent("Strategy Beta"); // 50 trades

    // Second click on Trades: toggles to asc
    fireEvent.click(tradesHeader);
    rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Strategy Beta"); // 50 trades
    expect(rows[4]).toHaveTextContent("Strategy Gamma"); // 200 trades

    // Third click on Trades: toggles back to desc
    fireEvent.click(tradesHeader);
    rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Strategy Gamma"); // 200 trades
    expect(rows[4]).toHaveTextContent("Strategy Beta"); // 50 trades
  });

  it("refuses the 5th selection and calls onMaxSelectedNotice", () => {
    const onToggleSelect = vi.fn();
    const onMaxSelectedNotice = vi.fn();

    const selectedIds = ["run-a", "run-b", "run-c", "run-d"];

    renderWithRouter(
      <RunsTable
        runs={sampleRuns}
        selectedIds={selectedIds}
        onToggleSelect={onToggleSelect}
        onMaxSelectedNotice={onMaxSelectedNotice}
      />
    );

    // Try to select the 5th run ("run-e")
    const checkboxE = screen.getByLabelText("Select Strategy Epsilon");
    fireEvent.click(checkboxE);

    expect(onMaxSelectedNotice).toHaveBeenCalled();
    expect(onToggleSelect).not.toHaveBeenCalledWith("run-e");
  });
});
