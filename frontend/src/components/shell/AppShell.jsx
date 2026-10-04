import React, { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Rail } from "./Rail.jsx";
import { TopBar } from "./TopBar.jsx";
import { MinWidthNotice } from "./MinWidthNotice.jsx";
import { CommandPalette } from "./CommandPalette.jsx";
import { BreadcrumbProvider, useBreadcrumbs } from "../../context/BreadcrumbContext.jsx";
import { ToastProvider } from "../../context/ToastContext.jsx";

function AppShellInner() {
  const location = useLocation();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { crumbs: customCrumbs } = useBreadcrumbs();

  // Global ⌘K / Ctrl+K shortcut
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

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
          <TopBar
            crumbs={effectiveCrumbs}
            onOpenPalette={() => setPaletteOpen(true)}
          />
          <main className="page">
            <Outlet />
          </main>
        </div>
      </div>
      <CommandPalette
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </>
  );
}

export function AppShell() {
  return (
    <BreadcrumbProvider>
      <ToastProvider>
        <AppShellInner />
      </ToastProvider>
    </BreadcrumbProvider>
  );
}
