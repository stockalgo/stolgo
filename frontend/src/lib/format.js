/**
 * Formatting library for Stolgo UI (UI plan §5).
 * The only place numbers become strings.
 */

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function isNil(v) {
  return v === null || v === undefined || (typeof v === "number" && Number.isNaN(v));
}

function formatIndianNumber(num, dec = 0) {
  return new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  }).format(num);
}

export function inr(v, { signed = false, dec = 0 } = {}) {
  if (isNil(v)) return "—";
  const num = Number(v);
  if (Math.abs(num) < 1e-9) return "₹0";
  const rounded = Math.round(num);
  if (num < 0) {
    return `\u2212₹${formatIndianNumber(Math.abs(rounded), dec)}`;
  }
  const prefix = signed ? "+₹" : "₹";
  return `${prefix}${formatIndianNumber(rounded, dec)}`;
}

export function inrCompact(v) {
  if (isNil(v)) return "—";
  const num = Number(v);
  if (Math.abs(num) < 1e-9) return "₹0";

  const isNeg = num < 0;
  const abs = Math.abs(num);
  const prefix = isNeg ? "\u2212₹" : "₹";

  let val = abs;
  let unit = "";

  if (abs >= 1e7) {
    val = abs / 1e7;
    unit = "Cr";
  } else if (abs >= 1e5) {
    val = abs / 1e5;
    unit = "L";
  } else if (abs >= 1e3) {
    val = abs / 1e3;
    unit = "k";
  } else {
    return inr(v);
  }

  const str = val % 1 === 0 ? val.toString() : val.toFixed(1).replace(/\.0$/, "");
  return `${prefix}${str}${unit}`;
}

export function pct(v, { dec = 1, signed = true } = {}) {
  if (isNil(v)) return "—";
  const num = Number(v) * 100;
  const fixed = num.toFixed(dec);
  if (Math.abs(Number(fixed)) < 1e-9) {
    return `${(0).toFixed(dec)}%`;
  }
  if (num < 0) {
    return `\u2212${Math.abs(num).toFixed(dec)}%`;
  }
  const prefix = signed ? "+" : "";
  return `${prefix}${num.toFixed(dec)}%`;
}

export function ratio(v, dec = 2) {
  if (isNil(v)) return "—";
  const num = Number(v);
  const fixed = num.toFixed(dec);
  if (Math.abs(Number(fixed)) < 1e-9) {
    return (0).toFixed(dec);
  }
  if (num < 0) {
    return `\u2212${Math.abs(num).toFixed(dec)}`;
  }
  return fixed;
}

export function count(v) {
  if (isNil(v)) return "—";
  return new Intl.NumberFormat("en-US").format(v);
}

export function sessions(v) {
  if (isNil(v)) return "—";
  return `${count(v)} sessions`;
}

export function rmult(v) {
  if (isNil(v)) return "—";
  const num = Number(v);
  const fixed = Math.abs(num).toFixed(2);
  if (Math.abs(num) < 1e-9) {
    return "0.00R";
  }
  if (num < 0) {
    return `\u2212${fixed}R`;
  }
  return `+${fixed}R`;
}

export function premium(v) {
  if (isNil(v)) return "—";
  return Number(v).toFixed(1);
}

export function level(v) {
  if (isNil(v)) return "—";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(v);
}

export function dateIST(epochSec) {
  if (isNil(epochSec)) return "—";
  const date = new Date(epochSec * 1000);
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).formatToParts(date);
  const day = parts.find((p) => p.type === "day")?.value;
  const month = parts.find((p) => p.type === "month")?.value;
  const year = parts.find((p) => p.type === "year")?.value;
  return `${day} ${month} ${year}`;
}

export function timeIST(val) {
  if (isNil(val)) return "—";
  let date;
  if (typeof val === "number") {
    date = new Date(val * 1000);
  } else if (!isNaN(Number(val))) {
    date = new Date(Number(val) * 1000);
  } else {
    date = new Date(val);
  }
  if (isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function sessionLabel(sessionDate) {
  if (!sessionDate) return "—";
  const parts = String(sessionDate).slice(0, 10).split("-");
  if (parts.length !== 3) return sessionDate;
  const [year, month, day] = parts;
  const mIdx = parseInt(month, 10) - 1;
  return `${day} ${MONTH_NAMES[mIdx] || month} ${year}`;
}

export function sessionShort(sessionDate) {
  if (!sessionDate) return "—";
  const parts = String(sessionDate).slice(0, 10).split("-");
  if (parts.length < 3) return sessionDate;
  const [, month, day] = parts;
  const mIdx = parseInt(month, 10) - 1;
  return `${day} ${MONTH_NAMES[mIdx] || month}`;
}

export function formatMetric(key, value, defs = []) {
  const def = Array.isArray(defs) ? defs.find((d) => d.key === key) : null;
  if (!def) {
    return isNil(value) ? "—" : String(value);
  }
  switch (def.unit) {
    case "inr":
      return inr(value, { signed: def.better !== "lower" });
    case "fraction":
      return pct(value);
    case "ratio":
      return ratio(value, def.decimals ?? 2);
    case "count":
      return count(value);
    case "sessions":
      return sessions(value);
    case "r":
      return rmult(value);
    default:
      return isNil(value) ? "—" : String(value);
  }
}
