import React, { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Rail } from "./Rail.jsx";
import { TopBar } from "./TopBar.jsx";
import { MinWidthNotice } from "./MinWidthNotice.jsx";

export function AppShell() {
  const location = useLocation();
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Compute breadcrumb based on current path
  const path = location.pathname;
  let crumbs = <b>Library</b>;
  if (path.startsWith("/runs/")) {
    crumbs = (
      <span>
        Library / <b>Run</b>
      </span>
    );
  } else if (path.startsWith("/compare")) {
    crumbs = <b>Compare</b>;
  } else if (path.startsWith("/groups")) {
    crumbs = <b>Groups</b>;
  } else if (path === "/new") {
    crumbs = <b>New run</b>;
  }

  return (
    <>
      <MinWidthNotice />
      <div className="app">
        <Rail />
        <div className="main">
          <TopBar crumbs={crumbs} onOpenPalette={() => setPaletteOpen(true)} />
          <main className="page">
            <Outlet />
          </main>
        </div>
      </div>
    </>
  );
}
