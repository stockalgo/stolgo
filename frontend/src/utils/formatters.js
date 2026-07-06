export function money(value) {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

export function price(value) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function dateLabel(timestamp) {
  return new Date(timestamp * 1000).toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    timeZone: "America/New_York",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function timeLabel(timestamp) {
  return new Date(timestamp * 1000).toLocaleTimeString("en-US", {
    timeZone: "America/New_York",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function percent(value) {
  return `${(value * 100).toFixed(2)}%`;
}

export function metricValue(value, fmt) {
  if (fmt === "pct") return percent(value);
  if (fmt === "int") return Math.round(value).toLocaleString("en-US");
  if (fmt === "r") return `${Number(value).toFixed(2)}R`;
  return Number(value).toFixed(2);
}

export function metricTone(value, fmt) {
  if (fmt === "int") return "neutral";
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}
