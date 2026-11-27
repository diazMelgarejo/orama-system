import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import {
  listSessionSecrets,
  purgeSessionSecrets,
  saveSessionSecrets,
  setSessionSecret,
} from "./sessionSecrets";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
}));

const VALUE = "fixture-value-not-a-real-key";

describe("session secrets api", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
    vi.mocked(apiFetch).mockResolvedValue({});
  });

  it("lists the session names through the authenticated fetch helper", async () => {
    await listSessionSecrets();

    expect(apiFetch).toHaveBeenCalledWith("/api/session-secrets", { signal: undefined });
  });

  it("puts the value in the body, never in the path", async () => {
    await setSessionSecret("WANDB_API_KEY", VALUE);

    expect(apiFetch).toHaveBeenCalledWith("/api/session-secrets/WANDB_API_KEY", {
      method: "PUT",
      body: { value: VALUE },
      signal: undefined,
    });
  });

  it("encodes the name so the server refuses an invalid one instead of a mangled path", async () => {
    await setSessionSecret("lower/name", "v");

    expect(apiFetch).toHaveBeenCalledWith("/api/session-secrets/lower%2Fname", {
      method: "PUT",
      body: { value: "v" },
      signal: undefined,
    });
  });

  it("asks the server to save without sending any value", async () => {
    await saveSessionSecrets();

    expect(apiFetch).toHaveBeenCalledWith("/api/session-secrets/save", {
      method: "POST",
      signal: undefined,
    });
  });

  it("purges the session without sending any value", async () => {
    await purgeSessionSecrets();

    expect(apiFetch).toHaveBeenCalledWith("/api/session-secrets", {
      method: "DELETE",
      signal: undefined,
    });
  });
});
