import { useEffect, useState } from "preact/hooks";

export interface FetchState<T> {
  data?: T;
  error?: string;
  loading: boolean;
}

// useFetch runs an async function whenever any dep changes and tracks
// loading/error/data. The reload key (a number bumped by the Refresh button)
// is passed as a dep to force re-fetches.
export function useFetch<T>(fn: () => Promise<T>, deps: unknown[]): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ loading: true });
  useEffect(() => {
    let cancelled = false;
    setState({ loading: true });
    fn()
      .then((data) => !cancelled && setState({ data, loading: false }))
      .catch((e) => !cancelled && setState({ error: String(e?.message ?? e), loading: false }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

// settle resolves to the value or undefined, so optional endpoints (e.g.
// inotifiers on older masters) don't fail an entire section.
export async function settle<T>(p: Promise<T>): Promise<T | undefined> {
  try {
    return await p;
  } catch {
    return undefined;
  }
}
