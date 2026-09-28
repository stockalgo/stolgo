import { useState, useEffect, useRef, useCallback } from "react";

const apiCache = new Map();

/**
 * useApi hook with in-memory caching and stale response protection.
 *
 * @param {string|null} key Cache key (pass null to skip fetching)
 * @param {Function} fetcher Async fetch function
 * @param {Array} deps Dependencies array
 */
export function useApi(key, fetcher, deps = []) {
  const [data, setData] = useState(() => (key ? apiCache.get(key) : undefined));
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(() => (key ? !apiCache.has(key) : false));
  const reqIdRef = useRef(0);

  const load = useCallback(
    (force = false) => {
      if (!key || typeof fetcher !== "function") return;
      if (!force && apiCache.has(key)) {
        setData(apiCache.get(key));
        setLoading(false);
        setError(null);
        return;
      }
      if (force) {
        apiCache.delete(key);
      }
      const currentReqId = ++reqIdRef.current;
      setLoading(true);
      setError(null);

      fetcher()
        .then((res) => {
          if (currentReqId === reqIdRef.current) {
            apiCache.set(key, res);
            setData(res);
            setLoading(false);
          }
        })
        .catch((err) => {
          if (currentReqId === reqIdRef.current) {
            setError(err);
            setLoading(false);
          }
        });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key, ...deps]
  );

  useEffect(() => {
    load();
  }, [load]);

  const reload = useCallback(() => {
    load(true);
  }, [load]);

  return { data, error, loading, reload };
}
