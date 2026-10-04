import React from "react";

export function Chip({
  children,
  selected = false,
  onClick,
  dotColor,
  className = "",
  style = {},
  as = "span",
  ...props
}) {
  const isButton = Boolean(onClick);
  const Component = as === "button" || isButton ? "button" : "span";

  const classes = [
    "chip",
    isButton ? "chip--button" : "",
    selected ? "chip--on" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Component
      type={Component === "button" ? "button" : undefined}
      className={classes}
      onClick={onClick}
      style={style}
      {...props}
    >
      {dotColor && <span className="dot" style={{ background: dotColor }} />}
      {children}
    </Component>
  );
}
