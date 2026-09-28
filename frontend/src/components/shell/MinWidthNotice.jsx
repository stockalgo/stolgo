import React from "react";

export function MinWidthNotice() {
  return (
    <div className="min-width-notice" role="alert">
      <h2>Screen width too small</h2>
      <p>Stolgo needs a window at least 1024 px wide.</p>
    </div>
  );
}
