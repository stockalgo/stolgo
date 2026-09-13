import { useEffect, useState } from "react";
import { AppNav } from "./components/AppNav";
import { getRun, getRunSeries, getRunTrades, listRuns, listSweeps } from "./data/client";
import { ComparePage } from "./pages/ComparePage";
import { NewBacktestPage } from "./pages/NewBacktestPage";
import { OptimizationPage } from "./pages/OptimizationPage";
import { ReportsPage } from "./pages/ReportsPage";
import { StrategyDetailPage } from "./pages/StrategyDetailPage";
import { StrategyLibraryPage } from "./pages/StrategyLibraryPage";
import { setFormattingConfig } from "./utils/formatters";

const emptyData = { candles: [], volume: [], equity: [], drawdown: [], trades: [] };

export function App() {
  const [activePage, setActivePage] = useState("library");
  const [exportState, setExportState] = useState("Export");
  const [runs, setRuns] = useState([]);
  const [sweeps, setSweeps] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [data, setData] = useState(emptyData);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState("light");
  const [currency, setCurrency] = useState("INR");
  const [timeZone, setTimeZone] = useState("Asia/Kolkata");

  const handleToggleCurrency = () => {
    const next = currency === "INR" ? "USD" : "INR";
    setCurrency(next);
    setFormattingConfig({ currency: next });
  };

  const handleToggleTimeZone = () => {
    const zones = ["Asia/Kolkata", "UTC", "America/New_York"];
    const next = zones[(zones.indexOf(timeZone) + 1) % zones.length];
    setTimeZone(next);
    setFormattingConfig({ timeZone: next });
  };

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoadingRuns(true);
      try {
        const [runRows, sweepRows] = await Promise.all([listRuns(), listSweeps()]);
        if (!alive) return;
        setRuns(runRows);
        setSweeps(sweepRows);
        setSelectedRunId((current) => current ?? runRows[0]?.id ?? null);
        setError("");
      } catch (loadError) {
        if (alive) setError(loadError.message);
      } finally {
        if (alive) setLoadingRuns(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId) return undefined;
    let alive = true;
    async function loadDetail() {
      setLoadingDetail(true);
      setSelectedTrade(null);
      try {
        const runDetail = await getRun(selectedRunId);
        const [seriesResult, tradesResult] = await Promise.allSettled([
          getRunSeries(selectedRunId),
          getRunTrades(selectedRunId),
        ]);
        if (!alive) return;
        const series = seriesResult.status === "fulfilled" ? seriesResult.value : emptyData;
        const trades = tradesResult.status === "fulfilled" ? tradesResult.value : [];
        const nextData = {
          candles: series.candles ?? [],
          volume: series.volume ?? [],
          equity: series.equity ?? [],
          drawdown: series.drawdown ?? [],
          trades,
        };
        setDetail(runDetail);
        setData(nextData);
        setSelectedTrade(trades[0] ?? null);
        setError("");
      } catch (loadError) {
        if (!alive) return;
        setDetail(null);
        setData(emptyData);
        setError(loadError.message);
      } finally {
        if (alive) setLoadingDetail(false);
      }
    }
    loadDetail();
    return () => {
      alive = false;
    };
  }, [selectedRunId]);

  const navigateToDetail = (runId) => {
    setSelectedRunId(runId);
    setActivePage("detail");
  };

  const handleExport = () => {
    if (!data.trades || data.trades.length === 0) {
      setExportState("No trades");
      setTimeout(() => setExportState("Export"), 1500);
      return;
    }
    const headers = [
      "id",
      "entry_time",
      "exit_time",
      "side",
      "entry_premium",
      "exit_premium",
      "qty",
      "gross_pnl",
      "costs",
      "net_pnl",
      "r_multiple",
      "tag",
    ];
    const rows = data.trades.map((t) => [
      t.id,
      new Date(t.entryTime * 1000).toISOString(),
      new Date(t.exitTime * 1000).toISOString(),
      t.side,
      t.entryPrice,
      t.exitPrice,
      t.qty,
      t.grossPnl ?? t.pnl,
      t.commission ?? 0,
      t.pnl,
      t.r,
      t.tag || "",
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${selectedRunId || "trades"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setExportState("Downloaded!");
    window.setTimeout(() => setExportState("Export"), 2000);
  };

  const pages = {
    library: <StrategyLibraryPage loading={loadingRuns} onOpenDetail={navigateToDetail} runs={runs} />,
    detail: (
      <StrategyDetailPage
        currency={currency}
        data={data}
        detail={detail}
        loading={loadingDetail}
        runs={runs}
        selectedRunId={selectedRunId}
        selectedTrade={selectedTrade}
        setSelectedRunId={setSelectedRunId}
        setSelectedTrade={setSelectedTrade}
        theme={theme}
        timeZone={timeZone}
      />
    ),
    new: <NewBacktestPage />,
    compare: <ComparePage onOpenDetail={navigateToDetail} runs={runs} />,
    optimize: <OptimizationPage sweeps={sweeps} />,
    reports: <ReportsPage onOpenDetail={navigateToDetail} runs={runs} />,
  };

  return (
    <main className={`app-shell ${theme}`}>
      <AppNav
        activePage={activePage}
        currency={currency}
        exportState={exportState}
        onExport={handleExport}
        onNavigate={setActivePage}
        onToggleCurrency={handleToggleCurrency}
        onToggleTheme={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
        onToggleTimeZone={handleToggleTimeZone}
        theme={theme}
        timeZone={timeZone}
      />
      {error && <div className="app-error">API error: {error}</div>}
      <div className="page-stage">{pages[activePage]}</div>
    </main>
  );
}
