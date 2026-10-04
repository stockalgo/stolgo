import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useApi } from "../hooks/useApi.js";

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

describe("useApi", () => {
  it("keeps a cached run when an older request finishes after navigation", async () => {
    const cachedFetcher = vi.fn().mockResolvedValue("cached run");
    const seed = renderHook(() => useApi("race:cached", cachedFetcher));
    await waitFor(() => expect(seed.result.current.data).toBe("cached run"));
    seed.unmount();

    const slow = deferred();
    const slowFetcher = vi.fn(() => slow.promise);
    const hook = renderHook(({ key, fetcher }) => useApi(key, fetcher), {
      initialProps: { key: "race:slow", fetcher: slowFetcher },
    });
    await waitFor(() => expect(slowFetcher).toHaveBeenCalled());
    hook.rerender({ key: "race:cached", fetcher: cachedFetcher });
    expect(hook.result.current.data).toBe("cached run");
    await act(async () => { slow.resolve("old run"); });
    expect(hook.result.current.data).toBe("cached run");
  });

  it("clears the previous run while a different run loads", async () => {
    const firstFetcher = vi.fn().mockResolvedValue("first run");
    const slow = deferred();
    const secondFetcher = vi.fn(() => slow.promise);
    const hook = renderHook(({ key, fetcher }) => useApi(key, fetcher), {
      initialProps: { key: "clear:first", fetcher: firstFetcher },
    });
    await waitFor(() => expect(hook.result.current.data).toBe("first run"));
    hook.rerender({ key: "clear:second", fetcher: secondFetcher });
    expect(hook.result.current.data).toBeUndefined();
    expect(hook.result.current.loading).toBe(true);
    await act(async () => { slow.resolve("second run"); });
    expect(hook.result.current.data).toBe("second run");
  });

  it("turns synchronous fetcher failures into a retryable error", async () => {
    const failure = new Error("fetch failed");
    const fetcher = vi.fn(() => { throw failure; });
    const hook = renderHook(() => useApi("sync:failure", fetcher));
    await waitFor(() => expect(hook.result.current.error).toBe(failure));
    expect(hook.result.current.loading).toBe(false);
    fetcher.mockResolvedValueOnce("recovered");
    act(() => { hook.result.current.reload(); });
    await waitFor(() => expect(hook.result.current.data).toBe("recovered"));
    expect(hook.result.current.error).toBeNull();
  });
});
