const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function get(path) {
  const response = await fetch(`${BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${path}`);
  }
  return response.json();
}

function items(payload) {
  return Array.isArray(payload) ? payload : payload.items ?? [];
}

export const listRuns = async () => items(await get("/runs"));
export const getRun = (id) => get(`/runs/${id}`);
export const getRunSeries = (id) => get(`/runs/${id}/series`);
export const getRunTrades = (id) => get(`/runs/${id}/trades`);
export const listSweeps = async () => items(await get("/sweeps"));
export const getSweep = (id) => get(`/sweeps/${id}`);
