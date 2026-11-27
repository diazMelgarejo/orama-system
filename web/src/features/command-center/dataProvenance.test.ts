import { afterEach, describe, expect, it, vi } from "vitest";
import { UNAVAILABLE_STATE, isDemoMode, provenanceOf } from "./dataProvenance";

describe("provenanceOf: where the numbers on screen came from", () => {
  it("is loading before the first answer", () => {
    expect(provenanceOf({ hasData: false, isError: false, isPending: true }, false)).toEqual({ kind: "loading" });
  });

  it("is live when the API answered and the last refresh worked", () => {
    expect(provenanceOf({ hasData: true, isError: false, isPending: false }, false)).toEqual({ kind: "live" });
  });

  it("is unavailable, never live, when the API never answered", () => {
    expect(provenanceOf({ hasData: false, isError: true, isPending: false }, false)).toEqual({ kind: "unavailable" });
  });

  it("is stale, with the time of the last good answer, when a refresh failed after a success", () => {
    const updatedAt = Date.UTC(2026, 10, 27, 8, 0, 0);
    expect(provenanceOf({ hasData: true, isError: true, isPending: false, dataUpdatedAt: updatedAt }, false)).toEqual({
      kind: "stale",
      lastGoodAt: updatedAt,
    });
  });

  it("is demo only when demo mode is switched on explicitly, whatever the API did", () => {
    expect(provenanceOf({ hasData: false, isError: true, isPending: false }, true)).toEqual({ kind: "demo" });
    expect(provenanceOf({ hasData: true, isError: false, isPending: false }, true)).toEqual({ kind: "demo" });
  });
});

describe("UNAVAILABLE_STATE", () => {
  it("claims nothing: every section is unavailable and empty", () => {
    for (const section of Object.values(UNAVAILABLE_STATE)) {
      expect(section.available).toBe(false);
      expect(section.data).toBeNull();
    }
  });
});

describe("isDemoMode", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("is off by default and on only for the explicit flag value 1", () => {
    expect(isDemoMode()).toBe(false);
    vi.stubEnv("VITE_PORTAL_DEMO", "true");
    expect(isDemoMode()).toBe(false);
    vi.stubEnv("VITE_PORTAL_DEMO", "1");
    expect(isDemoMode()).toBe(true);
  });
});
