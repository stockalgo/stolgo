import { useEffect, useState } from "react";
import { AppNav } from "./components/AppNav";
import { getRun, getRunSeries, getRunTrades, listRuns, listSweeps } from "./data/client";
import { ComparePage } from "./pages/ComparePage";
import { NewBacktestPage } from "./pages/NewBacktestPage";
import { OptimizationPage } from "./pages/OptimizationPage";
import { ReportsPage } from "./pages/ReportsPage";
import { StrategyDetailPage } from "./pages/StrategyDetailPage";
import { StrategyLibraryPage } from "./pages/StrategyLibraryPage";

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
    setExportState("Queued");
    window.setTimeout(() => setExportState("Export"), 1800);
  };

  const pages = {
    library: <StrategyLibraryPage loading={loadingRuns} onOpenDetail={navigateToDetail} runs={runs} />,
    detail: (
      <StrategyDetailPage
        data={data}
        detail={detail}
        loading={loadingDetail}
        runs={runs}
        selectedRunId={selectedRunId}
        selectedTrade={selectedTrade}
        setSelectedRunId={setSelectedRunId}
        setSelectedTrade={setSelectedTrade}
        theme={theme}
      />
    ),
    new: <NewBacktestPage />,
    compare: <ComparePage onOpenDetail={navigateToDetail} runs={runs} />,
    optimize: <OptimizationPage sweeps={sweeps} />,
    reports: <ReportsPage runs={runs} />,
  };

  return (
    <main className={`app-shell ${theme}`}>
      <AppNav
        activePage={activePage}
        exportState={exportState}
        onExport={handleExport}
        onNavigate={setActivePage}
        onToggleTheme={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
        theme={theme}
      />
      {error && <div className="app-error">API error: {error}</div>}
      <div className="page-stage">{pages[activePage]}</div>
    </main>
  );
}
