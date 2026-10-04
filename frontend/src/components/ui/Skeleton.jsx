import React from "react";

export function Skeleton({ width, height, className = "", style = {} }) {
  const mergedStyle = {
    ...(width ? { width } : {}),
    ...(height ? { height } : {}),
    ...style,
  };
  return <div className={`skeleton ${className}`} style={mergedStyle} />;
}
