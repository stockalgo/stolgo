import React from "react";
import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell.jsx";
import { LibraryPage } from "./pages/LibraryPage.jsx";
import { RunLayout } from "./pages/RunLayout.jsx";
import { RunOverviewPage } from "./pages/RunOverviewPage.jsx";
import { RunTradesPage } from "./pages/RunTradesPage.jsx";
import { RunDiagnosticsPage } from "./pages/RunDiagnosticsPage.jsx";
import { RunChartPage } from "./pages/RunChartPage.jsx";
import { ComparePage } from "./pages/ComparePage.jsx";
import { GroupsPage } from "./pages/GroupsPage.jsx";
import { GroupPage } from "./pages/GroupPage.jsx";
import { NewRunPage } from "./pages/NewRunPage.jsx";
import { KitPage } from "./pages/KitPage.jsx";
import { NotFoundPage } from "./pages/NotFoundPage.jsx";

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
      { path: "compare", element: <ComparePage /> },
      { path: "groups", element: <GroupsPage /> },
      { path: "groups/:groupId", element: <GroupPage /> },
      { path: "new", element: <NewRunPage /> },
      { path: "_kit", element: <KitPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "runs/:runId/chart",
    element: <RunChartPage />,
  },
]);
