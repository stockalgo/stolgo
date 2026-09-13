let currentConfig = {
  currency: "INR",
  timeZone: "Asia/Kolkata",
  timeZoneName: "IST",
};

export function setFormattingConfig(config = {}) {
  if (config.currency) currentConfig.currency = config.currency;
  if (config.timeZone) {
    currentConfig.timeZone = config.timeZone;
    if (config.timeZone === "Asia/Kolkata") currentConfig.timeZoneName = "IST";
    else if (config.timeZone === "UTC") currentConfig.timeZoneName = "UTC";
    else if (config.timeZone === "America/New_York") currentConfig.timeZoneName = "ET";
    else currentConfig.timeZoneName = config.timeZone;
  }
}

export function getFormattingConfig() {
  return { ...currentConfig };
}

export function money(value, currency = currentConfig.currency) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "-";
  const curr = currency || currentConfig.currency || "INR";
  const locale = curr === "INR" ? "en-IN" : "en-US";
  const num = Number(value);
  return num.toLocaleString(locale, {
    style: "currency",
    currency: curr,
    maximumFractionDigits: Math.abs(num) < 100 && Math.abs(num) > 0 ? 2 : 0,
  });
}

export function signedMoney(value, currency = currentConfig.currency) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "-";
  const num = Number(value);
  return num >= 0 ? money(num, currency) : `-${money(Math.abs(num), currency)}`;
}

export function price(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "-";
  const locale = currentConfig.currency === "INR" ? "en-IN" : "en-US";
  return Number(value).toLocaleString(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function dateLabel(timestamp, timeZone = currentConfig.timeZone) {
  if (!timestamp) return "-";
  const tz = timeZone || currentConfig.timeZone || "Asia/Kolkata";
  const locale = currentConfig.currency === "INR" ? "en-IN" : "en-US";
  return new Date(timestamp * 1000).toLocaleString(locale, {
    month: "short",
    day: "2-digit",
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function timeLabel(timestamp, timeZone = currentConfig.timeZone) {
  if (!timestamp) return "-";
  const tz = timeZone || currentConfig.timeZone || "Asia/Kolkata";
  const locale = currentConfig.currency === "INR" ? "en-IN" : "en-US";
  return new Date(timestamp * 1000).toLocaleTimeString(locale, {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function percent(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "0.00%";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

export function metricValue(value, fmt) {
  if (fmt === "pct") return percent(value);
  if (fmt === "int") {
    const locale = currentConfig.currency === "INR" ? "en-IN" : "en-US";
    return Math.round(Number(value) || 0).toLocaleString(locale);
  }
  if (fmt === "r") return `${Number(value || 0).toFixed(2)}R`;
  if (fmt === "inr" || fmt === "money") return money(value);
  return Number(value || 0).toFixed(2);
}

export function metricTone(value, fmt) {
  if (fmt === "int") return "neutral";
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}
