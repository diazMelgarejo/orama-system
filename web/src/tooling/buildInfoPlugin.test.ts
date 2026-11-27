import { describe, expect, it } from "vitest";
import { buildInfoPlugin } from "./buildInfoPlugin";

function emitted(plugin: ReturnType<typeof buildInfoPlugin>) {
  const files: { fileName: string; source: string }[] = [];
  const hook = plugin.generateBundle as (this: { emitFile: (f: { fileName: string; source: string }) => void }) => void;
  hook.call({ emitFile: (f) => files.push(f) });
  return files;
}

const FIXED = () => new Date("2026-11-27T08:00:00.000Z");

describe("buildInfoPlugin", () => {
  it("writes build-info.json with the commit and the build time", () => {
    const files = emitted(buildInfoPlugin(() => "abc1234", FIXED));
    expect(files).toHaveLength(1);
    expect(files[0].fileName).toBe("build-info.json");
    expect(JSON.parse(files[0].source)).toEqual({ git_sha: "abc1234", built_at: "2026-11-27T08:00:00.000Z" });
  });

  it("says unknown, never an invented commit, when git is not available", () => {
    const files = emitted(buildInfoPlugin(() => { throw new Error("not a git repository"); }, FIXED));
    expect(JSON.parse(files[0].source).git_sha).toBe("unknown");
  });

  it("only runs for builds, not the dev server", () => {
    expect(buildInfoPlugin().apply).toBe("build");
  });
});
