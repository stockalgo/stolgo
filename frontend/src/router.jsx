import React from "react";
import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell.jsx";
import { LibraryPage } from "./pages/LibraryPage.jsx";
import { RunLayout } from "./pages/RunLayout.jsx";
import { RunOverviewPage } from "./pages/RunOverviewPage.jsx";
import { RunTradesPage } from "./pages/RunTradesPage.jsx";
import { RunDiagnosticsPage } from "./pages/RunDiagnosticsPage.jsx";
import { NotFoundPage } from "./pages/NotFoundPage.jsx";

const ComparePage = React.lazy(() =>
  import("./pages/ComparePage.jsx").then((m) => ({ default: m.ComparePage }))
);
const GroupsPage = React.lazy(() =>
  import("./pages/GroupsPage.jsx").then((m) => ({ default: m.GroupsPage }))
);
const GroupPage = React.lazy(() =>
  import("./pages/GroupPage.jsx").then((m) => ({ default: m.GroupPage }))
);
const RunChartPage = React.lazy(() =>
  import("./pages/RunChartPage.jsx").then((m) => ({ default: m.RunChartPage }))
);
const NewRunPage = React.lazy(() =>
  import("./pages/NewRunPage.jsx").then((m) => ({ default: m.NewRunPage }))
);
const KitPage = React.lazy(() =>
  import("./pages/KitPage.jsx").then((m) => ({ default: m.KitPage }))
);

const withSuspense = (Component) => (
  <React.Suspense fallback={<div style={{ padding: "24px", color: "var(--text-muted, #888)" }}>Loading…</div>}>
    <Component />
  </React.Suspense>
);

const isDev = Boolean(typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <LibraryPage /> },
      {
        path: "runs/:runId",
        element: <RunLayout />,
        children: [
          { index: true, element: <RunOverviewPage /> },
          { path: "trades", element: <RunTradesPage /> },
          { path: "diagnostics", element: <RunDiagnosticsPage /> },
        ],
      },
      { path: "compare", element: withSuspense(ComparePage) },
      { path: "groups", element: withSuspense(GroupsPage) },
      { path: "groups/:groupId", element: withSuspense(GroupPage) },
      { path: "new", element: withSuspense(NewRunPage) },
      ...(isDev ? [{ path: "_kit", element: withSuspense(KitPage) }] : []),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "runs/:runId/chart",
    element: withSuspense(RunChartPage),
  },
]);

