import React from "react";

export function Banner({
  variant = "warn", // "warn" | "bad" | "info"
  children,
  action = null,
  className = "",
  style = {},
}) {
  let variantClass = "";
  let defaultStyle = {};

  if (variant === "bad") {
    variantClass = "banner--bad";
  } else if (variant === "info") {
    defaultStyle = {
      borderColor: "rgba(90, 176, 255, 0.35)",
      background: "var(--info-bg)",
      color: "var(--info)",
    };
  }

  const mergedStyle = { ...defaultStyle, ...style };

  return (
    <div className={`banner ${variantClass} ${className}`} style={mergedStyle}>
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{ flexShrink: 0 }}
      >
        {variant === "bad" || variant === "warn" ? (
          <>
            <path d="M12 3 2 20h20L12 3z" />
            <line x1="12" y1="10" x2="12" y2="14" />
            <line x1="12" y1="17" x2="12" y2="17.01" />
          </>
        ) : (
          <>
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="11" x2="12" y2="16" />
            <line x1="12" y1="8" x2="12" y2="8.01" />
          </>
        )}
      </svg>
      <div style={{ flex: 1 }}>{children}</div>
      {action && <div>{action}</div>}
    </div>
  );
}
