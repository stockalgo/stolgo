import React from "react";

export function Tabs({ tabs = [], activeTab, onChange, rightSlot = null, className = "" }) {
  return (
    <div className={`tabs-container ${className}`} style={{ display: "flex", alignItems: "center" }}>
      <div className="tabs">
        {tabs.map((tab) => {
          const isSelected = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              className="tab"
              aria-selected={isSelected}
              onClick={() => onChange && onChange(tab.id)}
            >
              {tab.label}
              {tab.count !== undefined && tab.count !== null && (
                <span className="count">{tab.count}</span>
              )}
            </button>
          );
        })}
      </div>
      {rightSlot && <div style={{ marginLeft: "auto", display: "flex", gap: "8px" }}>{rightSlot}</div>}
    </div>
  );
}
