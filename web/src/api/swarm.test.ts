import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import { launchSwarm, previewSwarm, type SwarmLaunchRequest } from "./swarm";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
}));

describe("swarm api", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
    vi.mocked(apiFetch).mockResolvedValue({});
  });

  it("posts the preview request to the preview endpoint with the abort signal", async () => {
    const controller = new AbortController();
    const req = { objective: "audit", task_type: "research" as const };

    await previewSwarm(req, controller.signal);

    expect(apiFetch).toHaveBeenCalledWith("/api/swarm/preview", {
      method: "POST",
      body: req,
      signal: controller.signal,
    });
  });

  it("posts the approved launch request, including preview id and approval token", async () => {
    const req: SwarmLaunchRequest = {
      objective: "audit",
      approved: true,
      preview_id: "preview-1",
      approval_token: "token-1",
    };

    await launchSwarm(req);

    expect(apiFetch).toHaveBeenCalledWith("/api/swarm/launch", {
      method: "POST",
      body: req,
      signal: undefined,
    });
  });

  it("propagates apiFetch rejections instead of swallowing them", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"));

    await expect(previewSwarm({ objective: "x" })).rejects.toThrow("boom");
  });
});
