import { useState, useEffect, useRef, useCallback } from "react";

const apiCache = new Map();

/**
 * useApi hook with in-memory caching and stale response protection.
 *
 * Signature:
 *   useApi(cacheKey, fetcher, deps = [])
 */
export function useApi(key, fetcher, deps = []) {
  const [data, setData] = useState(() => {
    if (key && apiCache.has(key)) {
      return apiCache.get(key);
    }
    return undefined;
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(() => {
    if (typeof fetcher !== "function") return false;
    if (key && apiCache.has(key)) return false;
    return true;
  });

  const reqIdRef = useRef(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(
    (force = false) => {
      // Invalidate older requests even when this load takes the cache path.
      const currentReqId = ++reqIdRef.current;
      const fn = fetcherRef.current;
      if (typeof fn !== "function") {
        setData(undefined);
        setError(null);
        setLoading(false);
        return;
      }

      if (key && !force && apiCache.has(key)) {
        setData(apiCache.get(key));
        setLoading(false);
        setError(null);
        return;
      }

      if (key && force) {
        apiCache.delete(key);
      }

      setData(undefined);
      setLoading(true);
      setError(null);

      Promise.resolve().then(() => fn())
        .then((res) => {
          if (currentReqId === reqIdRef.current) {
            if (key) {
              apiCache.set(key, res);
            }
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
    [key, fetcher, ...deps]
  );

  useEffect(() => {
    load();
    return () => { ++reqIdRef.current; };
  }, [load]);

  const reload = useCallback(() => {
    load(true);
  }, [load]);

  return { data, error, loading, reload };
}
