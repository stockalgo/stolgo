import React, { useState, useEffect } from "react";
import { Button } from "../ui/Button.jsx";

export function GoToDateDialog({ isOpen, onClose, onSelectDate }) {
  const [date, setDate] = useState("");

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (date) {
      onSelectDate(date);
      onClose();
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        className="panel"
        style={{
          width: "320px",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="panel__head" style={{ margin: 0 }}>
          <span className="eyebrow">Go to date</span>
        </div>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <input
            type="date"
            className="input mono"
            autoFocus
            value={date}
            onChange={(e) => setDate(e.target.value)}
            style={{ width: "100%" }}
            required
          />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
            <Button size="sm" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" variant="primary" type="submit">
              Jump
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
