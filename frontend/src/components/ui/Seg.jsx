import React from "react";

export function Seg({ options = [], value, onChange, className = "" }) {
  return (
    <div className={`seg ${className}`}>
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={String(opt.value)}
            type="button"
            className="seg__item"
            aria-selected={isSelected}
            disabled={opt.disabled}
            title={opt.tooltip || opt.title}
            onClick={() => !opt.disabled && onChange && onChange(opt.value)}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
