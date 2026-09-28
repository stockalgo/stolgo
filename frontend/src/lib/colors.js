/**
 * Colour palette lookup for markets and series (UI plan §7.5).
 */

const colorCache = new Map();

function readCssVar(varName, fallback) {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return fallback;
  }
  if (colorCache.has(varName)) {
    return colorCache.get(varName);
  }
  const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  const effective = val || fallback;
  colorCache.set(varName, effective);
  return effective;
}

export function marketColor(markets = [], dte = []) {
  const m = Array.isArray(markets) && markets.length === 1 ? String(markets[0]).toLowerCase() : "";
  const d = Array.isArray(dte) && dte.length === 1 ? String(dte[0]) : "";

  if (m === "nifty" && (d === "0" || d === "1")) {
    return readCssVar(`--market-nifty-${d}`, d === "0" ? "#7cc4ff" : "#2f6fd6");
  }
  if (m === "sensex" && (d === "0" || d === "1")) {
    return readCssVar(`--market-sensex-${d}`, d === "0" ? "#ffb35c" : "#c4561b");
  }
  return readCssVar("--market-other", "#9aa3b2");
}

export function seriesColor(slotIndex) {
  const i = (slotIndex % 4) + 1;
  const fallbacks = {
    1: "#f5a524",
    2: "#5ab0ff",
    3: "#3ddc97",
    4: "#c792ff",
  };
  return readCssVar(`--series-${i}`, fallbacks[i]);
}
