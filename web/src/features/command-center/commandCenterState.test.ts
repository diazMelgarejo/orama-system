import { describe, expect, it } from "vitest";
import type { AppState, JobSummary } from "@/api/appState";
import { mockState } from "@/data/mockState";
import {
  resolveDisplayState,
  resolveJobs,
  resolveLatestJobId,
} from "./commandCenterState";

// Produces a state where the jobs section data is null (absent from API response).
// Use this to test the guard path in resolveJobs; pass an array to test
// the present-but-empty path.
const stateWithJobsData = (
  data: { jobs: JobSummary[] } | null,
): AppState => ({
  ...mockState,
  jobs: {
    ...mockState.jobs,
    data,
  },
});

describe("resolveDisplayState", () => {
  it("falls back to mock state when the fetch result is undefined", () => {
    expect(resolveDisplayState(undefined, mockState)).toBe(mockState);
  });

  it("uses live API state when data is present", () => {
    const live: AppState = {
      ...mockState,
      portal: { ...mockState.portal, source: "live:portal" },
    };
    expect(resolveDisplayState(live, mockState)).toBe(live);
  });
});

describe("resolveJobs", () => {
  it("falls back to mock jobs when the jobs section is absent (data: null)", () => {
    const state = stateWithJobsData(null);
    expect(resolveJobs(state, mockState.jobs.data.jobs)).toEqual(
      mockState.jobs.data.jobs,
    );
  });

  it("preserves an explicit empty jobs array from the API", () => {
    const state = stateWithJobsData({ jobs: [] });
    expect(resolveJobs(state, mockState.jobs.data.jobs)).toEqual([]);
  });
});

describe("resolveLatestJobId", () => {
  it("returns undefined when the first job has an empty string id", () => {
    const jobs: JobSummary[] = [{ job_id: "", status: "queued" }];
    expect(resolveLatestJobId(jobs)).toBeUndefined();
  });

  it("returns job_id when present", () => {
    const jobs: JobSummary[] = [{ job_id: "run_abc", status: "queued" }];
    expect(resolveLatestJobId(jobs)).toBe("run_abc");
  });

  it("falls back to id when job_id is absent", () => {
    const jobs: JobSummary[] = [{ id: "legacy-1", status: "queued" }];
    expect(resolveLatestJobId(jobs)).toBe("legacy-1");
  });
});
