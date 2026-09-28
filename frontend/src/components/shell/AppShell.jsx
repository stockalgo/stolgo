import React, { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Rail } from "./Rail.jsx";
import { TopBar } from "./TopBar.jsx";
import { MinWidthNotice } from "./MinWidthNotice.jsx";
import { BreadcrumbProvider, useBreadcrumbs } from "../../context/BreadcrumbContext.jsx";

function AppShellInner() {
  const location = useLocation();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { crumbs: customCrumbs } = useBreadcrumbs();

  // Compute breadcrumb based on current path
  const path = location.pathname;
  let defaultCrumbs = <b>Library</b>;
  if (path.startsWith("/runs/")) {
    defaultCrumbs = (
      <span>
        Library / <b>Run</b>
      </span>
    );
  } else if (path.startsWith("/compare")) {
    defaultCrumbs = <b>Compare</b>;
  } else if (path.startsWith("/groups")) {
    defaultCrumbs = <b>Groups</b>;
  } else if (path === "/new") {
    defaultCrumbs = <b>New run</b>;
  }

  const effectiveCrumbs = customCrumbs || defaultCrumbs;

  return (
    <>
      <MinWidthNotice />
      <div className="app">
        <Rail />
        <div className="main">
          <TopBar crumbs={effectiveCrumbs} onOpenPalette={() => setPaletteOpen(true)} />
          <main className="page">
            <Outlet />
          </main>
        </div>
      </div>
    </>
  );
}

export function AppShell() {
  return (
    <BreadcrumbProvider>
      <AppShellInner />
    </BreadcrumbProvider>
  );
}
