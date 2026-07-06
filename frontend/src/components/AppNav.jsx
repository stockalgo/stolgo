import { navItems } from "../data/constants";

export function AppNav({ activePage, exportState, onExport, onNavigate, onToggleTheme, theme }) {
  return (
    <header className="app-nav">
      <button className="brand-lockup" type="button" onClick={() => onNavigate("library")}>
        <span className="status-orb" />
        <div>
          <b>Stolgo</b>
          <span>Backtesting workspace</span>
        </div>
      </button>
      <nav className="page-tabs" aria-label="Main pages">
        {navItems.map(([id, label]) => (
          <button className={activePage === id ? "active" : ""} key={id} type="button" onClick={() => onNavigate(id)}>
            {label}
          </button>
        ))}
      </nav>
      <div className="header-actions">
        <button className="ghost-button" type="button" onClick={onExport}>
          {exportState}
        </button>
        <button className="theme-toggle" type="button" onClick={onToggleTheme}>
          {theme === "light" ? "Light" : "Dark"}
        </button>
      </div>
    </header>
  );
}
