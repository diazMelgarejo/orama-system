import type { AppState, JobSummary } from "@/api/appState";

/** Display state: live API payload or mock seed while loading / on error. */
export function resolveDisplayState(
  fetched: AppState | undefined,
  fallback: AppState,
): AppState {
  return fetched ?? fallback;
}

/**
 * Jobs list from app state, with mock seed when the jobs section is absent.
 * An explicit empty array from the API is preserved (not replaced by mock).
 */
export function resolveJobs(
  state: AppState,
  fallbackJobs: JobSummary[],
): JobSummary[] {
  const fromApi = state.jobs?.data?.jobs;
  if (fromApi === undefined || fromApi === null) {
    return fallbackJobs;
  }
  return fromApi as JobSummary[];
}

export function resolveLatestJobId(jobs: JobSummary[]): string | undefined {
  const first = jobs[0];
  if (!first) return undefined;
  const id = first.job_id ?? first.id;
  if (id === undefined || id === "") return undefined;
  return String(id);
}
