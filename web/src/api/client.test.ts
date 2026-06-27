import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, ApiError } from "./client";

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on a successful response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );

    await expect(apiFetch<{ ok: boolean }>("/api/app/state")).resolves.toEqual({
      ok: true,
    });
  });

  it("throws ApiError with status and body on HTTP error", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "not found" }), {
        status: 404,
        statusText: "Not Found",
      }),
    );

    await expect(apiFetch("/api/missing")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      url: "/api/missing",
      body: { detail: "not found" },
    } satisfies Partial<ApiError>);
  });

  it("uses GET by default when no options are supplied", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "1" }), { status: 200 }),
    );

    await apiFetch("/api/jobs");

    expect(fetch).toHaveBeenCalledWith(
      "/api/jobs",
      expect.objectContaining({ method: "GET" }),
    );
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init as RequestInit).body).toBeUndefined();
  });

  it("serializes POST body as JSON string", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "1" }), { status: 200 }),
    );

    await apiFetch("/api/jobs", { method: "POST", body: { prompt: "hi" } });

    expect(fetch).toHaveBeenCalledWith(
      "/api/jobs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ prompt: "hi" }),
      }),
    );
  });
});
