import { useState, useEffect, useRef, useCallback } from "react";

const apiCache = new Map();

/**
 * useApi hook with in-memory caching and stale response protection.
 *
 * Supports signatures:
 *   useApi(fetcher, deps = [])
 *   useApi(cacheKey, fetcher, deps = [])
 */
export function useApi(arg1, arg2, arg3 = []) {
  let key = null;
  let fetcher = null;
  let deps = [];

  if (typeof arg1 === "function") {
    fetcher = arg1;
    deps = Array.isArray(arg2) ? arg2 : [];
    key = null;
  } else {
    key = typeof arg1 === "string" ? arg1 : null;
    fetcher = typeof arg2 === "function" ? arg2 : null;
    deps = Array.isArray(arg3) ? arg3 : [];
  }

  const [data, setData] = useState(() => {
    if (key && apiCache.has(key)) {
      return apiCache.get(key);
    }
    return undefined;
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(() => {
    if (!fetcher) return false;
    if (key && apiCache.has(key)) return false;
    return true;
  });

  const reqIdRef = useRef(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(
    (force = false) => {
      const fn = fetcherRef.current;
      if (typeof fn !== "function") {
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

      const currentReqId = ++reqIdRef.current;
      setLoading(true);
      setError(null);

      Promise.resolve(fn())
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
  }, [load]);

  const reload = useCallback(() => {
    load(true);
  }, [load]);

  return { data, error, loading, reload };
}
