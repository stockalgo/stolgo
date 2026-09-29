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

export const COLORS = {
  pos: "#3ddc97",
  neg: "#e5484d",
  negText: "#ff7a7e",
  accent: "#f5a524",
  info: "#5ab0ff",
  purple: "#c792ff",
  text1: "#e6e8ea",
  text2: "#c9ced3",
  text3: "#a7aeb5",
  textMuted: "#8a929b",
  textFaint: "#6b737c",
  line: "#1b1f24",
  lineStrong: "#2a3037",
  bgApp: "#0a0c0e",
  bgPanel: "#0d1013",
  bgRaised: "#14181c",
  marketOther: "#9aa3b2",
  marketNifty0: "#7cc4ff",
  marketNifty1: "#2f6fd6",
  marketSensex0: "#ffb35c",
  marketSensex1: "#c4561b",
};

