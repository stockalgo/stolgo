import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { RunHeader } from "../components/run/RunHeader.jsx";
import { RunTabs } from "../components/run/RunTabs.jsx";

const sampleRun = {
  id: "nifty-0dte-strangle-benchmark",
  name: "NIFTY 0-DTE Strangle Benchmark",
  status: "ok",
  status_reasons: [],
  markets: ["NIFTY"],
  structure: "short_strangle",
  dte: [0],
  capital: 180000,
  window: {
    start: "2023-09-14",
    end: "2026-09-08",
    sessions: 740,
  },
  metrics: {
    num_trades: 157,
    total_return: 0.169,
    sharpe: 0.73,
    net_pnl: 30331,
  },
  robustness: {
    p_net_positive: 0.88,
    net_without_top5: -6014,
  },
  has: {
    ohlcv: true,
    legs: true,
    audit: true,
  },
};

describe("RunHeader and RunTabs", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("renders RunHeader with title, chips, status badge and verdict", () => {
    render(
      <BrowserRouter>
        <RunHeader run={sampleRun} />
      </BrowserRouter>
    );

    expect(screen.getByText("NIFTY 0-DTE Strangle Benchmark")).toBeInTheDocument();
    expect(screen.getByText("Run · nifty-0dte-strangle-benchmark")).toBeInTheDocument();
    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("157 trades")).toBeInTheDocument();
    expect(screen.getByText("Capital ₹1,80,000")).toBeInTheDocument();
    expect(screen.getByText("14 Sep 2023 → 08 Sep 2026 · 740 sessions")).toBeInTheDocument();
    expect(screen.getByText("EDGE · FRAGILE")).toBeInTheDocument();
  });

  it("renders RunTabs with links and action buttons", () => {
    const onToast = vi.fn();

    render(
      <BrowserRouter>
        <RunTabs run={sampleRun} onToast={onToast} />
      </BrowserRouter>
    );

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Trades")).toBeInTheDocument();
    expect(screen.getByText("157")).toBeInTheDocument();
    expect(screen.getByText("Diagnostics")).toBeInTheDocument();
    expect(screen.getByText("Add to compare")).toBeInTheDocument();
    expect(screen.getByText("Audit report")).toBeInTheDocument();
    expect(screen.getByText("Trades CSV")).toBeInTheDocument();

    // Clicking Add to compare
    fireEvent.click(screen.getByText("Add to compare"));
    expect(onToast).toHaveBeenCalledWith("Added nifty-0dte-strangle-benchmark to compare");
    expect(JSON.parse(sessionStorage.getItem("stolgo.compare"))).toEqual([
      "nifty-0dte-strangle-benchmark",
    ]);

    // Clicking Add to compare again
    fireEvent.click(screen.getByText("Add to compare"));
    expect(onToast).toHaveBeenCalledWith("Already in compare");
  });
});
