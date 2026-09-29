import React, { createContext, useContext, useState, useRef, useCallback } from "react";

const ToastContext = createContext({
  showToast: () => {},
});

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timerRef = useRef(null);

  const showToast = useCallback((msg) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    setToast(msg);
    timerRef.current = setTimeout(() => {
      setToast(null);
      timerRef.current = null;
    }, 2500); // 2.5s per §9
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && (
        <div
          className="toast"
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            zIndex: 9999,
          }}
        >
          {toast}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
