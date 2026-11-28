import type { AppState, AppStateSection } from "@/api/appState";

/** Where the numbers on screen came from. Only "live" may be presented as current. */
export type Provenance =
  | { kind: "loading" }
  | { kind: "live" }
  | { kind: "stale"; lastGoodAt: number }
  | { kind: "unavailable" }
  | { kind: "demo" };

interface QueryFacts {
  hasData: boolean;
  isError: boolean;
  isPending: boolean;
  /** A paused fetch (browser offline) cannot refresh, so the data must not be presented as current. */
  isPaused?: boolean;
  dataUpdatedAt?: number;
}

/** Demo fixtures appear only when switched on explicitly (VITE_PORTAL_DEMO=1); never as an error fallback. */
export function isDemoMode(): boolean {
  return import.meta.env.VITE_PORTAL_DEMO === "1";
}

export function provenanceOf(query: QueryFacts, demo: boolean): Provenance {
  if (demo) return { kind: "demo" };
  if (query.hasData) {
    return query.isError || query.isPaused ? { kind: "stale", lastGoodAt: query.dataUpdatedAt ?? 0 } : { kind: "live" };
  }
  return query.isError ? { kind: "unavailable" } : { kind: "loading" };
}

function unavailableSection<T>(name: string): AppStateSection<T> {
  return { available: false, source: `unavailable:${name}`, data: null, error: "no live answer from the portal" };
}

/** What the console shows instead of invented data: every section unavailable and empty. */
export const UNAVAILABLE_STATE: AppState = {
  portal: unavailableSection("portal"),
  runtime: unavailableSection("runtime"),
  models: unavailableSection("models"),
  activity: unavailableSection("activity"),
  jobs: unavailableSection("jobs"),
};

/** Effect controls (preview, launch) work only against a live answer; the reason is shown, never hidden. */
export function effectsOffReason(p: Provenance): string | undefined {
  switch (p.kind) {
    case "live":
      return undefined;
    case "demo":
      return "Demo data: controls are off. Nothing here is real.";
    case "stale":
      return "Data is stale: controls are off until live data returns.";
    case "loading":
      return "Loading: controls are off until live data returns.";
    default:
      return "Live data unavailable: controls are off until live data returns.";
  }
}
