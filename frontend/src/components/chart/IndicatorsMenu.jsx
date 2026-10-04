import React, { useState, useRef, useEffect } from "react";
import { COLORS } from "../../lib/colors.js";

export function IndicatorsMenu({ activeIndicators = {}, onToggleIndicator, hasVolume = false }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [open]);

  const indicators = [
    { key: "ema20", label: "EMA 20", color: COLORS.info },
    { key: "ema50", label: "EMA 50", color: COLORS.accent },
    { key: "ema200", label: "EMA 200", color: COLORS.purple },
    { key: "sma20", label: "SMA 20", color: COLORS.pos },
    { key: "sma50", label: "SMA 50", color: COLORS.negText },
    { key: "bollinger", label: "Bollinger Bands (20, 2)", color: COLORS.marketNifty0 },
    { key: "rsi", label: "RSI (14)", color: COLORS.text1 },
    ...(hasVolume ? [{ key: "volume_ma", label: "Volume MA (20)", color: COLORS.marketOther }] : []),
  ];

  const activeCount = Object.values(activeIndicators).filter(Boolean).length;

  return (
    <div style={{ position: "relative" }} ref={ref}>
      <button
        className="btn btn--sm"
        style={{ marginLeft: "4px" }}
        onClick={() => setOpen((prev) => !prev)}
      >
        Indicators {activeCount > 0 && `(${activeCount})`}
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            background: "var(--bg-overlay)",
            border: "1px solid var(--line)",
            borderRadius: "6px",
            padding: "8px",
            minWidth: "200px",
            zIndex: 100,
            boxShadow: "0 6px 16px rgba(0,0,0,0.5)",
            display: "flex",
            flexDirection: "column",
            gap: "4px",
          }}
        >
          <div className="eyebrow" style={{ padding: "4px 8px 6px" }}>
            Overlay Indicators
          </div>
          {indicators.map((ind) => {
            const isChecked = Boolean(activeIndicators[ind.key]);
            return (
              <label
                key={ind.key}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "12px",
                  color: isChecked ? "var(--text-1)" : "var(--text-2)",
                  background: isChecked ? "rgba(255,255,255,0.04)" : "transparent",
                }}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => onToggleIndicator(ind.key)}
                  style={{ accentColor: "var(--accent)" }}
                />
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: ind.color,
                    flexShrink: 0,
                  }}
                />
                <span>{ind.label}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
