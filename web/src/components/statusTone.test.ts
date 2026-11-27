import { describe, expect, it } from "vitest";

import { statusToTone } from "./statusTone";
import type { StatusTone } from "./StatusBadge";

describe("statusToTone", () => {
  it.each([
    ["ok", "ok"],
    ["online", "ok"],
    ["READY", "ok"],
    ["completed", "ok"],
    ["succeeded", "ok"],
    ["warn", "warn"],
    ["queued", "warn"],
    ["pending", "warn"],
    ["waiting", "warn"],
    ["partial", "warn"],
    ["PARTIAL", "warn"],
    ["error", "err"],
    ["failed", "err"],
    ["blocked", "err"],
    ["rejected", "err"],
    ["running", "info"],
    ["in_progress", "info"],
    ["active", "info"],
    ["gpu", "gpu"],
    ["busy", "gpu"],
    ["mystery", "neutral"],
  ] as [string, StatusTone][])("maps %s to %s", (status, tone) => {
    expect(statusToTone(status)).toBe(tone);
  });

  it.each([undefined, null, ""] as (string | null | undefined)[])(
    "treats a missing status as neutral",
    (status) => {
      expect(statusToTone(status)).toBe("neutral");
    },
  );
});
