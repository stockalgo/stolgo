/**
 * Fetch client wrapper with custom ApiError.
 */

export class ApiError extends Error {
  constructor(status, detail, path) {
    super(`API Error ${status}: ${detail || path}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.path = path;
  }
}

export async function get(path) {
  const url = path.startsWith("/") ? `/api${path}` : `/api/${path}`;
  const res = await fetch(url);
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body.detail || "";
    } catch {
      detail = await res.text();
    }
    throw new ApiError(res.status, detail, path);
  }
  return res.json();
}
