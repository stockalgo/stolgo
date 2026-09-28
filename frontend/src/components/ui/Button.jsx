import React from "react";

export function Button({
  children,
  variant = "default", // "primary" | "ghost" | "default"
  size = "default", // "sm" | "default"
  disabled = false,
  icon = null,
  onClick,
  className = "",
  title,
  type = "button",
  ...props
}) {
  const classes = [
    "btn",
    variant === "primary" ? "btn--primary" : "",
    variant === "ghost" ? "btn--ghost" : "",
    size === "sm" ? "btn--sm" : "",
    icon && !children ? "icon-btn" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled}
      onClick={onClick}
      title={title}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
