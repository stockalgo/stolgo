import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState.jsx";

export function NotFoundPage() {
  useEffect(() => {
    document.title = "Not Found · Stolgo";
  }, []);
  return (
    <div style={{ padding: "48px 0" }}>
      <EmptyState
        title="Page not found"
        description="The page you requested does not exist or may have been moved."
        action={
          <Link to="/" className="btn btn--primary">
            Go to Library
          </Link>
        }
      />
    </div>
  );
}
