import React from "react";

export function Panel({
  title,
  eyebrow,
  headerRight,
  footer,
  children,
  className = "",
  style = {},
}) {
  const hasHead = title || eyebrow || headerRight;

  return (
    <section className={`panel ${className}`} style={style}>
      {hasHead && (
        <div className="panel__head">
          <div>
            {eyebrow && <span className="eyebrow">{eyebrow}</span>}
            {title && (
              <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-1)" }}>
                {title}
              </div>
            )}
          </div>
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      {children}
      {footer && <div className="panel__foot">{footer}</div>}
    </section>
  );
}
