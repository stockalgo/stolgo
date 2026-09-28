import React, { useState, useRef } from "react";

export function Tooltip({ content, children, delay = 120, className = "" }) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef(null);

  if (!content) return children;

  const onEnter = () => {
    timerRef.current = setTimeout(() => {
      setVisible(true);
    }, delay);
  };

  const onLeave = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    setVisible(false);
  };

  return (
    <span
      className={`tooltip-trigger ${className}`}
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      {children}
      {visible && (
        <div
          className="tooltip"
          role="tooltip"
          style={{
            position: "absolute",
            bottom: "100%",
            left: "50%",
            transform: "translateX(-50%)",
            marginBottom: "6px",
            zIndex: 100,
            pointerEvents: "none",
          }}
        >
          {content}
        </div>
      )}
    </span>
  );
}
