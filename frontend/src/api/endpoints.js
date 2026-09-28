import { get } from "./client.js";

const enc = encodeURIComponent;
const qs = (obj) =>
  Object.entries(obj)
    .filter(([_, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${enc(k)}=${enc(v)}`)
    .join("&");

export const listRuns = () => get("/runs");
export const getRun = (id) => get(`/runs/${enc(id)}`);
export const getDaily = (id) => get(`/runs/${enc(id)}/daily`);
export const getMonthly = (id) => get(`/runs/${enc(id)}/monthly`);
export const getTrades = (id) => get(`/runs/${enc(id)}/trades`);
export const getTrade = (id, tradeId) => get(`/runs/${enc(id)}/trades/${tradeId}`);
export const getCandles = (id, tf, from, to) =>
  get(`/runs/${enc(id)}/candles?${qs({ tf, from, to })}`);
export const getEquity = (id) => get(`/runs/${enc(id)}/equity`);
export const listGroups = () => get("/groups");
export const getGroup = (gid) => get(`/groups/${enc(gid)}`);
export const auditUrl = (id) => `/api/runs/${enc(id)}/audit`;
