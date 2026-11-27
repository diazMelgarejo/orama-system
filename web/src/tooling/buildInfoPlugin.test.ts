import { describe, expect, it } from "vitest";
import { buildInfoPlugin } from "./buildInfoPlugin";

async function emitted(plugin: ReturnType<typeof buildInfoPlugin>) {
  const files: { fileName: string; source: string }[] = [];
  const hook = plugin.generateBundle;
  const handler = typeof hook === "function" ? hook : hook?.handler;
  if (!handler) throw new Error("Expected a generateBundle hook");
  type Context = ThisParameterType<typeof handler>;
  const emitFile: Context["emitFile"] = (file) => {
    if (file.type !== "asset" || !file.fileName || typeof file.source !== "string") {
      throw new Error("Expected a named text asset");
    }
    return String(files.push({ fileName: file.fileName, source: file.source }));
  };
  await handler.call({ emitFile } as Context, {} as Parameters<typeof handler>[0], {}, false);
  return files;
}

const FIXED = () => new Date("2026-11-27T08:00:00.000Z");

describe("buildInfoPlugin", () => {
  it("writes build-info.json with the commit and the build time", async () => {
    const files = await emitted(buildInfoPlugin(() => "abc1234", FIXED));
    expect(files).toHaveLength(1);
    expect(files[0].fileName).toBe("build-info.json");
    expect(JSON.parse(files[0].source)).toEqual({ git_sha: "abc1234", built_at: "2026-11-27T08:00:00.000Z" });
  });

  it("says unknown, never an invented commit, when git is not available", async () => {
    const files = await emitted(buildInfoPlugin(() => { throw new Error("not a git repository"); }, FIXED));
    expect(JSON.parse(files[0].source).git_sha).toBe("unknown");
  });

  it("only runs for builds, not the dev server", () => {
    expect(buildInfoPlugin().apply).toBe("build");
  });
});
